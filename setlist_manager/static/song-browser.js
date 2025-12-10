(() => {
    const songsBrowser = document.querySelector("[data-setlist-id]");
    if (!songsBrowser) {
        return;
    }

    const setlistId = songsBrowser.dataset.setlistId;
    const searchInput = document.getElementById("song-search");
    const sortSelect = document.getElementById("sort-select");
    const genreFilter = document.getElementById("genre-filter");
    const tagFilter = document.getElementById("tag-filter");
    const songsContainer = document.getElementById("available-songs-container");

    let availableSongs = [];
    let filteredSongs = [];

    // Debounce function for search
    const debounce = (func, wait) => {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    };

    // Load available songs via API
    const loadAvailableSongs = async () => {
        try {
            const response = await fetch(`/setlists/${setlistId}/available-songs/search`);
            const data = await response.json();
            availableSongs = data.songs;
            filteredSongs = [...availableSongs];

            populateGenreFilter();
            renderSongs();
        } catch (error) {
            console.error("Error loading available songs:", error);
            songsContainer.innerHTML = '<p class="error">Error loading songs. Please refresh the page.</p>';
        }
    };

    // Populate genre filter dropdown
    const populateGenreFilter = () => {
        const genres = [...new Set(availableSongs.map(song => song.genre).filter(Boolean))];
        genreFilter.innerHTML = '<option value="">All Genres</option>';
        genres.sort().forEach(genre => {
            const option = document.createElement("option");
            option.value = genre;
            option.textContent = genre;
            genreFilter.appendChild(option);
        });
    };

    // Filter and sort songs
    const filterAndSortSongs = () => {
        const query = searchInput.value.toLowerCase().trim();
        const sortBy = sortSelect.value;
        const genreValue = genreFilter.value;
        const tagValue = tagFilter.value;

        // Filter songs
        filteredSongs = availableSongs.filter(song => {
            const matchesSearch = !query ||
                song.title.toLowerCase().includes(query) ||
                song.artist.toLowerCase().includes(query) ||
                (song.alias && song.alias.toLowerCase().includes(query)) ||
                (song.genre && song.genre.toLowerCase().includes(query));

            const matchesGenre = !genreValue || song.genre === genreValue;

            const matchesTag = !tagValue ||
                (tagValue === "M" && song.tag_summary?.includes("M")) ||
                (tagValue === "CVR" && song.tag_summary?.includes("CVR")) ||
                (tagValue === "VO" && song.tag_summary?.includes("VO"));

            return matchesSearch && matchesGenre && matchesTag;
        });

        // Sort songs
        filteredSongs.sort((a, b) => {
            switch (sortBy) {
                case "title":
                    return a.title.localeCompare(b.title);
                case "artist":
                    return a.artist.localeCompare(b.artist) || a.title.localeCompare(b.title);
                case "duration":
                    return a.duration_seconds - b.duration_seconds;
                case "energy":
                    return (b.energy || 0) - (a.energy || 0) || a.title.localeCompare(b.title);
                case "plays":
                    return b.play_count - a.play_count || a.title.localeCompare(b.title);
                case "last_played":
                    // Handle "Never played" as oldest date
                    if (!a.last_played && !b.last_played) {
                        return a.title.localeCompare(b.title);
                    } else if (!a.last_played) {
                        return 1; // a is never played, put it after b
                    } else if (!b.last_played) {
                        return -1; // b is never played, put it after a
                    } else {
                        return new Date(b.last_played) - new Date(a.last_played) || a.title.localeCompare(b.title);
                    }
                default:
                    return a.title.localeCompare(b.title);
            }
        });

        renderSongs();
    };

    // Render songs list
    const renderSongs = () => {
        if (filteredSongs.length === 0) {
            songsContainer.innerHTML = '<p class="no-results">No songs found matching your criteria.</p>';
            return;
        }

        const songsHtml = filteredSongs.map(song => `
            <div class="song-card" data-song-id="${song.id}">
                <div class="song-info">
                    <div class="song-title">${song.title}</div>
                    <div class="song-artist">${song.artist}</div>
                    <div class="song-meta">
                        <span class="duration">${song.duration_label}</span>
                        ${song.genre ? `<span class="genre">${song.genre}</span>` : ''}
                        ${song.energy ? `<span class="energy">E${song.energy}</span>` : ''}
                        ${song.tag_summary ? `<span class="tags">${song.tag_summary}</span>` : ''}
                        <span class="plays">${song.play_count} plays</span>
                        ${song.last_played ? `<span class="last-played">Last: ${song.last_played}</span>` : '<span class="last-played">Never played</span>'}
                    </div>
                </div>
                <div class="song-actions">
                    <button class="add-button" data-song-id="${song.id}">Add</button>
                </div>
            </div>
        `).join("");

        songsContainer.innerHTML = songsHtml;
        attachSongEventListeners();
    };

    // Attach event listeners to song cards
    const attachSongEventListeners = () => {
        // Add buttons only
        document.querySelectorAll(".add-button").forEach(button => {
            button.addEventListener("click", handleAddSong);
        });
    };

    // Add song handler
    const handleAddSong = async (e) => {
        const songId = e.target.dataset.songId;
        await addSongToSetlist(songId);
    };

    // Add song to setlist via API
    const addSongToSetlist = async (songId) => {
        try {
            const button = document.querySelector(`[data-song-id="${songId}"] .add-button`);
            const originalText = button.textContent;
            button.textContent = "Adding...";
            button.disabled = true;

            const response = await fetch(`/setlists/${setlistId}/add-song`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-Requested-With": "XMLHttpRequest",
                },
                body: `song_id=${songId}`
            });

            const data = await response.json();

            if (response.ok && data.status === "success") {
                // Remove song from available list immediately
                availableSongs = availableSongs.filter(song => song.id != songId);
                filterAndSortSongs();

                // Update the setlist metadata in the UI without page reload
                updateSetlistMetadata(data);

                // Add the new song to the setlist table (if table exists)
                addSongToSetlistTable(data);

                // Log success for debugging
                console.log("Song added successfully:", data);

            } else {
                button.textContent = originalText;
                button.disabled = false;
                console.error("Server response:", data);
            }
        } catch (error) {
            console.error("Error adding song:", error);
            const button = document.querySelector(`[data-song-id="${songId}"] .add-button`);
            if (button) {
                button.textContent = "Add";
                button.disabled = false;
            }
        }
    };

    // Update setlist metadata in the UI
    const updateSetlistMetadata = (data) => {
        // Update song count - find the "Songs" dt and get its dd
        const dts = document.querySelectorAll("dt");
        dts.forEach(dt => {
            if (dt.textContent.includes("Songs")) {
                const dd = dt.nextElementSibling;
                if (dd && dd.tagName === "DD") {
                    dd.textContent = data.new_song_count;
                }
            }
            if (dt.textContent.includes("Total Duration")) {
                const dd = dt.nextElementSibling;
                if (dd && dd.tagName === "DD") {
                    dd.textContent = data.new_duration;
                }
            }
        });
    };

    // Add song to setlist table
    const addSongToSetlistTable = (data) => {
        const tableBody = document.querySelector("[data-setlist-body]");
        if (!tableBody) return;

        // Create new row for the added song
        const newRow = document.createElement("tr");
        newRow.dataset.entryId = data.entry_id;
        newRow.innerHTML = `
            <td data-position-cell>${data.position}</td>
            <td class="drag-cell">
                <button type="button" data-drag-handle draggable="true" class="drag-handle" aria-label="Drag to reorder">☰</button>
            </td>
            <td>${data.song_title}</td>
            <td>${data.song_artist}</td>
            <td>—</td>
            <td>${data.song_duration}</td>
            <td class="actions">
                <div class="dropdown">
                    <button class="dropdown-toggle" onclick="toggleDropdown(event, 'dropdown-${data.entry_id}')">
                        <span aria-hidden="true">⋯</span>
                        <span class="sr-only">Actions</span>
                    </button>
                    <div id="dropdown-${data.entry_id}" class="dropdown-menu">
                        <button class="dropdown-item" onclick="addEncore('/setlists/${setlistId}/entries/${data.entry_id}/add-encore', event)">
                            <span class="dropdown-icon">➕</span>
                            Add Encore Break
                        </button>
                        <button class="dropdown-item danger-item" onclick="removeSong(this, '/setlists/${setlistId}/entries/${data.entry_id}/remove')">
                            <span class="dropdown-icon">🗑️</span>
                            Remove Song
                        </button>
                    </div>
                </div>
            </td>
        `;

        tableBody.appendChild(newRow);

        // Re-initialize drag and drop if needed
        if (window.initializeSortableTable) {
            window.initializeSortableTable();
        }
    };

    // Show notification
    const showNotification = (message, type = "info") => {
        const notification = document.createElement("div");
        notification.className = `flash ${type}`;
        notification.textContent = message;

        const container = document.querySelector("main");
        container.insertBefore(notification, container.firstChild);

        setTimeout(() => notification.remove(), 3000);
    };

    // Event listeners
    searchInput.addEventListener("input", debounce(filterAndSortSongs, 300));
    sortSelect.addEventListener("change", filterAndSortSongs);
    genreFilter.addEventListener("change", filterAndSortSongs);
    tagFilter.addEventListener("change", filterAndSortSongs);

    // Initialize
    loadAvailableSongs();

    // Make refreshAvailableSongs globally available
    window.refreshAvailableSongs = loadAvailableSongs;
})();
