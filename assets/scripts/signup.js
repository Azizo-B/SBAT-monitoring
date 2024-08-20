document.addEventListener("DOMContentLoaded", function () {
    const signupForm = document.getElementById("signup-form");
    const submitButton = signupForm.querySelector("button[type='submit']");

    loginForm.addEventListener("submit", async function (event) {
      event.preventDefault();

      submitButton.disabled = true;

      const formData = new FormData(signupForm);
      const userData = {
        name: formData.get("name"),
        email: formData.get("email"),
        password: formData.get("password"),
      };

      try {
        const response = await fetch(
          "http://35.202.199.95:8080/auth/subscribe",
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(userData),
          }
        );

        let data;
        try {
          data = await response.json();
        } catch (error) {
          data = { detail: "Er is een onverwachte fout opgetreden." };
        }
        if (response.status === 200) {
          console.log("Response Data:", data);
          window.location.href = "/login";
        } else {
          const errorMessage =
            typeof data.detail === "string"
              ? data.detail
              : "Er is een onverwachte fout opgetreden.";
          alert(`Error: ${errorMessage}`);
          submitButton.disabled = false;
        }
      } catch (error) {
        console.error(
          "There was a problem with the fetch operation:",
          error
        );
        submitButton.disabled = false;
      }
    });
  });