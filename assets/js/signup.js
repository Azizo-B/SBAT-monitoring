document.addEventListener("DOMContentLoaded", function () {
    const createAccountBtn = document.getElementById("createAccountBtn");

    createAccountBtn.addEventListener("click", async function (event) {


        const userData = {
            name: document.getElementById("nameInput").value,
            email: document.getElementById("emailInput").value,
            password: document.getElementById("passwordInput").value,
        };


        try {
            const response = await fetch(
                "https://api.rijexamenmeldingen.be/auth/signup",
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