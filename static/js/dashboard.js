/* Amazi GIS map engine — Bugesera-scoped.
   Rebuilt from scratch: the map is locked to the case-study district
   (Bugesera) with a real district boundary overlay, risk-coloured marker
   clusters, search/status/risk/sector filters, rainfall overlay, and a
   live count bar. Data comes from window.AMAZI_MAP set by map.html. */
(function () {
    const mapEl = document.getElementById("map");
    const cfg = window.AMAZI_MAP;
    if (!mapEl || typeof L === "undefined" || !cfg || !Array.isArray(cfg.points)) return;

    const points = cfg.points;
    const district = cfg.district;
    const boundary = Array.isArray(cfg.boundary) ? cfg.boundary : [];

    const STATUS_COLORS = {
        "Functional": "#16794a",
        "At Risk": "#a8610c",
        "Non-Functional": "#a92b1d",
        "Under Repair": "#46799a"
    };

    const districtBounds = boundary.length
        ? L.latLngBounds(boundary.map(function (ll) { return [ll[0], ll[1]]; }))
        : L.latLngBounds([[latMin(), lngMin()], [latMax(), lngMax()]]);

    function latMin() { return Math.min.apply(null, points.map(function (p) { return p.lat; })); }
    function lngMin() { return Math.min.apply(null, points.map(function (p) { return p.lng; })); }
    function latMax() { return Math.max.apply(null, points.map(function (p) { return p.lat; })); }
    function lngMax() { return Math.max.apply(null, points.map(function (p) { return p.lng; })); }

    const map = L.map("map", {
        zoomControl: false,
        maxBounds: districtBounds.pad(0.12),
        maxBoundsViscosity: 1.0
    });
    L.control.zoom({ position: "bottomright" }).addTo(map);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors"
    }).addTo(map);

    // cluster layer with risk-aware colouring
    const clusterGroup = L.markerClusterGroup({
        showCoverageOnHover: false,
        maxClusterRadius: 42,
        iconCreateFunction: function (cluster) {
            let cls = "marker-cluster-amazi";
            const children = cluster.getAllChildMarkers();
            const crit = children.some(function (m) { return (m.__risk || 0) >= 0.66; });
            const atRisk = children.some(function (m) { return (m.__risk || 0) >= 0.33; });
            if (crit) cls += " is-crit";
            else if (atRisk) cls += " is-risk";
            const el = document.createElement("div");
            el.className = cls;
            el.style.width = el.style.height = "34px";
            el.textContent = cluster.getChildCount();
            return el;
        }
    });
    clusterGroup.addTo(map);

    // district boundary overlay
    const boundaryLayer = L.layerGroup();
    if (boundary.length) {
        L.polygon(boundary, {
            color: "#1b7f8e",
            weight: 2,
            dashArray: "6 5",
            fillColor: "#3da2b1",
            fillOpacity: 0.06,
            className: "bugesera-boundary"
        })
            .bindTooltip(district + " District", { sticky: true })
            .addTo(boundaryLayer);
    }
    boundaryLayer.addTo(map);

    const rainfallLayer = L.layerGroup();

    const buildDropletIcon = function (color) {
        const el = document.createElement("div");
        el.className = "amazi-pin";
        el.style.setProperty("--pin", color);
        return L.divIcon({
            className: "amazi-pin",
            html: el.outerHTML,
            iconSize: [26, 30],
            iconAnchor: [13, 28],
            popupAnchor: [0, -30]
        });
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
            (p.sector ? '<div class="pp-row"><span class="pp-k">Sector</span><span>' + p.sector + '</span></div>' : '') +
            '<div class="pp-row"><span class="pp-k">District</span><span>' + p.district + '</span></div>' +
            '<div style="margin-top:.5rem"><a href="' + "/dashboard/water-points/" + p.id + '">Open point →</a></div>' +
            '</div>'
        );
        return marker;
    };

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

    const renderRainfall = function () {
        rainfallLayer.clearLayers();
        points.forEach(function (p) { rainfallLayer.addLayer(rainfallFor(p)); });
    };

    // filtering
    const filter = { q: "", status: "", sector: "", minRisk: 0 };

    const countEl = function (id) { return document.getElementById(id); };

    const updateCounts = function (matched) {
        const shown = matched.length;
        const total = points.length;
        const num = function (status) {
            return matched.filter(function (p) { return p.status === status; }).length;
        };
        const set = function (id, v) {
            const el = countEl(id);
            if (el) el.textContent = v;
        };
        set("count-functional", num("Functional"));
        set("count-risk", num("At Risk"));
        set("count-nonfunc", num("Non-Functional"));
        set("count-repair", num("Under Repair"));
        const stat = countEl("map-count");
        if (stat) stat.textContent = total ? "Showing " + shown + " / " + total + " points" : "No water points";
    };

    const applyFilters = function () {
        clusterGroup.clearLayers();
        const matched = points.filter(function (p) {
            if (filter.status && p.status !== filter.status) return false;
            if (filter.sector && p.sector !== filter.sector) return false;
            if (p.risk < filter.minRisk) return false;
            if (filter.q) {
                const hay = (p.uid + " " + (p.technology || "") + " " + (p.district || "") + " " + (p.sector || "")).toLowerCase();
                if (hay.indexOf(filter.q.toLowerCase()) === -1) return false;
            }
            return true;
        });
        matched.forEach(function (p) { clusterGroup.addLayer(makeMarker(p)); });

        if (countEl("layer-rainfall") && countEl("layer-rainfall").checked) renderRainfall();

        updateCounts(matched);
        return matched;
    };

    const fitBounds = function (b, zoom) {
        if (b.isValid()) {
            map.fitBounds(b.pad(0.12), { maxZoom: zoom || 12, animate: false });
        } else {
            map.setView(districtBounds.getCenter(), 11);
        }
    };

    const fitDistrict = function () {
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
        fitBounds(districtBounds);
    };

    const refit = function (matched) {
        if (focusId) { fitDistrict(); return; }
        const markers = [];
        clusterGroup.eachLayer(function (layer) {
            if (layer instanceof L.Marker) markers.push(layer.getLatLng());
        });
        if (markers.length && (filter.q || filter.status || filter.sector || filter.minRisk > 0)) {
            fitBounds(L.latLngBounds(markers));
        } else {
            fitDistrict();
        }
    };

    // wire UI
    const q = document.getElementById("map-search");
    const status = document.getElementById("map-status");
    const risk = document.getElementById("map-risk");
    const sector = document.getElementById("map-sector");
    const reset = document.getElementById("map-reset");
    const layersToggle = document.getElementById("map-layers-toggle");
    const layerPanel = document.getElementById("map-layers");
    const recenter = document.getElementById("map-recenter");
    const cbPoints = document.getElementById("layer-points");
    const cbBoundary = document.getElementById("layer-boundary");
    const cbRain = document.getElementById("layer-rainfall");

    const refresh = function () {
        if (q) filter.q = q.value;
        if (status) filter.status = status.value;
        if (sector) filter.sector = sector.value;
        if (risk) filter.minRisk = parseFloat(risk.value) || 0;
        const matched = applyFilters();
        refit(matched);
    };

    const pendingRefit = (function () {
        let t = null;
        return function () {
            if (t) clearTimeout(t);
            t = setTimeout(function () { refit(applyFilters()); }, 300);
        };
    })();

    if (q) q.addEventListener("input", pendingRefit);
    if (status) status.addEventListener("change", refresh);
    if (risk) risk.addEventListener("change", refresh);
    if (sector) sector.addEventListener("change", refresh);
    if (reset) reset.addEventListener("click", function () {
        if (q) q.value = "";
        if (status) status.value = "";
        if (risk) risk.value = "0";
        if (sector) sector.value = "";
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
    if (cbBoundary) cbBoundary.addEventListener("change", function () {
        if (cbBoundary.checked) boundaryLayer.addTo(map); else map.removeLayer(boundaryLayer);
    });
    if (cbRain) cbRain.addEventListener("change", function () {
        if (cbRain.checked) { renderRainfall(); rainfallLayer.addTo(map); } else map.removeLayer(rainfallLayer);
    });
    if (recenter) recenter.addEventListener("click", function () { fitDistrict(); });

    applyFilters();
    fitDistrict();

    // ensure the map measures correctly after the layout settles
    if (window.requestAnimationFrame) {
        requestAnimationFrame(function () { map.invalidateSize(); });
    }
})();
