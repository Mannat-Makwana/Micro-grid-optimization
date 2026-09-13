(() => {
  const colors = {
    demand: "#182126",
    renewable: "#2e7d5b",
    solar: "#e9a72b",
    wind: "#3578b8",
    fixed: "#65727a",
    flexible: "#7561a8",
    surplus: "#77a98b",
    temperature: "#d26c4d",
    humidity: "#7561a8",
    cloud: "#8d9ba3",
    irradiance: "#e9a72b",
    rain: "#4d9bc2",
  };

  const charts = {};
  let forecastRetryTimer;

  function isNumber(value) {
    return value !== null && value !== "" && Number.isFinite(Number(value));
  }

  function values(series) {
    return (series || []).filter(isNumber).map(Number);
  }

  function stats(series) {
    const clean = values(series);
    if (!clean.length) return { current: null, peak: null, average: null, total: null };
    return {
      current: isNumber(series?.[0]) ? Number(series[0]) : null,
      peak: Math.max(...clean),
      average: clean.reduce((sum, value) => sum + value, 0) / clean.length,
      total: clean.reduce((sum, value) => sum + value, 0),
    };
  }

  function formatValue(value, unit = "") {
    return isNumber(value) ? `${Number(value).toFixed(1)}${unit}` : "—";
  }

  function parseTimestamp(value, timezone) {
    if (!value) return null;
    const source = String(value);
    if (/[zZ]|[+-]\d{2}:?\d{2}$/.test(source)) return new Date(source);
    const offset = timezone === "Asia/Kolkata" ? "+05:30" : "Z";
    return new Date(`${source}${offset}`);
  }

  function formatDateTime(value, timezone) {
    const date = parseTimestamp(value, timezone);
    if (!date || Number.isNaN(date.getTime())) return "—";
    return new Intl.DateTimeFormat("en-IN", {
      timeZone: timezone,
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(date);
  }

  function formatAxis(value, timezone) {
    const date = parseTimestamp(value, timezone);
    if (!date || Number.isNaN(date.getTime())) return "";
    return new Intl.DateTimeFormat("en-IN", {
      timeZone: timezone,
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(date);
  }

  function formatRange(start, end, timezone) {
    if (!start || !end) return "—";
    return `${formatDateTime(start, timezone)} → ${formatDateTime(end, timezone)}`;
  }

  function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
  }

  function setStats(prefix, series) {
    const result = stats(series);
    setText(`${prefix}Current`, formatValue(result.current, " kW"));
    setText(`${prefix}Peak`, formatValue(result.peak, " kW"));
    setText(`${prefix}Avg`, formatValue(result.average, " kW"));
  }

  function chartOptions(yTitle) {
    return {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          position: "bottom",
          labels: { boxWidth: 10, usePointStyle: true, font: { size: 10 } },
        },
        tooltip: {
          callbacks: {
            label(context) {
              const value = context.parsed.y;
              return `${context.dataset.label}: ${formatValue(value, " kW")}`;
            },
          },
        },
      },
      scales: {
        x: {
          type: "category",
          grid: { display: false },
          ticks: { maxTicksLimit: 14, font: { size: 10 } },
        },
        y: {
          beginAtZero: true,
          title: { display: true, text: yTitle },
          ticks: { font: { size: 10 } },
        },
      },
    };
  }

  const forecastBoundaryPlugin = {
    id: "forecastBoundary",
    afterDraw(chart, _args, options) {
      if (!options || options.index === undefined || !chart.chartArea) return;
      const x = chart.scales.x.getPixelForValue(options.index);
      const { top, bottom } = chart.chartArea;
      const context = chart.ctx;
      context.save();
      context.strokeStyle = "#2e7d5b";
      context.setLineDash([4, 4]);
      context.lineWidth = 1.25;
      context.beginPath();
      context.moveTo(x, top);
      context.lineTo(x, bottom);
      context.stroke();
      context.setLineDash([]);
      context.fillStyle = "#2e7d5b";
      context.font = "600 10px Inter, sans-serif";
      context.fillText("Forecast", Math.min(x + 6, chart.width - 58), top + 13);
      context.restore();
    },
  };

  function pairedDataset(label, color, historySeries, forecastSeries, historyLength) {
    return [
      {
        label: `${label} · history`,
        data: [...(historySeries || []), ...Array(forecastSeries.length).fill(null)],
        borderColor: color,
        backgroundColor: "transparent",
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.25,
        spanGaps: false,
      },
      {
        label: `${label} · next 24h`,
        data: [...Array(historyLength).fill(null), ...(forecastSeries || [])],
        borderColor: color,
        backgroundColor: "transparent",
        borderWidth: 2,
        borderDash: [7, 5],
        pointRadius: 0,
        tension: 0.25,
        spanGaps: false,
      },
    ];
  }

  function drawContextChart(forecast) {
    if (charts.context) charts.context.destroy();
    const history = forecast.history;
    const timestamps = [...history.timestamps, ...forecast.timestamps];
    const labels = timestamps.map((value) => formatAxis(value, forecast.timezone));
    const datasets = [
      ...pairedDataset("Demand", colors.demand, history.demand, forecast.demand, history.timestamps.length),
      ...pairedDataset("Renewable", colors.renewable, history.renewable, forecast.renewable, history.timestamps.length),
      ...pairedDataset("Solar", colors.solar, history.solar, forecast.solar, history.timestamps.length),
      ...pairedDataset("Wind", colors.wind, history.wind, forecast.wind, history.timestamps.length),
    ];
    const options = chartOptions("Power (kW)");
    options.plugins.forecastBoundary = { index: history.timestamps.length - 0.5 };
    charts.context = new Chart(document.getElementById("forecastContextChart"), {
      type: "line",
      data: { labels, datasets },
      plugins: [forecastBoundaryPlugin],
      options,
    });
  }

  function drawDetailChart(forecast) {
    if (charts.detail) charts.detail.destroy();
    const labels = forecast.timestamps.map((value) => formatAxis(value, forecast.timezone));
    const datasets = [
      { label: "Demand", data: forecast.demand, borderColor: colors.demand, borderWidth: 2.5, pointRadius: 0, tension: 0.3 },
      { label: "Fixed load", data: forecast.fixedLoad, borderColor: colors.fixed, borderDash: [3, 3], pointRadius: 0, tension: 0.3 },
      { label: "Flexible baseline", data: forecast.flexibleLoadBaseline, borderColor: colors.flexible, borderDash: [7, 4], pointRadius: 0, tension: 0.3 },
      { label: "Renewable available", data: forecast.renewable, borderColor: colors.renewable, borderWidth: 2.5, pointRadius: 0, tension: 0.3 },
      { label: "Solar available", data: forecast.solar, borderColor: colors.solar, pointRadius: 0, tension: 0.3 },
      { label: "Wind available", data: forecast.wind, borderColor: colors.wind, pointRadius: 0, tension: 0.3 },
      { label: "Renewable surplus", data: forecast.renewableSurplus, borderColor: colors.surplus, borderDash: [2, 3], pointRadius: 0, tension: 0.3 },
    ];
    charts.detail = new Chart(document.getElementById("forecastDetailChart"), {
      type: "line",
      data: { labels, datasets },
      options: chartOptions("Power (kW)"),
    });
  }

  function drawWeatherChart(forecast) {
    if (charts.weather) charts.weather.destroy();
    const weather = forecast.weather;
    const canvas = document.getElementById("weatherChart");
    const empty = document.getElementById("weatherUnavailable");
    if (!weather.available) {
      canvas.hidden = true;
      empty.hidden = false;
      return;
    }
    canvas.hidden = false;
    empty.hidden = true;
    const labels = forecast.timestamps.map((value) => formatAxis(value, forecast.timezone));
    charts.weather = new Chart(canvas, {
      data: {
        labels,
        datasets: [
          { type: "line", label: "Temperature (°C)", data: weather.temperature, borderColor: colors.temperature, yAxisID: "temperature", pointRadius: 0, tension: 0.3 },
          { type: "line", label: "Humidity (%)", data: weather.humidity, borderColor: colors.humidity, yAxisID: "percent", pointRadius: 0, tension: 0.3 },
          { type: "line", label: "Cloud cover (%)", data: weather.cloudCover, borderColor: colors.cloud, yAxisID: "percent", borderDash: [4, 3], pointRadius: 0, tension: 0.3 },
          { type: "line", label: "Wind speed (m/s)", data: weather.windSpeed, borderColor: colors.wind, yAxisID: "wind", pointRadius: 0, tension: 0.3 },
          { type: "line", label: "GHI (W/m²)", data: weather.ghi, borderColor: colors.irradiance, yAxisID: "irradiance", pointRadius: 0, tension: 0.3 },
          { type: "line", label: "DNI (W/m²)", data: weather.dni, borderColor: "#c77d2a", yAxisID: "irradiance", borderDash: [6, 3], pointRadius: 0, tension: 0.3 },
          { type: "line", label: "DHI (W/m²)", data: weather.dhi, borderColor: "#b9a35e", yAxisID: "irradiance", borderDash: [2, 3], pointRadius: 0, tension: 0.3 },
          { type: "bar", label: "Precipitation (mm)", data: weather.precipitation, backgroundColor: "rgba(77,155,194,.28)", borderColor: colors.rain, yAxisID: "rain", borderWidth: 1 },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { position: "bottom", labels: { boxWidth: 10, usePointStyle: true, font: { size: 10 } } },
          tooltip: { callbacks: { title: (items) => items.length ? formatDateTime(forecast.timestamps[items[0].dataIndex], forecast.timezone) : "" } },
        },
        scales: {
          x: { grid: { display: false }, ticks: { maxTicksLimit: 12, font: { size: 10 } } },
          temperature: { position: "left", title: { display: true, text: "Temperature (°C)" } },
          percent: { position: "right", min: 0, max: 100, grid: { drawOnChartArea: false }, title: { display: true, text: "%" } },
          wind: { display: false, min: 0 },
          irradiance: { display: false, min: 0 },
          rain: { display: false, min: 0 },
        },
      },
    });
  }

  function showView(view, forecast) {
    document.querySelectorAll("[data-view-panel]").forEach((panel) => {
      panel.hidden = panel.dataset.viewPanel !== view;
    });
    document.querySelectorAll("[data-forecast-view]").forEach((button) => {
      const active = button.dataset.forecastView === view;
      button.classList.toggle("active", active);
      button.setAttribute("aria-selected", String(active));
    });
    if (typeof Chart !== "function") return;
    if (view === "horizon" && !charts.detail) drawDetailChart(forecast);
    if (view === "weather" && !charts.weather) drawWeatherChart(forecast);
  }

  function tableValue(value, unit = "") {
    return isNumber(value) ? `${Number(value).toFixed(1)}${unit}` : "—";
  }

  function populateTable(forecast) {
    const body = document.getElementById("forecastRows");
    const weather = forecast.weather;
    body.innerHTML = forecast.timestamps.map((timestamp, index) => `
      <tr>
        <td>${formatDateTime(timestamp, forecast.timezone)}</td>
        <td>${tableValue(forecast.demand[index], " kW")}</td>
        <td>${tableValue(forecast.fixedLoad[index], " kW")}</td>
        <td>${tableValue(forecast.flexibleLoadBaseline[index], " kW")}</td>
        <td>${tableValue(forecast.solar[index], " kW")}</td>
        <td>${tableValue(forecast.wind[index], " kW")}</td>
        <td>${tableValue(forecast.renewable[index], " kW")}</td>
        <td>${tableValue(forecast.renewableSurplus[index], " kW")}</td>
        <td>${tableValue(weather.temperature[index], " °C")}</td>
        <td>${tableValue(weather.humidity[index], " %")}</td>
        <td>${tableValue(weather.cloudCover[index], " %")}</td>
        <td>${tableValue(weather.precipitation[index], " mm")}</td>
        <td>${tableValue(weather.ghi[index], " W/m²")}</td>
        <td>${tableValue(weather.dni[index], " W/m²")}</td>
        <td>${tableValue(weather.dhi[index], " W/m²")}</td>
        <td>${tableValue(weather.windSpeed[index], " m/s")}</td>
        <td>${tableValue(weather.windDirection[index], "°")}</td>
      </tr>`).join("");
  }

  function exportForecast(forecast) {
    const weather = forecast.weather;
    const columns = ["timestamp", "demand_kW", "fixed_load_kW", "flexible_load_baseline_kW", "solar_kW", "wind_kW", "renewable_kW", "renewable_surplus_kW", "temperature_c", "humidity_pct", "cloud_cover_pct", "precipitation_mm", "ghi_w_m2", "dni_w_m2", "dhi_w_m2", "wind_speed_mps", "wind_direction_deg"];
    const rows = forecast.timestamps.map((timestamp, index) => [
      timestamp, forecast.demand[index], forecast.fixedLoad[index], forecast.flexibleLoadBaseline[index], forecast.solar[index], forecast.wind[index], forecast.renewable[index], forecast.renewableSurplus[index], weather.temperature[index], weather.humidity[index], weather.cloudCover[index], weather.precipitation[index], weather.ghi[index], weather.dni[index], weather.dhi[index], weather.windSpeed[index], weather.windDirection[index],
    ]);
    const csv = [columns, ...rows].map((row) => row.map((value) => value ?? "").join(",")).join("\n");
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    link.download = "microgrid_forecast_24h.csv";
    link.click();
    URL.revokeObjectURL(link.href);
  }

  function updateBrowserClock(timezone) {
    const now = new Date();
    setText("browserClock", `Current time · ${new Intl.DateTimeFormat("en-IN", { timeZone: timezone, dateStyle: "medium", timeStyle: "short" }).format(now)}`);
  }

  async function loadForecast() {
    try {
      const forecast = await api.getForecast();
      if (forecastRetryTimer) {
        window.clearInterval(forecastRetryTimer);
        forecastRetryTimer = null;
      }
      const history = forecast.history;
      const weather = forecast.weather;
      setStats("demand", forecast.demand);
      setStats("solar", forecast.solar);
      setStats("wind", forecast.wind);

      setText("forecastUpdated", formatDateTime(forecast.displayUpdated || forecast.start, forecast.timezone));
      setText("historyWindow", formatRange(history.start, history.end, forecast.timezone));
      setText("forecastWindow", formatRange(forecast.start, forecast.end, forecast.timezone));
      setText("forecastTimezone", `Pipeline timezone · ${forecast.timezone} · ${forecast.calendar || "display calendar"}`);
      setText("historyCoverage", `${history.availableHours} hourly records`);
      setText("historySource", history.source);
      setText("forecastSource", forecast.source);
      setText("weatherSource", weather.available ? weather.source : "Weather artifact unavailable");
      setText("contextBoundaryLabel", `Forecast begins ${formatDateTime(forecast.start, forecast.timezone)}`);
      setText("horizonLabel", formatRange(forecast.start, forecast.end, forecast.timezone));
      setText("weatherChartStatus", weather.available ? weather.source : "Unavailable");
      updateBrowserClock(forecast.timezone);
      window.setInterval(() => updateBrowserClock(forecast.timezone), 30000);

      const demandStats = stats(forecast.demand);
      const fixedStats = stats(forecast.fixedLoad);
      const flexibleStats = stats(forecast.flexibleLoadBaseline);
      const shiftStats = stats(forecast.maxFlexibleShift);
      const solarStats = stats(forecast.solar);
      const windStats = stats(forecast.wind);
      const rainStats = stats(weather.precipitation);
      setText("demandNote", `Demand ranges from ${formatValue(Math.min(...values(forecast.demand)), " kW")} to ${formatValue(demandStats.peak, " kW")} across ${forecast.horizon} hourly intervals.`);
      setText("renewableNote", `Solar and wind availability combine for a peak of ${formatValue(stats(forecast.renewable).peak, " kW")} in the model horizon.`);
      setText("fixedLoadSummary", formatValue(fixedStats.average, " kW avg"));
      setText("flexibleLoadSummary", formatValue(flexibleStats.average, " kW avg"));
      setText("shiftSummary", formatValue(shiftStats.peak, " kW max"));
      setText("solarEnergySummary", formatValue(solarStats.total, " kWh"));
      setText("windEnergySummary", formatValue(windStats.total, " kWh"));
      setText("rainSummary", weather.available ? formatValue(rainStats.total, " mm") : "—");

      populateTable(forecast);
      if (typeof Chart === "function") {
        drawContextChart(forecast);
      } else {
        setText("contextBoundaryLabel", "Charts unavailable · hourly data is below");
      }
      document.querySelectorAll("[data-forecast-view]").forEach((button) => {
        button.addEventListener("click", () => showView(button.dataset.forecastView, forecast));
      });
      document.getElementById("downloadForecast")?.addEventListener("click", () => exportForecast(forecast));
    } catch (error) {
      showDataError(error);
      if (!forecastRetryTimer) {
        forecastRetryTimer = window.setInterval(loadForecast, 5000);
      }
    }
  }

  loadForecast();
})();
