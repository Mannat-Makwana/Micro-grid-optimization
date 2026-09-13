/* Live API boundary for every dashboard page. */
const API_BASE = window.MICROGRID_API_BASE || "http://127.0.0.1:8000";
let dashboardStatePromise;

async function requestJson(path) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { Accept: "application/json" },
  });

  let payload = null;
  try {
    payload = await response.json();
  } catch (_) {
    payload = null;
  }

  if (!response.ok) {
    const detail = payload?.detail || `API request failed (${response.status})`;
    throw new Error(detail);
  }
  return payload;
}

function getDashboardState() {
  if (!dashboardStatePromise) {
    dashboardStatePromise = requestJson("/dashboard/state");
  }
  return dashboardStatePromise;
}

const api = {
  baseUrl: API_BASE,
  async getCurrentMicrogridState() {
    return (await getDashboardState()).current;
  },
  async getForecast() {
    return (await getDashboardState()).forecast;
  },
  async getDispatchPlan() {
    return (await getDashboardState()).dispatch;
  },
  async getBatteryStatus() {
    return (await getDashboardState()).battery;
  },
  async getAlerts() {
    return (await getDashboardState()).alerts;
  },
  async getSystemSettings() {
    return (await getDashboardState()).settings;
  },
  async getSystemStatus() {
    return (await getDashboardState()).system;
  },
};
