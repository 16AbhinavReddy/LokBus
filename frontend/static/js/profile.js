document.addEventListener("DOMContentLoaded", () => {
    loadProfile();

    document.getElementById("logoutBtn")
        .addEventListener("click", logout);
});


async function loadProfile() {

    try {
        const response = await fetch("/profile", {
            method: "GET",
            credentials: "same-origin"
        });

        if (response.status === 401) {
             document.getElementById("errorMessage").textContent =
                    "Please log in to view your profile information.";
             return;
        }

        if (!response.ok) {
            throw new Error("Failed to load profile");
        }

        const user = await response.json();

        document.getElementById("displayName").textContent =
            user.full_name;

        document.getElementById("displayUsername").textContent =
            "@" + user.username;

        document.getElementById("fullName").textContent =
            user.full_name;

        document.getElementById("username").textContent =
            user.username;

        document.getElementById("email").textContent =
            user.email;

        const date = new Date(user.created_at);

        document.getElementById("createdAt").textContent =
            date.toLocaleDateString();

        document.getElementById("avatar").textContent =
            user.full_name.charAt(0).toUpperCase();

    } catch (error) {
        console.error(error);

        document.getElementById("errorMessage").textContent =
            "Unable to load profile information.";
    }
}


async function logout() {

    try {
        const response = await fetch("/logout", {
            method: "POST",
            credentials: "same-origin"
        });

        if (!response.ok) {
            throw new Error("Logout failed");
        }

        window.location.href = "/login-page";

    } catch (error) {
        alert("Unable to log out. Please try again.");
    }
}
