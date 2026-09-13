(async()=>{
 try {
  const s=await api.getSystemSettings();
  const set=(id,v)=>{const e=document.getElementById(id);if(e)e.textContent=v;};
  const range=document.getElementById("preference"), out=document.getElementById("preferenceValue");
  range.value=s.optimizationPreference; range.disabled=true; out.textContent=s.optimizationPreference+"% emissions weight";
  document.getElementById("reserveInput").value=s.minBatteryReserve;
  document.getElementById("dieselInput").value=s.dieselMaxOutput;
  document.getElementById("horizonInput").value=s.planningHorizon;
  document.getElementById("intervalInput").value=s.forecastUpdateInterval ?? "—";
  document.getElementById("dieselAvailability").value=s.dieselAvailability;
  ["reserveInput","dieselInput","horizonInput","intervalInput","dieselAvailability"].forEach(id=>document.getElementById(id).disabled=true);
  set("preferenceValueRow",s.optimizationPreference+"% emissions weight");
  set("reserveValueRow",s.minBatteryReserve+"%"); set("dieselValueRow",s.dieselMaxOutput+" kW"); set("horizonValueRow",s.planningHorizon+" hours"); set("intervalValueRow",s.forecastUpdateInterval==null?"Not configured":s.forecastUpdateInterval+" minutes");
  set("systemLocation",s.location.name); set("households",s.households); set("configSource",s.source); set("systemSource",s.source);
 } catch(error) { showDataError(error); }
})()
