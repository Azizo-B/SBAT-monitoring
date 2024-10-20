document.addEventListener('DOMContentLoaded', function () {
    const urlParams = new URLSearchParams(window.location.search);
    const verificationToken = urlParams.get('verification_token');

    if (verificationToken) {
        fetch(`https://api.rijexamenmeldingen.be/auth/verify?verification_token=${verificationToken}`, {
            method: 'GET'
        })
            .then(response => {
                if (response.ok) {
                    setTimeout(function () {
                        window.location.href = '/login';
                    }, 500);
                } else {
                    document.getElementById('verification-status').innerText = 'Verification failed. Invalid or expired token.';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                document.getElementById('verification-status').innerText = 'An error occurred during verification.';
            });
    } else {
        document.getElementById('verification-status').innerText = 'A verification mail was sent to your mailbox.';
    }
});
