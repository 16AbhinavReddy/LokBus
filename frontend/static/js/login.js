const loginForm = document.getElementById("loginForm");
const message = document.getElementById("message");
loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;
    message.textContent = "";
    message.className = "message";
    const submitButton = loginForm.querySelector("button[type='submit']");
    submitButton.disabled = true;
    try {
        const response = await fetch("/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            credentials: "same-origin",
            body: JSON.stringify({
                username: username,
                password: password
            })
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Invalid username or password.");
        }
        message.textContent = "Login successful!";
        message.classList.add("success");
        window.location.href = "/home";
    } catch (error) {
        message.textContent = error.message;
        message.classList.add("error");
    } finally {
        submitButton.disabled = false;
    }
});
