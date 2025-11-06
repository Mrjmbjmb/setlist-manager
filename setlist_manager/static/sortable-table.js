(() => {
    const sortableTable = document.querySelector("[data-sortable-table]");
    if (!sortableTable) {
        return;
    }

    const table = sortableTable.querySelector("table");
    const tbody = table.querySelector("tbody");
    const headers = table.querySelectorAll("th[data-sortable]");

    let currentSort = { column: null, direction: "asc" };

    // Parse different data types
    const parseValue = (text, dataType) => {
        const cleanText = text.trim();

        switch (dataType) {
            case "number":
                return parseInt(cleanText.replace(/[^\d-]/g, ""), 10) || 0;
            case "date":
                // Handle dates like "Nov 05, 2025" and "—"
                if (cleanText === "—" || cleanText === "") {
                    return new Date(0); // Put empty dates at the beginning
                }
                return new Date(cleanText) || new Date(0);
            case "duration":
                // Parse duration like "45:30" into seconds
                if (cleanText === "—" || cleanText === "") {
                    return 0;
                }
                const [minutes, seconds] = cleanText.split(":").map(Number);
                return (minutes * 60) + (seconds || 0);
            default:
                return cleanText.toLowerCase();
        }
    };

    const sortTable = (columnIndex, dataType) => {
        const rows = Array.from(tbody.querySelectorAll("tr"));

        // Toggle sort direction or set to ascending if new column
        if (currentSort.column === columnIndex) {
            currentSort.direction = currentSort.direction === "asc" ? "desc" : "asc";
        } else {
            currentSort.column = columnIndex;
            currentSort.direction = "asc";
        }

        // Update header classes
        headers.forEach((header, index) => {
            header.classList.remove("sort-asc", "sort-desc");
            if (index === columnIndex) {
                header.classList.add(`sort-${currentSort.direction}`);
            }
        });

        // Sort rows
        rows.sort((a, b) => {
            const aValue = parseValue(a.cells[columnIndex].textContent, dataType);
            const bValue = parseValue(b.cells[columnIndex].textContent, dataType);

            let comparison = 0;
            if (aValue < bValue) {
                comparison = -1;
            } else if (aValue > bValue) {
                comparison = 1;
            }

            return currentSort.direction === "asc" ? comparison : -comparison;
        });

        // Reorder DOM
        rows.forEach(row => tbody.appendChild(row));
    };

    // Add click handlers to sortable headers
    headers.forEach((header, index) => {
        // Make headers look clickable
        header.style.cursor = "pointer";
        header.title = "Click to sort";

        // Add sort indicator
        const indicator = document.createElement("span");
        indicator.className = "sort-indicator";
        indicator.innerHTML = " ↕";
        header.appendChild(indicator);

        header.addEventListener("click", () => {
            const dataType = header.dataset.sortable || "text";
            sortTable(index, dataType);
        });
    });

    // Add CSS for sort indicators
    const style = document.createElement("style");
    style.textContent = `
        th[data-sortable] {
            position: relative;
            user-select: none;
        }

        th[data-sortable]:hover {
            background-color: rgba(0, 0, 0, 0.05);
        }

        .sort-indicator {
            opacity: 0.3;
            font-size: 0.8em;
        }

        th.sort-asc .sort-indicator::after {
            content: " ↑";
            opacity: 1;
        }

        th.sort-desc .sort-indicator::after {
            content: " ↓";
            opacity: 1;
        }
    `;
    document.head.appendChild(style);
})();