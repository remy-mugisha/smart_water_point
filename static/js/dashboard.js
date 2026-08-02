/* Amazi GIS map engine.
   Droplet markers, marker clusters, status/district/risk filters,
   district footprints, rainfall overlay, and detail popups. */
(function () {
    const mapEl = document.getElementById("map");
    if (!mapEl || typeof L === "undefined" || typeof points === "undefined") return;

    const STATUS_COLORS = {
        "Functional": "#16794a",
        "At Risk": "#a8610c",
        "Non-Functional": "#a92b1d",
        "Under Repair": "#46799a"
    };

    const map = L.map("map", { zoomControl: false });
    L.control.zoom({ position: "bottomright" }).addTo(map);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors"
    }).addTo(map);

    const clusterGroup = L.markerClusterGroup({
        showCoverageOnHover: false,
        maxClusterRadius: 42,
        iconCreateFunction: function (cluster) {
            let cls = "marker-cluster-amazi";
            const children = cluster.getAllChildMarkers();
            const riskCount = children.filter(function (m) { return (m.__risk || 0) >= 0.33; }).length;
            const critCount = children.filter(function (m) { return (m.__risk || 0) >= 0.66; }).length;
            if (critCount > 0) cls += " is-crit";
            else if (riskCount > 0) cls += " is-risk";
            const el = document.createElement("div");
            el.className = cls;
            el.style.width = el.style.height = "34px";
            el.textContent = cluster.getChildCount();
            return el;
        }
    });
    clusterGroup.addTo(map);

    const footprintLayer = L.layerGroup().addTo(map);
    const rainfallLayer = L.layerGroup();

    const buildDropletIcon = function (color) {
        const el = document.createElement("div");
        el.className = "amazi-pin";
        el.style.setProperty("--pin", color);
        return L.divIcon({ className: "amazi-pin", html: el.outerHTML, iconSize: [26, 30], iconAnchor: [13, 28], popupAnchor: [0, -30] });
    };

    const makeMarker = function (p) {
        const color = STATUS_COLORS[p.status] || "#1b7f8e";
        const marker = L.marker([p.lat, p.lng], { icon: buildDropletIcon(color), title: p.uid });
        marker.__risk = p.risk;
        marker.__data = p;
        marker.bindPopup(
            '<div class="map-popup">' +
            '<div class="pp-id">' + p.uid + '</div>' +
            '<div class="pp-row"><span class="pp-k">Status</span><span style="color:' + color + ';font-weight:600">' + p.status + '</span></div>' +
            '<div class="pp-row"><span class="pp-k">Risk</span><span>' + Math.round(p.risk * 100) + '%</span></div>' +
            '<div class="pp-row"><span class="pp-k">Technology</span><span>' + p.technology + '</span></div>' +
            '<div class="pp-row"><span class="pp-k">District</span><span>' + p.district + '</span></div>' +
            '<div style="margin-top:.5rem"><a href="' + "/dashboard/water-points/" + p.id + '">Open point →</a></div>' +
            '</div>'
        );
        return marker;
    };

    // district footprints: dashed coverage ring around each district centroid
    const footprintFor = function (districtPoints) {
        const n = districtPoints.length;
        if (!n) return null;
        let cx = 0, cy = 0;
        districtPoints.forEach(function (p) { cx += p.lat; cy += p.lng; });
        cx /= n; cy /= n;
        let radius = 0;
        districtPoints.forEach(function (p) {
            const d = map.distance([cx, cy], [p.lat, p.lng]);
            if (d > radius) radius = d;
        });
        radius = Math.max(radius + 3000, 8000);
        return L.circle([cx, cy], {
            radius: radius,
            color: "#1b7f8e",
            weight: 1.5,
            dashArray: "4 6",
            fillColor: "#3da2b1",
            fillOpacity: 0.05,
            className: "footprint-circle"
        }).bindTooltip(districtPoints[0].district, { permanent: false });
    };

    // rainfall overlay: translucent halos sized by mm/month
    const rainfallFor = function (p) {
        const mm = p.rainfall || 0;
        const r = Math.min(1200 + mm * 30, 6000);
        return L.circle([p.lat, p.lng], {
            radius: r,
            color: "#1b7f8e",
            weight: 1,
            fillColor: "#3da2b1",
            fillOpacity: 0.18
        }).bindTooltip(p.uid + " · " + Math.round(mm) + " mm/mo");
    };

    const renderFootprints = function () {
        footprintLayer.clearLayers();
        const byDistrict = {};
        points.forEach(function (p) {
            (byDistrict[p.district] = byDistrict[p.district] || []).push(p);
        });
        Object.keys(byDistrict).forEach(function (name) {
            const ring = footprintFor(byDistrict[name]);
            if (ring) footprintLayer.addLayer(ring);
        });
    };

    const renderRainfall = function () {
        rainfallLayer.clearLayers();
        points.forEach(function (p) { rainfallLayer.addLayer(rainfallFor(p)); });
    };

    // filtering
    let filter = { q: "", status: "", district: "", minRisk: 0 };

    const applyFilters = function () {
        clusterGroup.clearLayers();
        const matched = points.filter(function (p) {
            if (filter.status && p.status !== filter.status) return false;
            if (filter.district && p.district !== filter.district) return false;
            if (p.risk < filter.minRisk) return false;
            if (filter.q) {
                const hay = (p.uid + " " + p.technology + " " + p.district).toLowerCase();
                if (hay.indexOf(filter.q.toLowerCase()) === -1) return false;
            }
            return true;
        });
        matched.forEach(function (p) { clusterGroup.addLayer(makeMarker(p)); });

        if (document.getElementById("layer-footprints") && document.getElementById("layer-footprints").checked) {
            renderFootprints();
        }
        if (document.getElementById("layer-rainfall") && document.getElementById("layer-rainfall").checked) {
            renderRainfall();
        }

        const any = matched.length || points.length;
        return matched;
    };

    const fit = function () {
        if (focusId) {
            const p = points.find(function (x) { return x.id === focusId; });
            if (p) {
                map.setView([p.lat, p.lng], 14);
                clusterGroup.eachLayer(function (layer) {
                    if (layer instanceof L.Marker && layer.__data && layer.__data.id === focusId) {
                        layer.openPopup();
                    }
                });
                return;
            }
        }
        const markers = [];
        clusterGroup.eachLayer(function (layer) {
            if (layer instanceof L.Marker) markers.push([layer.getLatLng().lat, layer.getLatLng().lng]);
        });
        if (markers.length) {
            map.fitBounds(L.latLngBounds(markers).pad(0.15), { maxZoom: 11 });
        } else {
            map.setView([-1.95, 29.87], 8);
        }
    };

    // wire UI
    const wire = function () {
        const q = document.getElementById("map-search");
        const status = document.getElementById("map-status");
        const district = document.getElementById("map-district");
        const reset = document.getElementById("map-reset");
        const layersToggle = document.getElementById("map-layers-toggle");
        const layerPanel = document.getElementById("map-layers");
        const recenter = document.getElementById("map-recenter");
        const cbPoints = document.getElementById("layer-points");
        const cbFoot = document.getElementById("layer-footprints");
        const cbRain = document.getElementById("layer-rainfall");

        const refresh = function () {
            if (q) filter.q = q.value;
            if (status) filter.status = status.value;
            if (district) filter.district = district.value;
            filter.minRisk = 0;
            applyFilters();
        };

        if (q) q.addEventListener("input", refresh);
        if (status) status.addEventListener("change", refresh);
        if (district) district.addEventListener("change", refresh);
        if (reset) reset.addEventListener("click", function () {
            if (q) q.value = ""; if (status) status.value = ""; if (district) district.value = "";
            refresh();
        });

        if (layersToggle && layerPanel) {
            layersToggle.addEventListener("click", function () {
                const open = layerPanel.classList.toggle("is-open");
                layersToggle.setAttribute("aria-expanded", open ? "true" : "false");
            });
        }
        if (cbPoints) cbPoints.addEventListener("change", function () {
            if (cbPoints.checked) clusterGroup.addTo(map); else map.removeLayer(clusterGroup);
        });
        if (cbFoot) cbFoot.addEventListener("change", function () {
            if (cbFoot.checked) { renderFootprints(); footprintLayer.addTo(map); } else map.removeLayer(footprintLayer);
        });
        if (cbRain) cbRain.addEventListener("change", function () {
            if (cbRain.checked) { renderRainfall(); rainfallLayer.addTo(map); } else map.removeLayer(rainfallLayer);
        });
        if (recenter) recenter.addEventListener("click", fit);
    };

    applyFilters();
    wire();
    fit();
})();
