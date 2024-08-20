document.addEventListener("DOMContentLoaded", function () {
    const profileIcon = document.getElementById("profile-icon");
    profileIcon.addEventListener("click", function () {
      const token = localStorage.getItem("authToken");
      if (token) {
        window.location.href = "/profile";
      } else {
        window.location.href = "/login";
      }
    });
  });