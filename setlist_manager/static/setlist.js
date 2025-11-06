(() => {
    const tableBody = document.querySelector("[data-setlist-body]");
    if (!tableBody) {
        return;
    }

    const reorderUrl = tableBody.dataset.reorderUrl;
    if (!reorderUrl) {
        return;
    }

    let draggedRow = null;
    let draggedEncoreRow = null;
    let initialOrder = [];

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

        // Add visual feedback to the drag handle
        handle.style.transform = 'scale(1.1)';
        handle.style.background = '#e7efff';
    });

    tableBody.addEventListener("dragend", () => {
        if (draggedRow) {
            draggedRow.classList.remove("dragging");

            // Reset drag handle styling
            const handle = draggedRow.querySelector('[data-drag-handle]');
            if (handle) {
                handle.style.transform = '';
                handle.style.background = '';
            }
        }
        draggedRow = null;
        draggedEncoreRow = null;
    });

    tableBody.addEventListener("dragover", (event) => {
        if (!draggedRow) {
            return;
        }
        event.preventDefault();
        event.dataTransfer.dropEffect = "move";

        const targetRow = event.target.closest("tr[data-entry-id]");
        if (!targetRow) {
            placeRow(draggedRow, null);
            return;
        }

        if (targetRow === draggedRow) {
            return;
        }

        const rect = targetRow.getBoundingClientRect();
        const offset = event.clientY - rect.top;
        const insertBefore = offset < rect.height / 2;

        if (insertBefore) {
            placeRow(draggedRow, targetRow);
        } else {
            placeRow(draggedRow, targetRow.nextElementSibling);
        }
    });

    tableBody.addEventListener("drop", (event) => {
        if (!draggedRow) {
            return;
        }
        event.preventDefault();

        updatePositionCells();
        persistOrder();
    });

    // Prevent dragging from triggering on interactive elements other than the handle.
    tableBody.querySelectorAll("button, a").forEach((element) => {
        element.addEventListener("dragstart", (event) => {
            if (!event.target.closest("[data-drag-handle]")) {
                event.preventDefault();
            }
        });
    });
})();
