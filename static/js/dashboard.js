(function () {
    const mapEl = document.getElementById("map");
    if (!mapEl || typeof L === "undefined") {
        return;
    }

    const map = L.map("map").setView([-1.95, 30.06], 8);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors"
    }).addTo(map);

    const bounds = [];
    const colors = {
        "Functional": "#16a34a",
        "At Risk": "#d97706",
        "Non-Functional": "#dc2626",
        "Under Repair": "#2563eb"
    };

    points.forEach((point) => {
        const marker = L.circleMarker([point.lat, point.lng], {
            radius: 8,
            color: colors[point.status] || "#2563eb",
            fillColor: colors[point.status] || "#2563eb",
            fillOpacity: 0.8,
            weight: 2
        }).addTo(map);
        marker.bindPopup(
            `<strong>${point.id}</strong><br>${point.technology}<br>${point.status}<br>Risk: ${Math.round(point.risk * 100)}%`
        );
        bounds.push([point.lat, point.lng]);
    });

    if (bounds.length > 0) {
        map.fitBounds(bounds, { padding: [24, 24] });
    }
})();
