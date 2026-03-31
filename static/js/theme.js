/* =========================================================
   THEME TOGGLE SCRIPT
   - Dark / Light Mode
   - Smooth Transition
   - Local Storage Support
========================================================= */

document.addEventListener("DOMContentLoaded", () => {
    const savedTheme = localStorage.getItem("theme");

    if (savedTheme === "dark") {
        document.body.classList.add("dark");
    }
});

/* =========================================================
   TOGGLE THEME
========================================================= */
function toggleTheme() {
    document.body.classList.toggle("dark");

    if (document.body.classList.contains("dark")) {
        localStorage.setItem("theme", "dark");
        animateTheme("🌙 Dark Mode Enabled");
    } else {
        localStorage.setItem("theme", "light");
        animateTheme("☀️ Light Mode Enabled");
    }
}

/* =========================================================
   OPTIONAL: SMALL TOAST ANIMATION
========================================================= */
function animateTheme(message) {
    const toast = document.createElement("div");
    toast.innerText = message;

    toast.style.position = "fixed";
    toast.style.bottom = "30px";
    toast.style.right = "30px";
    toast.style.padding = "14px 20px";
    toast.style.background = "rgba(0,0,0,0.85)";
    toast.style.color = "#fff";
    toast.style.borderRadius = "12px";
    toast.style.fontSize = "14px";
    toast.style.boxShadow = "0 10px 30px rgba(0,0,0,0.4)";
    toast.style.zIndex = "9999";
    toast.style.opacity = "0";
    toast.style.transition = "all 0.4s ease";

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "1";
        toast.style.transform = "translateY(-10px)";
    }, 50);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateY(10px)";
        setTimeout(() => toast.remove(), 400);
    }, 2000);
}
