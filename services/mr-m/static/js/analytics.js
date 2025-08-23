(() => {
  // Ping
  fetch("/api/log-visit", { method: "POST" });

  // ---------- Country name normalization ----------
  // Canonicalize text: remove diacritics, punctuation, spaces, lower-case.
  const canon = (s) =>
    (s || "")
      .normalize("NFD")
      .replace(/\p{Diacritic}/gu, "")
      .toLowerCase()
      .replace(/[\s'’`"().,-]/g, "")
      .trim();

  // Map common analytics-country names -> GeoJSON names (canonicalized)
  const CANON_ALIAS = {};
  const aliasPairs = {
    "United States": "United States of America",
    Russia: "Russian Federation",
    Vietnam: "Viet Nam",
    Iran: "Iran, Islamic Republic of",
    Syria: "Syrian Arab Republic",
    "South Korea": "Korea, Republic of",
    "North Korea": "Korea, Democratic People's Republic of",
    Venezuela: "Venezuela, Bolivarian Republic of",
    Tanzania: "United Republic of Tanzania",
    Moldova: "Moldova, Republic of",
    Bolivia: "Bolivia, Plurinational State of",
    Brunei: "Brunei Darussalam",
    "Congo (Kinshasa)": "Congo, the Democratic Republic of the",
    "Congo (Brazzaville)": "Congo",
    "Ivory Coast": "Côte d'Ivoire",
    "Cape Verde": "Cabo Verde",
    Czechia: "Czech Republic",
    Swaziland: "Eswatini",
    Palestine: "Palestine, State of",
    Laos: "Lao People's Democratic Republic",
    Macau: "Macao",
    Micronesia: "Micronesia, Federated States of",
    Reunion: "Réunion"
  };
  Object.keys(aliasPairs).forEach((k) => {
    CANON_ALIAS[canon(k)] = canon(aliasPairs[k]);
  });

  const countryCounts = {}; // keyed by canonical country name

  // ---------- Map (Leaflet choropleth) ----------
  function getColor(d) {
    return d > 50 ? "#7F0000" :
           d > 20 ? "#B30000" :
           d > 10 ? "#E34A33" :
           d > 5  ? "#FC8D59" :
           d > 1  ? "#FDBB84" :
           d > 0  ? "#FDD49E" :
                    "#FFFFCC";
  }

  function loadChoroplethMap() {
    const mapEl = document.getElementById("map");
    if (!mapEl) return;

    const map = L.map("map").setView([25, 0], 2);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors"
    }).addTo(map);

    // GeoJSON path (kept as a static URL since this file is static JS)
    fetch("/static/data/world-countries.geo.json")
      .then((res) => res.json())
      .then((geo) => {
        L.geoJson(geo, {
          style: (feature) => {
            const key = canon(feature?.properties?.name || "");
            const visits = countryCounts[key] || 0;
            return {
              fillColor: getColor(visits),
              weight: 1,
              opacity: 1,
              color: "white",
              dashArray: "3",
              fillOpacity: 0.7
            };
          },
          onEachFeature: (feature, layer) => {
            const key = canon(feature?.properties?.name || "");
            const visits = countryCounts[key] || 0;
            layer.bindPopup(`${feature.properties.name}: ${visits} visit(s)`);
          }
        }).addTo(map);

        // Legend
        const legend = L.control({ position: "bottomright" });
        legend.onAdd = function () {
          const div = L.DomUtil.create("div", "info legend");
          const grades = [0, 1, 5, 10, 20, 50];
          const labels = [];
          for (let i = 0; i < grades.length; i++) {
            const from = grades[i];
            const to = grades[i + 1];
            labels.push(
              `<i style="background:${getColor(from + 1)}"></i> ${from}${to ? "&ndash;" + to : "+"}`
            );
          }
          div.innerHTML = labels.join("<br>");
          return div;
        };
        legend.addTo(map);

        setTimeout(() => map.invalidateSize(), 300);
      });
  }

  // ---------- Fetch visit list (for map counts) ----------
  fetch("/api/analytics-data")
    .then((res) => res.json())
    .then((visits) => {
      visits.forEach(({ country }) => {
        if (!country || country === "Unknown") return;
        let k = canon(country);
        if (CANON_ALIAS[k]) k = CANON_ALIAS[k];
        countryCounts[k] = (countryCounts[k] || 0) + 1;
      });
      loadChoroplethMap();
    });

  // ---------- Charts / summary ----------
  fetch("/api/analytics-summary")
    .then((res) => res.json())
    .then((data) => {
      // Totals
      document.getElementById("total-visits").textContent = data.total_visits;
      document.getElementById("vpn-count").textContent = data.vpn_count;
      document.getElementById("unknown-country-count").textContent =
        data.unknown_country_count;
      document.getElementById("top-page").textContent =
        data.most_visited_path || "Unavailable";

      // Device pie
      const deviceCtx = document.getElementById("deviceChart").getContext("2d");
      new Chart(deviceCtx, {
        type: "pie",
        data: {
          labels: Object.keys(data.by_device),
          datasets: [
            {
              label: "Device Type",
              data: Object.values(data.by_device)
            }
          ]
        },
        options: { responsive: false, maintainAspectRatio: false }
      });

      // Daily line
      const dailyCtx = document.getElementById("dailyChart").getContext("2d");
      const days = Object.keys(data.by_day).sort();
      new Chart(dailyCtx, {
        type: "line",
        data: {
          labels: days,
          datasets: [
            {
              label: "Visits per Day",
              data: days.map((d) => data.by_day[d]),
              fill: false,
              tension: 0.2
            }
          ]
        }
      });

      // Page popularity (click to navigate)
      const tabToPath = {
        Home: "/",
        Projects: "/projects",
        Research: "/research",
        Talks: "/talks",
        "Ask Mr M": "/ask-mr-m",
        Analytics: "/analytics",
        Contact: "/contact"
      };
      const pageCtx = document.getElementById("pageChart").getContext("2d");
      const pages = Object.keys(data.by_tab);
      const pageCounts = Object.values(data.by_tab);
      new Chart(pageCtx, {
        type: "bar",
        data: {
          labels: pages,
          datasets: [
            {
              label: "Visits per Tab",
              data: pageCounts,
              backgroundColor: "rgba(54, 162, 235, 0.6)"
            }
          ]
        },
        options: {
          onClick: (e, el) => {
            if (el.length) {
              const label = pages[el[0].index];
              const path = tabToPath[label];
              if (path) window.location.href = path;
            }
          },
          onHover: (evt, el) => {
            evt.native.target.style.cursor = el.length ? "pointer" : "default";
          },
          responsive: true,
          scales: { y: { beginAtZero: true } }
        }
      });

      // Toggle chart (device / country)
      const groupCtx = document.getElementById("groupChart").getContext("2d");
      let currentChart;
      function renderGroupChart(key) {
        if (currentChart) currentChart.destroy();
        const ds = data[key];
        currentChart = new Chart(groupCtx, {
          type: "bar",
          data: {
            labels: Object.keys(ds),
            datasets: [
              {
                label: `Visits by ${key === "by_device" ? "Device" : "Country"}`,
                data: Object.values(ds),
                backgroundColor: "rgba(255, 99, 132, 0.6)"
              }
            ]
          },
          options: { responsive: true, scales: { y: { beginAtZero: true } } }
        });
      }
      document
        .getElementById("groupFilter")
        .addEventListener("change", (e) => renderGroupChart(e.target.value));
      renderGroupChart("by_device");
    });
})();
