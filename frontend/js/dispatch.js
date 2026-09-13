(async()=>{
 try {
  const p=await api.getDispatchPlan();
  const tbody=document.getElementById("dispatchRows");
  tbody.innerHTML=p.times.map((t,i)=>{
   const battery=p.battery[i];
   const batteryText=battery>0?battery.toFixed(1)+" ↓ discharge":battery<0?Math.abs(battery).toFixed(1)+" ↑ charge":"0.0 idle";
   return "<tr><td>"+t+"</td><td>"+p.demand[i].toFixed(1)+"</td><td>"+p.solar[i].toFixed(1)+"</td><td>"+p.wind[i].toFixed(1)+"</td><td>"+batteryText+"</td><td>"+p.diesel[i].toFixed(1)+"</td></tr>";
  }).join("");
  const total=(a,fn=x=>x)=>a.reduce((s,v)=>s+fn(v),0);
  document.getElementById("renewableTotal").textContent=(total(p.solar)+total(p.wind)).toFixed(1)+" kWh";
  document.getElementById("batteryThroughput").textContent=(total(p.batteryCharge)+total(p.batteryDischarge)).toFixed(1)+" kWh";
  document.getElementById("dieselEnergy").textContent=total(p.diesel).toFixed(1)+" kWh";
  document.getElementById("dispatchCost").textContent="₹"+formatNumber(Math.round(total(p.cost)));
  document.getElementById("dispatchCo2").textContent=total(p.co2).toFixed(1)+" kg";
  document.getElementById("dispatchUpdated").textContent=new Date(p.updated).toLocaleString("en-IN",{dateStyle:"medium",timeStyle:"short"});
  document.getElementById("dispatchSource").textContent=p.source;
  document.getElementById("dispatchHorizon").textContent=p.times.length+" hours";
 } catch(error) { showDataError(error); }
})()
