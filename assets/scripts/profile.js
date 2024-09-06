let subscriber_id;
let disableButton;
const token = localStorage.getItem("authToken");
document.addEventListener("DOMContentLoaded", async function () {
  disableButton = document.getElementById("disable-subscription");


  let hash = window.location.hash;
  let accessToken = null;
  if (hash && hash.charAt(0) === '#') {
    hash = hash.substring(1);
    const params = new URLSearchParams(hash);
    accessToken = params.get('access_token');
  }

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
    if (accessToken) {
      onDiscordAuth(accessToken)
    }
    paintPage(data)


    document
      .getElementById("submit-preferences")
      .addEventListener("click", () => submitPreferences(token));

    document
      .getElementById("activate-subscription")
      .addEventListener("click", function () {
        window.location.href = `https://buy.stripe.com/28oeWs5Jmd9o3Cg7ss?client_reference_id=${subscriber_id}`;
      });

    document.getElementById("discord-login-button").addEventListener("click", function () {
      window.location.href = "https://discord.com/oauth2/authorize?client_id=1279427216706502750&response_type=token&redirect_uri=https%3A%2F%2Frijexamenmeldingen.be%2Fprofile&scope=identify+email";
    })

    document.getElementById("sign-out").addEventListener("click", function () {
      localStorage.removeItem("authToken");
      window.location.href = `/`;
    });

    document.getElementById("unlink-telegram").addEventListener("click", async function () {
      await patchTelegramUser({});
    });

    document.getElementById("unlink-discord").addEventListener("click", async function () {
      await patchDiscordUser({});
    });

    disableButton.addEventListener("click", async function () {
      window.location.href = "https://billing.stripe.com/p/login/9AQ5kV1gD4WP3XW288"
    });

  } catch (error) {
    console.error("There was a problem with the fetch operation:", error);
    alert("Er is een onverwachte fout opgetreden.");
  }
});

function paintPage(data) {
  const discordButton = document.getElementById("discord-login-button");
  const telegramButton = document.getElementById("telegram-login-button");
  const emailCheckbox = document.querySelector("input[name='email_notifications']");
  const unlinkTelegramButton = document.getElementById("unlink-telegram");
  const unlinkDiscordButton = document.getElementById("unlink-discord");

  if (data.discord_user && Object.keys(data.discord_user).length > 0) {
    discordButton.style.display = "none";
    unlinkDiscordButton.style.display = "inline-block";
  }

  if (data.telegram_user && Object.keys(data.telegram_user).length > 0) {
    telegramButton.style.display = "none";
    unlinkTelegramButton.style.display = "inline-block";
  }

  document.getElementById("user-name").textContent = data.name || "Onbekend";
  document.getElementById("user-email").textContent =
    data.email || "Onbekend";
  document.getElementById("user-phone").textContent =
    data.phone || "Niet opgegeven";
  document.getElementById("user-telegram").textContent =
    `${data.telegram_user?.first_name || "Onbekend"} ${data.telegram_user?.last_name || ""}`;
  document.getElementById("user-discord").textContent = `${data.discord_user?.username || "Onbekend"}`;
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

  if (emailCheckbox) {
    emailCheckbox.checked = data.wants_emails || false;
  }

  if (subscriptionStatus === "Actief") {
    disableButton.style.display = "inline-block";
    document.getElementById("submit-preferences").style.display = ""
    document.getElementById("activate-subscription").disabled = true
  }
}

async function submitPreferences(token) {
  const selectedLicenseTypes = Array.from(
    document.querySelectorAll("input[name='license_types']:checked")
  ).map((cb) => cb.value);
  const selectedExamCenters = Array.from(
    document.querySelectorAll("input[name='exam_center_ids']:checked")
  ).map((cb) => cb.value);
  const wantsEmails = document.querySelector("input[name='email_notifications']").checked;

  try {
    const saveResponse = await fetch(
      `https://api.rijexamenmeldingen.be/subscribers/me/preferences?wants_emails=${wantsEmails}`,
      {
        method: "PATCH",
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
}
function patchTelegramUser(user) {
  fetch('https://api.rijexamenmeldingen.be/subscribers/me/telegram-account', {
    method: 'PATCH',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(user),
  })
    .then(response => {
      if (!response.ok) {
        throw new Error('Network response was not ok.');
      }
      return response.json();
    })
    .then(data => {
      console.log('Server response:', data);
      window.location.reload();

    })
    .catch((error) => {
      console.error('Error:', error);
      alert('Er is een onverwachte fout opgetreden.');
    });
}

function onDiscordAuth(accessToken) {
  fetch('https://api.rijexamenmeldingen.be/subscribers/me/discord-account', {
    method: 'PATCH',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ token: accessToken }),
  })
    .then(response => {
      if (!response.ok) {
        throw new Error('Network response was not ok.');
      }
      return response.json();
    })
    .then(data => {
      console.log(data)
      window.location.href = "/profile";
    })
    .catch(error => {
      console.error('Error:', error);
      alert('Er is een onverwachte fout opgetreden.');
    });
}
function patchDiscordUser(user) {
  fetch('https://api.rijexamenmeldingen.be/subscribers/me/discord-account', {
    method: 'PATCH',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ discord_user: user }),
  })
    .then(response => {
      if (!response.ok) {
        throw new Error('Network response was not ok.');
      }
      return response.json();
    })
    .then(data => {
      console.log('Server response:', data);
      window.location.reload();
    })
    .catch((error) => {
      console.error('Error:', error);
      alert('Er is een onverwachte fout opgetreden.');
    });
}
