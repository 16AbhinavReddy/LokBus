const form = document.getElementById("reviewForm");
const bus_list = document.getElementById("reviewBus");
const status = document.getElementById("reviewStatus");

async function loadBuses() {
    try {
        const response = await fetch("/api/routes");
        if (response.status === 401) return window.location.assign("/login-page");
        const buses = await response.json();
        if (!response.ok) {
            throw new Error(buses.error || "Unable to load buses.");
        }
        bus_list.replaceChildren(new Option("Choose an operating bus", ""));
        for (let i = 0; i < buses.length; i++) {
            let bus = buses[i];

            if (bus.route_name && bus.vehicle_number) {
                let option = new Option(
                    bus.vehicle_number + " — Route " + bus.route_name,
                    bus.vehicle_number
                );

                bus_list.add(option);
            }
        }
        if (bus_list.options.length === 1) {
            status.textContent = "No operating buses are available right now.";
        }
    } catch (error) {
        bus_list.replaceChildren(new Option("Buses unavailable", ""));
        status.textContent = error.message;
    }
}

form.addEventListener("submit", async event => {
    event.preventDefault();
    const button = document.getElementById("submitReviewBtn");
    button.disabled = true;
    status.textContent = "Submitting your review...";
    try {
        const response = await fetch("/api/reviews", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                vehicle_number: bus_list.value,
                rating: document.getElementById("reviewRating").value || null,
                review: document.getElementById("reviewText").value
            })
        });
        const result = await response.json();
        if (response.status === 401) {
            return window.location.assign("/login-page");
        }
        if (!response.ok) {
            throw new Error(result.error || "Review submission failed.");
        }
        status.textContent = `Review #${result.review_id} submitted. Category: ${result.category}; sentiment: ${result.sentiment}.`;
        form.reset();
    } catch (error) {
        status.textContent = error.message;
    } finally {
        button.disabled = false;
    }
});

document.getElementById("logoutBtn").addEventListener("click", async () => {
    const response = await fetch("/logout", { method: "POST" });
    if (response.ok) {
        window.location.assign("/login-page");
    }
});

loadBuses();
