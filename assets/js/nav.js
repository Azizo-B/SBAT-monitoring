document.addEventListener("DOMContentLoaded", function () {
    const isLoggedIn = localStorage.getItem("authToken") !== null;

    const navItems = document.querySelectorAll(".navbar-nav li");

    navItems.forEach(item => {
        const link = item.querySelector('a');

        if (isLoggedIn) {
            if (link.href.includes("login") || link.href.includes("register")) {
                item.style.display = "none";
            }

            if (link.href.includes("profile")) {
                item.style.display = "inline";
            }
        } else {
            if (link.href.includes("profile")) {
                item.style.display = "none";
            }
        }
    });
});
