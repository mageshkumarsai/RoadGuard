// RoadGuard Leaflet map for the provider dashboard and the /map/ page.
// Reads JSON from <script id="map-data" type="application/json"> and draws
// markers. Popups are built with DOM nodes (textContent) so user-entered text
// can never inject HTML.
(function () {
  const holder = document.getElementById("map-data");
  const el = document.getElementById("providerMap");
  if (!holder || !el || typeof L === "undefined") return;

  const data = JSON.parse(holder.textContent);
  const map = L.map(el).setView([11.1271, 78.6569], 7); // Tamil Nadu

  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map);

  const bounds = [];

  function line(parent, label, value) {
    const row = document.createElement("div");
    if (label) {
      const b = document.createElement("strong");
      b.textContent = label + " ";
      row.appendChild(b);
    }
    row.appendChild(document.createTextNode(value));
    parent.appendChild(row);
  }

  function colored(color) {
    return L.divIcon({
      className: "",
      html: '<span style="display:block;width:18px;height:18px;border-radius:50%;background:' + color +
            ';border:3px solid #fff;box-shadow:0 1px 6px rgba(0,0,0,.5)"></span>',
      iconSize: [18, 18],
      iconAnchor: [9, 9],
    });
  }

  function requestPopup(r) {
    const box = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = "Request #" + r.id + " · " + r.service;
    box.appendChild(title);
    line(box, "Vehicle:", r.vehicle);
    line(box, "Issue:", r.issue);
    if (r.location) line(box, "Location:", r.location);
    line(box, "GPS:", r.lat.toFixed(6) + ", " + r.lng.toFixed(6));
    if (r.distance !== null && r.distance !== undefined) line(box, "Distance:", r.distance + " km away");
    const a = document.createElement("a");
    a.href = r.url;
    a.textContent = "View details →";
    box.appendChild(a);
    return box;
  }

  if (data.mode === "provider") {
    if (data.center) {
      L.marker(data.center, { icon: colored("#1769aa") })
        .addTo(map)
        .bindPopup("Your service location");
      L.circle(data.center, {
        radius: data.radius_km * 1000,
        color: "#1769aa",
        weight: 1,
        fillOpacity: 0.06,
      }).addTo(map);
      bounds.push(data.center);
    }
    (data.requests || []).forEach((r) => {
      if (r.lat === null || r.lng === null) return;
      L.marker([r.lat, r.lng], { icon: colored("#e0a100") }).addTo(map).bindPopup(requestPopup(r));
      bounds.push([r.lat, r.lng]);
    });
    (data.assigned || []).forEach((r) => {
      L.marker([r.lat, r.lng], { icon: colored("#19a974") }).addTo(map).bindPopup(requestPopup(r));
      bounds.push([r.lat, r.lng]);
    });
  } else {
    (data.providers || []).forEach((p) => {
      const box = document.createElement("div");
      const t = document.createElement("strong");
      t.textContent = p.name;
      box.appendChild(t);
      line(box, "", p.service);
      line(box, "Phone:", p.phone);
      L.marker([p.lat, p.lng]).addTo(map).bindPopup(box);
      bounds.push([p.lat, p.lng]);
    });
  }

  if (bounds.length > 1) map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
  else if (bounds.length === 1) map.setView(bounds[0], 13);

  // Maps inside hidden/resizing containers need a size refresh.
  setTimeout(() => map.invalidateSize(), 200);
})();
