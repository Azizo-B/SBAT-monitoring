var subscriber_id;
document.addEventListener("DOMContentLoaded", async function () {
  const disableButton = document.getElementById("disable-subscription");
  const token = localStorage.getItem("authToken");

  if (!token) {
    window.location.href = "/login";
    return;
  }

  try {
    const response = await fetch(
      "https://api.rijexamenmeldingen.be/subscribers/me",
      {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      }
    );

    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }

    if (!response.ok) {
      throw new Error("Network response was not ok.");
    }

    const data = await response.json();

    subscriber_id = data._id;


    document.getElementById("user-name").textContent = data.name || "Onbekend";
    document.getElementById("user-email").textContent =
      data.email || "Onbekend";
    document.getElementById("user-phone").textContent =
      data.phone || "Niet opgegeven";
    document.getElementById("user-telegram").textContent =
      `${data.telegram_user.first_name || "Onbekend"} ${data.telegram_user.last_name || ""}`;
    const subscriptionStatus =
      data.is_subscription_active ? "Actief" : "Niet Actief";
    document.getElementById("subscription-status").textContent =
      subscriptionStatus;

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

    if (subscriptionStatus === "Actief") {
      disableButton.style.display = "inline-block";
      document.getElementById("activate-subscription").disabled = true
    }

    document
      .getElementById("submit-preferences")
      .addEventListener("click", async function () {
        const selectedLicenseTypes = Array.from(
          document.querySelectorAll("input[name='license_types']:checked")
        ).map((cb) => cb.value);
        const selectedExamCenters = Array.from(
          document.querySelectorAll("input[name='exam_center_ids']:checked")
        ).map((cb) => cb.value);

        try {
          const saveResponse = await fetch(
            "https://api.rijexamenmeldingen.be/subscribers/me/preferences",
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
          console.error("There was a problem with the fetch operation:", error);
          alert("Er is een onverwachte fout opgetreden.");
        }
      });

    document
      .getElementById("activate-subscription")
      .addEventListener("click", function () {
        window.location.href = `https://buy.stripe.com/28oeWs5Jmd9o3Cg7ss?client_reference_id=${subscriber_id}`;
      });

    document.getElementById("sign-out").addEventListener("click", function () {
      localStorage.removeItem("authToken");
      window.location.href = `/`;
    });

    disableButton.addEventListener("click", async function () {
      window.location.href = "https://billing.stripe.com/p/login/9AQ5kV1gD4WP3XW288"
    });

  } catch (error) {
    console.error("There was a problem with the fetch operation:", error);
    alert("Er is een onverwachte fout opgetreden.");
  }
});

function onTelegramAuth(user) {
  fetch('https://api.rijexamenmeldingen.be/telegram-webhook', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ "login_widget_event": { subscriber_id: subscriber_id, user: user } }),
  })
    .then(response => {
      if (!response.ok) {
        throw new Error('Network response was not ok.');
      }
      return response.json();
    })
    .then(data => {
      console.log('Server response:', data);
      if (data.status === 'ok') {
        window.location.reload();
      } else {
        alert('Er is een onverwachte fout opgetreden.');
      }
    })
    .catch((error) => {
      console.error('Error:', error);
      alert('Er is een onverwachte fout opgetreden.');
    });
}