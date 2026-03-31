/* =========================================================
   LIVE CLOCK & DATE SCRIPT
   - Updates every second
   - Smooth (no DOM flicker)
   - Auto format
========================================================= */

document.addEventListener("DOMContentLoaded", () => {
    const clockElement = document.getElementById("clock");

    if (!clockElement) return;

    function updateClock() {
        const now = new Date();

        // Time
        let hours = now.getHours();
        let minutes = now.getMinutes();
        let seconds = now.getSeconds();

        // Date
        const day = now.toLocaleDateString("en-US", { weekday: "long" });
        const date = now.toLocaleDateString("en-US", {
            day: "numeric",
            month: "short",
            year: "numeric"
        });

        // Format time
        const ampm = hours >= 12 ? "PM" : "AM";
        hours = hours % 12 || 12;

        minutes = minutes < 10 ? "0" + minutes : minutes;
        seconds = seconds < 10 ? "0" + seconds : seconds;

        const timeString = `${hours}:${minutes}:${seconds} ${ampm}`;
        const dateString = `${day}, ${date}`;

        clockElement.innerHTML = `
            <span class="clock-time">${timeString}</span>
            <span class="clock-date">${dateString}</span>
        `;
    }

    updateClock();
    setInterval(updateClock, 1000);
});

