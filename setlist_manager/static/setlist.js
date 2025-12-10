(() => {
    const tableBody = document.querySelector("[data-setlist-body]");
    const reorderUrl = tableBody?.dataset.reorderUrl || null;

    const actionSelector = "[data-entry-action]";
    const menuSelector = "[data-entry-menu]";
    const toggleSelector = "[data-entry-menu-toggle]";

    const closeEntryMenus = () => {
        document.querySelectorAll(`${menuSelector}.show`).forEach((menu) => {
            menu.classList.remove("show");
            const toggle = document.querySelector(
                `${toggleSelector}[aria-controls="${menu.id}"]`
            );
            if (toggle) {
                toggle.setAttribute("aria-expanded", "false");
            }
        });
    };

    const fallbackPost = (url) => {
        const form = document.createElement("form");
        form.method = "POST";
        form.action = url;
        form.style.display = "none";
        document.body.appendChild(form);
        form.submit();
    };

    const performEntryAction = (action, url) => {
        if (!url) {
            return;
        }

        const confirmations = {
            "remove-song": "Remove this song from the setlist?",
            "remove-encore": "Remove this encore break?",
            "add-encore": "Add an encore break after this song?",
        };

        const confirmMessage = confirmations[action];
        if (confirmMessage && !window.confirm(confirmMessage)) {
            return;
        }

        fetch(url, {
            method: "POST",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        })
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`Request failed with ${response.status}`);
                }
                return response.json();
            })
            .then((data) => {
                if (!data || (data.status !== "success" && data.status !== "ok")) {
                    throw new Error(data?.message || "Unexpected response from server.");
                }
                window.location.reload();
            })
            .catch((error) => {
                console.error("Falling back to form submission after error:", error);
                fallbackPost(url);
            });
    };

    document.addEventListener("click", (event) => {
        const actionButton = event.target.closest(actionSelector);
        if (actionButton) {
            event.preventDefault();
            event.stopPropagation();
            closeEntryMenus();
            performEntryAction(
                actionButton.dataset.entryAction,
                actionButton.dataset.actionUrl
            );
            return;
        }

        const toggle = event.target.closest(toggleSelector);
        if (toggle) {
            event.preventDefault();
            event.stopPropagation();
            const menuId = toggle.getAttribute("aria-controls");
            const menu = menuId ? document.getElementById(menuId) : null;
            if (!menu) {
                return;
            }

            const isOpen = menu.classList.contains("show");
            closeEntryMenus();
            if (!isOpen) {
                menu.classList.add("show");
                toggle.setAttribute("aria-expanded", "true");
            }
            return;
        }

        if (!event.target.closest(menuSelector)) {
            closeEntryMenus();
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeEntryMenus();
        }
    });

    if (!tableBody || !reorderUrl) {
        return;
    }

    let draggedRow = null;
    let draggedEncoreRow = null;
    let initialOrder = [];
    let hoverRow = null;
    let hoverPosition = null;

    const setHoverState = (row, position) => {
        if (hoverRow === row && hoverPosition === position) {
            return;
        }

        if (hoverRow) {
            hoverRow.classList.remove("drag-target-before", "drag-target-after");
        }

        hoverRow = row;
        hoverPosition = position;

        if (hoverRow) {
            hoverRow.classList.add(
                position === "before" ? "drag-target-before" : "drag-target-after"
            );
        }
    };

    const clearHoverState = () => {
        if (hoverRow) {
            hoverRow.classList.remove("drag-target-before", "drag-target-after");
            hoverRow = null;
            hoverPosition = null;
        }
    };

    const maybeAutoScroll = (clientY) => {
        const margin = 60;
        const speed = 15;
        if (clientY < margin) {
            window.scrollBy({ top: -speed, behavior: "auto" });
        } else if (clientY > window.innerHeight - margin) {
            window.scrollBy({ top: speed, behavior: "auto" });
        }
    };

    const getEncoreRow = (row) => {
        const previous = row.previousElementSibling;
        if (previous && previous.classList.contains("encore-break")) {
            return previous;
        }
        return null;
    };

    const placeRow = (row, beforeNode) => {
        const encoreRow = draggedEncoreRow;
        if (encoreRow) {
            encoreRow.remove();
        }

        row.remove();

        if (beforeNode) {
            tableBody.insertBefore(row, beforeNode);
        } else {
            tableBody.appendChild(row);
        }

        if (encoreRow) {
            tableBody.insertBefore(encoreRow, row);
            draggedEncoreRow = encoreRow;
        }
    };

    const getOrder = () =>
        Array.from(tableBody.querySelectorAll("tr[data-entry-id]")).map((row) =>
            Number.parseInt(row.dataset.entryId, 10)
        );

    const updatePositionCells = () => {
        tableBody
            .querySelectorAll("tr[data-entry-id]")
            .forEach((row, index) => {
                const cell = row.querySelector("[data-position-cell]");
                if (cell) {
                    cell.textContent = index + 1;
                }
            });
    };

    const persistOrder = () => {
        const currentOrder = getOrder();
        if (currentOrder.length === initialOrder.length) {
            const unchanged = currentOrder.every(
                (value, index) => value === initialOrder[index]
            );
            if (unchanged) {
                return;
            }
        }

        fetch(reorderUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Requested-With": "XMLHttpRequest",
            },
            body: JSON.stringify({ order: currentOrder }),
        }).catch((error) => {
            console.error("Failed to save setlist order", error);
        });
    };

    tableBody.addEventListener("dragstart", (event) => {
        const handle = event.target.closest("[data-drag-handle]");
        if (!handle) {
            event.preventDefault();
            return;
        }

        const row = handle.closest("tr[data-entry-id]");
        if (!row) {
            event.preventDefault();
            return;
        }

        row.classList.add("dragging");
        draggedRow = row;
        draggedEncoreRow = getEncoreRow(row);
        initialOrder = getOrder();

        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", row.dataset.entryId);

        handle.style.transform = "scale(1.1)";
        handle.style.background = "#e7efff";
    });

    tableBody.addEventListener("dragend", () => {
        if (draggedRow) {
            draggedRow.classList.remove("dragging");
            const handle = draggedRow.querySelector("[data-drag-handle]");
            if (handle) {
                handle.style.transform = "";
                handle.style.background = "";
            }
        }

        draggedRow = null;
        draggedEncoreRow = null;
        clearHoverState();
    });

    tableBody.addEventListener("dragover", (event) => {
        if (!draggedRow) {
            return;
        }
        event.preventDefault();
        event.dataTransfer.dropEffect = "move";
        maybeAutoScroll(event.clientY);

        let targetRow = event.target.closest("tr[data-entry-id]");
        let forceBefore = false;

        if (!targetRow) {
            const encoreRow = event.target.closest("tr.encore-break");
            if (encoreRow) {
                const nextRow = encoreRow.nextElementSibling;
                if (nextRow && nextRow.matches("tr[data-entry-id]")) {
                    targetRow = nextRow;
                    forceBefore = true;
                }
            }
        }

        if (!targetRow) {
            placeRow(draggedRow, null);
            const rows = tableBody.querySelectorAll("tr[data-entry-id]");
            if (rows.length) {
                setHoverState(rows[rows.length - 1], "after");
            } else {
                clearHoverState();
            }
            return;
        }

        if (targetRow === draggedRow) {
            clearHoverState();
            return;
        }

        let insertBefore = forceBefore;
        if (!insertBefore) {
            const rect = targetRow.getBoundingClientRect();
            const offset = event.clientY - rect.top;
            insertBefore = offset < rect.height / 2;
        }

        if (insertBefore) {
            placeRow(draggedRow, targetRow);
            setHoverState(targetRow, "before");
        } else {
            placeRow(draggedRow, targetRow.nextElementSibling);
            setHoverState(targetRow, "after");
        }
    });

    tableBody.addEventListener("drop", (event) => {
        if (!draggedRow) {
            return;
        }
        event.preventDefault();

        clearHoverState();
        updatePositionCells();
        persistOrder();
    });

    tableBody.querySelectorAll("button, a").forEach((element) => {
        element.addEventListener("dragstart", (event) => {
            if (!event.target.closest("[data-drag-handle]")) {
                event.preventDefault();
            }
        });
    });
})();
