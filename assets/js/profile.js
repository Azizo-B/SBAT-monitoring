let subscriber_id;
const token = localStorage.getItem("authToken");
document.addEventListener("DOMContentLoaded", async function () {
    if (!token) {
        window.location.href = "/login";
        return;
    }

    let hash = window.location.hash;
    let accessToken = null;
    if (hash && hash.charAt(0) === '#') {
        hash = hash.substring(1);
        const params = new URLSearchParams(hash);
        accessToken = params.get('access_token');
    }

    try {
        const response = await fetch("https://api.rijexamenmeldingen.be/subscribers/me", { method: "GET", headers: { Authorization: `Bearer ${token}` } });

        if (response.status === 401) {
            window.location.href = "/login";
            return;
        }

        if (!response.ok) {
            throw new Error("Network response was not ok.");
        }

        if (accessToken) {
            onDiscordAuth(accessToken)
        }

        const data = await response.json();
        subscriber_id = data._id;
        paintPage(data)

    } catch (error) {
        console.error("There was a problem with the fetch operation:", error);
        alert("Er is een onverwachte fout opgetreden.");
    }
});

function paintPage(data) {
    const preferencesButton = document.getElementById("submit-preferences");
    const subscriptionButton = document.getElementById("subscription-btn");


    populateUserInformation(data)

    if (data.is_subscription_active) {
        preferencesButton.style.display = ""
        preferencesButton.addEventListener("click", () => submitPreferences(token));
        populateUserPreferences(data)

        subscriptionButton.innerText = "Annuleer Abonnement"
        subscriptionButton.style.backgroundColor = "#FF4C4C"
        subscriptionButton.addEventListener("click", function () {
            window.location.href = "https://billing.stripe.com/p/login/9AQ5kV1gD4WP3XW288";
        });
    } else {
        subscriptionButton.addEventListener("click", function () {
            window.location.href = `https://buy.stripe.com/28oeWs5Jmd9o3Cg7ss?client_reference_id=${subscriber_id}`;
        });
        document.getElementById("subscription-status").value = "Niet Actief";
    }


    document.getElementById("discord-login-button").addEventListener("click", function () {
        window.location.href = "https://discord.com/oauth2/authorize?client_id=1279427216706502750&response_type=token&redirect_uri=https%3A%2F%2Frijexamenmeldingen.be%2Fprofile&scope=identify+email";
    })

    document.getElementById("logout").addEventListener("click", function () {
        localStorage.removeItem("authToken");
        window.location.href = `/`;
    });

    document.getElementById("unlink-telegram").addEventListener("click", async function () {
        await patchTelegramUser({});
    });

    document.getElementById("unlink-discord").addEventListener("click", async function () {
        await patchDiscordUser({});
    });
}


function populateUserInformation(data) {
    document.getElementById("name").value = data.name || "Onbekend";
    document.getElementById("email").value = data.email || "Onbekend";
    document.getElementById("phone").value = data.phone || "Niet opgegeven";
    document.getElementById("telegram").value = `${data.telegram_user?.first_name || "Onbekend"} ${data.telegram_user?.last_name || ""}`;
    document.getElementById("discord").value = `${data.discord_user?.username || "Onbekend"}`;

    if (data.discord_user && Object.keys(data.discord_user).length > 0) {
        document.getElementById("discord-login-button").style.display = "none";
        document.getElementById("unlink-discord").style.display = "inline-block";
    }

    if (data.telegram_user && Object.keys(data.telegram_user).length > 0) {
        document.getElementById("telegram-login-button").style.display = "none";
        document.getElementById("unlink-telegram").style.display = "inline-block";
    }
}

function populateUserPreferences(data) {

    document.querySelectorAll(`.dropdown-section`).forEach(element => {
        element.style.display = "block";
    });

    InitializeExamTypes(data)
    InitializeExamCenters(data)

    // Email notifications checkbox
    const emailCheckbox = document.getElementById("emailNotificationCheckbox");
    if (emailCheckbox) {
        emailCheckbox.checked = data.wants_emails || false;
    }
}

function InitializeExamTypes(data) {
    const licenseSelect = document.getElementById("Rijbewijzen");
    const selectedLicenses = data.monitoring_preferences.license_types.map(String);
    let selectedLicenseCount = 0;

    Array.from(licenseSelect.options).forEach((option) => {
        if (selectedLicenses.includes(option.value)) {
            option.selected = true;
            selectedLicenseCount++;
        } else {
            option.selected = false;
        }
    });
    document.getElementById("rijbewijzen-count").innerText = `${selectedLicenseCount} selected`;

    const updateRijbewijzenCount = (values) => {
        const count = values.length;
        document.getElementById("rijbewijzen-count").innerText = `${count} selected`;
    };

    new MultiSelectTag("Rijbewijzen", {
        rounded: true,
        shadow: true,
        disabled: true,
        placeholder: "Selecteer Rijbewijzen",
        onChange: updateRijbewijzenCount,
    });
}

function InitializeExamCenters(data) {
    const examCenterSelect = document.getElementById("Examencentra");
    const selectedCenters = data.monitoring_preferences.exam_center_ids.map(String);
    let selectedCenterCount = 0;

    Array.from(examCenterSelect.options).forEach((option) => {
        if (selectedCenters.includes(option.value)) {
            option.selected = true;
            selectedCenterCount++;
        } else {
            option.selected = false;
        }
    });
    document.getElementById("examencentra-count").innerText = `${selectedCenterCount} selected`;

    const updateExamencentraCount = (values) => {
        const count = values.length;
        document.getElementById("examencentra-count").innerText = `${count} selected`;
    };

    new MultiSelectTag("Examencentra", {
        rounded: true,
        shadow: true,
        placeholder: "Selecteer Examencentra",
        onChange: updateExamencentraCount,
    });
}


async function submitPreferences(token) {
    const selectedLicenseTypes = Array.from(
        document.querySelectorAll("#Rijbewijzen option:checked")
    ).map((option) => option.value);

    const selectedExamCenters = Array.from(
        document.querySelectorAll("#Examencentra option:checked")
    ).map((option) => option.value);

    const wantsEmails = document.getElementById("emailNotificationCheckbox").checked;

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