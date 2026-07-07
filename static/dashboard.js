document.addEventListener("DOMContentLoaded", async () => {
    AuthGuard.requireAuth();

    const user = await AuthGuard.fetchUser();
    if (!user) return;

    AuthGuard.setupSidebar();

    document.getElementById("welcome-msg").textContent =
        `Welcome Back, ${user.name.split(" ")[0]}`;

    // Fetch Stats
    try {
        const stats = await AuthGuard.apiCall("/rbac/stats");

        document.getElementById("stat-users").textContent = stats.total_users;
        document.getElementById("stat-admins").textContent = stats.total_admins;
        document.getElementById("stat-sessions").textContent = stats.active_sessions;
        document.getElementById("stat-reports").textContent = stats.reports_generated;
    } catch (error) {
        console.error("Failed to load stats", error);
    }

    // Render Chart
    const ctx = document.getElementById("activityChart").getContext("2d");

    new Chart(ctx, {
        type: "line",
        data: {
            labels: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            datasets: [
                {
                    label: "Logins",
                    data: [12, 19, 3, 5, 2, 3, 9],
                    borderColor: "#6366f1",
                    tension: 0.4,
                },
            ],
        },
        options: {
            plugins: {
                legend: {
                    display: false,
                },
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: "rgba(255,255,255,0.1)",
                    },
                },
                x: {
                    grid: {
                        display: false,
                    },
                },
            },
        },
    });
});