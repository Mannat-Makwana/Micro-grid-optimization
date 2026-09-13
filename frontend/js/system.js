(() => {
  const fieldIds = [
    "preference",
    "reserveInput",
    "dieselInput",
    "horizonInput",
    "dieselAvailability",
    "intervalInput",
  ];
  let settings;

  const get = (id) => document.getElementById(id);
  const setText = (id, value) => {
    const element = get(id);
    if (element) element.textContent = value;
  };

  function render(values) {
    settings = values;
    get("preference").value = values.optimizationPreference;
    get("reserveInput").value = values.minBatteryReserve;
    get("dieselInput").value = values.dieselMaxOutput;
    get("horizonInput").value = values.planningHorizon;
    get("dieselAvailability").value = values.dieselAvailability;
    get("intervalInput").value = values.forecastUpdateInterval;
    updatePreview();

    setText("systemLocation", values.location.name);
    setText("households", values.households);
    setText("configSource", values.source);
    setText("systemSource", values.source);
  }

  function collect() {
    return {
      optimization_preference: Number(get("preference").value),
      min_battery_reserve: Number(get("reserveInput").value),
      diesel_max_output: Number(get("dieselInput").value),
      planning_horizon: Number(get("horizonInput").value),
      diesel_availability: get("dieselAvailability").value,
      forecast_update_interval: Number(get("intervalInput").value),
    };
  }

  function updatePreview() {
    const values = collect();
    setText("preferenceValue", `${values.optimization_preference}% emissions weight`);
    setText("preferenceValueRow", `${values.optimization_preference}% emissions weight`);
    setText("reserveValueRow", `${values.min_battery_reserve}%`);
    setText("dieselValueRow", `${values.diesel_max_output} kW`);
    setText("horizonValueRow", `${values.planning_horizon} hours`);
    setText("intervalValueRow", `${values.forecast_update_interval} minutes`);
    setText("settingsStatus", "Unsaved changes");
    get("settingsStatus")?.classList.add("pending");
  }

  function validate(values) {
    if (values.min_battery_reserve > 60) {
      throw new Error("Minimum battery reserve cannot exceed the configured initial SOC of 60%.");
    }
    if (values.planning_horizon < 6 || values.planning_horizon > 24) {
      throw new Error("Planning horizon must be between 6 and 24 hours for the available forecast pipeline.");
    }
    if (values.forecast_update_interval < 1) {
      throw new Error("Forecast update interval must be at least 1 minute.");
    }
  }

  async function loadSettings() {
    try {
      const values = await api.getSystemSettings();
      render(values);
      setText("settingsStatus", "Saved configuration");
      get("settingsStatus")?.classList.remove("pending", "error");
    } catch (error) {
      showDataError(error);
    }
  }

  async function saveSettings() {
    const button = get("saveSettings");
    const status = get("settingsStatus");
    try {
      const values = collect();
      validate(values);
      button.disabled = true;
      status.textContent = "Saving…";
      status.classList.remove("error");
      const saved = await api.updateSystemSettings(values);
      render(saved);
      status.textContent = "Saved · rerun the controller to apply dispatch changes";
      status.classList.remove("pending");
    } catch (error) {
      status.textContent = error.message || "Could not save configuration";
      status.classList.add("error");
    } finally {
      button.disabled = false;
    }
  }

  function attachEvents() {
    fieldIds.forEach((id) => get(id)?.addEventListener("input", updatePreview));
    fieldIds.forEach((id) => get(id)?.addEventListener("change", updatePreview));
    get("saveSettings")?.addEventListener("click", saveSettings);
    get("reloadSettings")?.addEventListener("click", loadSettings);
  }

  attachEvents();
  loadSettings();
})();
