(function () {
    window.ReportCharts = window.ReportCharts || {};

    // Matches the status colors used on the map (static/js/dashboard.js) so
    // the same status reads the same color everywhere in the app.
    const LABEL_COLORS = {
        "Functional": "#16a34a",
        "At Risk": "#d97706",
        "Non-Functional": "#dc2626",
        "Under Repair": "#2563eb",
        "Low": "#16a34a",
        "Medium": "#d97706",
        "High": "#dc2626"
    };
    const PALETTE = ["#0f6f8f", "#16a34a", "#d97706", "#dc2626", "#2563eb", "#7c3aed", "#0891b2"];

    function colorFor(label, index) {
        return LABEL_COLORS[label] || PALETTE[index % PALETTE.length];
    }

    window.ReportCharts.renderPie = function (canvasId, chartData) {
        const ctx = document.getElementById(canvasId);
        if (!ctx || typeof Chart === "undefined") return;
        const labels = chartData.labels;
        const values = chartData.datasets[0].values;
        new Chart(ctx, {
            type: "pie",
            data: { labels: labels, datasets: [{ data: values, backgroundColor: labels.map(colorFor) }] },
            options: { responsive: true, plugins: { legend: { position: "bottom" } } }
        });
    };

    window.ReportCharts.renderBar = function (canvasId, chartData) {
        const ctx = document.getElementById(canvasId);
        if (!ctx || typeof Chart === "undefined") return;
        new Chart(ctx, {
            type: "bar",
            data: {
                labels: chartData.labels,
                datasets: chartData.datasets.map((ds, i) => ({
                    label: ds.label,
                    data: ds.values,
                    backgroundColor: colorFor(ds.label, i)
                }))
            },
            options: { responsive: true, plugins: { legend: { position: "bottom" } } }
        });
    };

    window.ReportCharts.renderLine = function (canvasId, chartData) {
        const ctx = document.getElementById(canvasId);
        if (!ctx || typeof Chart === "undefined") return;
        new Chart(ctx, {
            type: "line",
            data: {
                labels: chartData.labels,
                datasets: chartData.datasets.map((ds, i) => ({
                    label: ds.label,
                    data: ds.values,
                    borderColor: colorFor(ds.label, i),
                    backgroundColor: colorFor(ds.label, i),
                    tension: 0.3,
                    fill: false
                }))
            },
            options: { responsive: true, plugins: { legend: { position: "bottom" } } }
        });
    };
})();
