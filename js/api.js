/*
  API service boundary. Replace these functions with fetch() calls when FastAPI is ready.
  UI code should call api.js, never read mockData.js directly.
*/
const api = {
  async getCurrentMicrogridState(){ return structuredClone(MicrogridMockData.current); },
  async getForecast(){ return structuredClone(MicrogridMockData.forecast); },
  async getDispatchPlan(){ return structuredClone(MicrogridMockData.dispatch); },
  async getBatteryStatus(){
    const c = MicrogridMockData.current;
    return {
      soc:c.batterySoc, capacity:200, availableEnergy:136, power:c.batteryPower,
      direction:c.batteryDirection, reserve:c.batteryReserve, maxCharge:50, maxDischarge:50,
      socTrajectory:MicrogridMockData.dispatch.soc
    };
  },
  async getAlerts(){ return structuredClone(MicrogridMockData.alerts); },
  async getSystemSettings(){ return structuredClone(MicrogridMockData.settings); },
  async getSystemStatus(){ return structuredClone(MicrogridMockData.system); }
};
