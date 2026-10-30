const registerForm = document.getElementById("registerForm");
const message = document.getElementById("message");

registerForm.addEventListener("submit", async (event) => {

    event.preventDefault();

    const fullName = document.getElementById("fullName").value.trim();
    const username = document.getElementById("username").value.trim();
    const email = document.getElementById("email").value.trim();

    const password = document.getElementById("password").value;
    const confirmPassword = document.getElementById("confirmPassword").value;

    message.textContent = "";
    message.className = "message";

    if (password !== confirmPassword) {
        message.textContent = "Passwords do not match.";
        message.classList.add("error");
        return;
    }

    if (password.length < 12) {
        message.textContent = "Password must contain at least 12 characters.";
        message.classList.add("error");
        return;
    }

    const submitButton = registerForm.querySelector("button[type='submit']");
    submitButton.disabled = true;

    try {

        const response = await fetch("/register", {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                full_name: fullName,
                username: username,
                email: email,
                password: password
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Registration failed.");
        }

        message.textContent = "Registration successful! Redirecting to login...";
        message.classList.add("success");

        setTimeout(() => {
            window.location.href = "/login-page";
        }, 1200);

    } catch (error) {

        message.textContent = error.message;
        message.classList.add("error");

    } finally {
        submitButton.disabled = false;
    }

});
