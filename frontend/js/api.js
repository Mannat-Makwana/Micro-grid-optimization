/* Live API boundary for every dashboard page. */
const API_BASE = window.MICROGRID_API_BASE || (
  window.location.protocol.startsWith("http") && window.location.port === "8000"
    ? window.location.origin
    : "http://127.0.0.1:8000"
);
let dashboardStatePromise;
let forecastStatePromise;

async function requestJson(path) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: { Accept: "application/json" },
    });
  } catch (error) {
    throw new Error(`Cannot reach the backend at ${API_BASE}. Start FastAPI with: uvicorn api.main:app --reload`);
  }

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
  return dashboardStatePromise.catch((error) => {
    dashboardStatePromise = null;
    throw error;
  });
}

const api = {
  baseUrl: API_BASE,
  async getCurrentMicrogridState() {
    return (await getDashboardState()).current;
  },
  async getForecast() {
    if (!forecastStatePromise) {
      forecastStatePromise = requestJson("/forecast/next-24h");
    }
    return forecastStatePromise.catch((error) => {
      forecastStatePromise = null;
      throw error;
    });
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
