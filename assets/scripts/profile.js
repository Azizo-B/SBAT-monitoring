
document.addEventListener("DOMContentLoaded", async function () {
    const token = localStorage.getItem("authToken");
    let subscriber_id;

    if (!token) {
      window.location.href = "/login";
      return;
    }

    try {
      const response = await fetch("https://api.rijexamenmeldingen.be/auth/user/me", {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }

      if (!response.ok) {
        throw new Error("Network response was not ok.");
      }

      const data = await response.json();

      subscriber_id = data._id;

      document.getElementById("user-name").textContent =
        data.name || "Onbekend";
      document.getElementById("user-email").textContent =
        data.email || "Onbekend";
      document.getElementById("user-phone").textContent =
        data.phone || "Niet opgegeven";
      document.getElementById("user-telegram").textContent =
        data.telegram_username || "Niet opgegeven";

      const subscriptionStatus =
        data.stripe_ids.length > 0 ? "Actief" : "Niet Actief";
      document.getElementById("subscription-status").textContent =
        subscriptionStatus;

      if (subscriptionStatus === "Actief") {
        document
          .querySelectorAll("input[type='checkbox']")
          .forEach((checkbox) => (checkbox.disabled = false));
        document.getElementById("submit-preferences").disabled = false;

        data.monitoring_preferences.license_types.forEach((type) => {
          document.querySelector(
            `input[name='license_types'][value='${type}']`
          ).checked = true;
        });
        data.monitoring_preferences.exam_center_ids.forEach((id) => {
          document.querySelector(
            `input[name='exam_center_ids'][value='${id}']`
          ).checked = true;
        });
      }

      document
        .getElementById("submit-preferences")
        .addEventListener("click", async function () {
          const selectedLicenseTypes = Array.from(
            document.querySelectorAll("input[name='license_types']:checked")
          ).map((cb) => cb.value);
          const selectedExamCenters = Array.from(
            document.querySelectorAll(
              "input[name='exam_center_ids']:checked"
            )
          ).map((cb) => cb.value);

          try {
            const saveResponse = await fetch(
              "https://api.rijexamenmeldingen.be/auth/user/preferences",
              {
                method: "POST",
                headers: {
                  Authorization: `Bearer ${token}`,
                  "Content-Type": "application/json",
                },
                body: JSON.stringify({
                  license_types: selectedLicenseTypes,
                  exam_center_ids: selectedExamCenters,
                }),
              }
            );

            const saveData = await saveResponse.json();

            if (saveResponse.ok) {
              alert("Voorkeuren succesvol opgeslagen.");
            } else {
              alert(
                typeof saveData.detail === "string"
                  ? saveData.detail
                  : "Er is een fout opgetreden bij het opslaan van uw voorkeuren."
              );
            }
          } catch (error) {
            console.error(
              "There was a problem with the fetch operation:",
              error
            );
            alert("Er is een onverwachte fout opgetreden.");
          }
        });

      document
        .getElementById("activate-subscription")
        .addEventListener("click", function () {
          window.location.href = `https://buy.stripe.com/test_fZe9Cgb193Nmenm3cd?client_reference_id=${subscriber_id}`;
        });
    } catch (error) {
      console.error("There was a problem with the fetch operation:", error);
      alert("Er is een onverwachte fout opgetreden.");
    }
  });