document.addEventListener("DOMContentLoaded", function () {
    const signInBtn = document.getElementById("signInBtn");


    signInBtn.addEventListener("click", async function (event) {
        signInBtn.disabled = true;

        const formEntries = new URLSearchParams();
        formEntries.append("username", document.getElementById("emailInput").value);
        formEntries.append("password", document.getElementById("passwordInput").value);

        try {
            const response = await fetch("https://api.rijexamenmeldingen.be/auth/token", {
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
                localStorage.setItem("authToken", data.access_token);
                window.location.href = "/profile";
            } else {
                signInBtn.disabled = false;
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
            signInBtn.disabled = false;
            alert("Er is een onverwachte fout opgetreden.");
        }
    });
});