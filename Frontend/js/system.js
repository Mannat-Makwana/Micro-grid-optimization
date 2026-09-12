(async()=>{
 const s=await api.getSystemSettings();
 const range=document.getElementById("preference"), out=document.getElementById("preferenceValue");
 range.value=s.optimizationPreference; const update=()=>{const v=+range.value; out.textContent=v<50?`Cost-focused (${v}% emissions)`:v>50?`Emissions-focused (${100-v}% cost)`: "Balanced";}; update(); range.addEventListener("input",update);
 document.getElementById("reserveInput").value=s.minBatteryReserve;
 document.getElementById("dieselInput").value=s.dieselMaxOutput;
 document.getElementById("horizonInput").value=s.planningHorizon;
 document.getElementById("intervalInput").value=s.forecastUpdateInterval;
 document.getElementById("dieselAvailability").value=s.dieselAvailability;
 ["reserveInput","dieselInput","horizonInput","intervalInput","dieselAvailability"].forEach(id=>{
   document.getElementById(id).addEventListener("change",e=>{ document.getElementById(id+"State")?.replaceChildren(document.createTextNode(e.target.value)); });
 });
})()
