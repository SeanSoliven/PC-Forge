const errorMessage = document.getElementById('login-error');
const loginButton = document.getElementById('login-button');
const lockoutUntil = Number(errorMessage?.dataset.lockoutUntil || 0);

if (errorMessage && loginButton && lockoutUntil > 0) {
    loginButton.disabled = true;

    const updateCountdown = () => {
        const remaining = Math.max(0, Math.ceil(lockoutUntil - Date.now() / 1000));
        if (remaining === 0) {
            loginButton.disabled = false;
            errorMessage.hidden = true;
            return;
        }

        const minutes = String(Math.floor(remaining / 60)).padStart(2, '0');
        const seconds = String(remaining % 60).padStart(2, '0');
        errorMessage.textContent =
            `Too many failed login attempts. Please try again in ${minutes}:${seconds}.`;
        window.setTimeout(updateCountdown, 250);
    };

    updateCountdown();
}
