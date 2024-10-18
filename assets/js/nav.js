document.addEventListener("DOMContentLoaded", function () {
    const isLoggedIn = localStorage.getItem("authToken") !== null;

    const navItems = document.querySelectorAll(".navbar-nav li");

    navItems.forEach(item => {
        const link = item.querySelector('a');

        if (isLoggedIn) {
            if (link.href.includes("login.html") || link.href.includes("register.html")) {
                item.style.display = "none";
            }

            if (link.href.includes("profile.html")) {
                item.style.display = "inline";
            }
        } else {
            if (link.href.includes("profile.html")) {
                item.style.display = "none";
            }
        }
    });
});
