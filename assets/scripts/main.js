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

  sendReferencePostRequest();
});

function collectTrackingInfo() {
  return {
    current_url: window.location.href,
    referrer: document.referrer || 'Direct Access',
    screen_width: window.screen.width,
    screen_height: window.screen.height,
  };
}
async function sendReferencePostRequest() {
  const data = collectTrackingInfo();
  try {
    const response = await fetch('https://api.rijexamenmeldingen.be/ref-webhook', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    });

    if (response.ok) {
      const result = await response.json();
      console.log('Success:', result);
    } else {
      console.error('Error:', response.status, response.statusText);
    }
  } catch (error) {
    console.error('Error making request:', error);
  }
}

function toggleFaqContent(button) {
  const content = button.nextElementSibling;
  const isOpen = button.classList.toggle("active");
  content.style.display = isOpen ? "block" : "none";
}