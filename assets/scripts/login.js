
document.addEventListener("DOMContentLoaded", function () {
    const loginForm = document.getElementById("login-form");
    const submitButton = loginForm.querySelector("button[type='submit']");

    loginForm.addEventListener("submit", async function (event) {
      event.preventDefault();

      submitButton.disabled = true;
      submitButton.textContent = "Bezig met inloggen..."; // Optionally, change the button text

      const formData = new FormData(loginForm);
      const formEntries = new URLSearchParams();
      formEntries.append("username", formData.get("email"));
      formEntries.append("password", formData.get("password"));

      try {
        const response = await fetch("http://35.202.199.95:8080/auth/token", {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
          body: formEntries,
        });

        let data;
        try {
          data = await response.json();
        } catch (error) {
          console.error("Error parsing JSON:", error);
          data = { detail: "Er is een onverwachte fout opgetreden." };
        }

        if (response.ok) {
          console.log("Response Data:", data);
          localStorage.setItem("authToken", data.access_token);
          window.location.href = "/profile";
        } else {
          submitButton.disabled = false;
          submitButton.textContent = "Inloggen";
          const errorMessage =
            typeof data.detail === "string"
              ? data.detail
              : "Er is een onverwachte fout opgetreden.";
          alert(`Error: ${errorMessage}`);
        }
      } catch (error) {
        console.error(
          "There was a problem with the fetch operation:",
          error
        );
        submitButton.disabled = false;
        submitButton.textContent = "Inloggen";
        alert("Er is een onverwachte fout opgetreden.");
      }
    });
  });