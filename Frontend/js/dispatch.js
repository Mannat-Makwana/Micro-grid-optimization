(async()=>{
 const p=await api.getDispatchPlan();
 const tbody=document.getElementById("dispatchRows");
 tbody.innerHTML=p.times.map((t,i)=>`<tr><td>${t}</td><td>${p.demand[i]}</td><td>${p.solar[i]}</td><td>${p.wind[i]}</td><td>${p.battery[i] > 0 ? p.battery[i]+" ↓" : Math.abs(p.battery[i])+" ↑ charge"}</td><td>${p.diesel[i]}</td></tr>`).join("");
 const total=(a,fn=x=>x)=>Math.round(a.reduce((s,v)=>s+fn(v),0));
 document.getElementById("renewableTotal").textContent=total(p.solar)+total(p.wind)+" kWh";
 document.getElementById("batteryThroughput").textContent=total(p.battery,Math.abs)+" kWh";
 document.getElementById("dieselEnergy").textContent=total(p.diesel)+" kWh";
 document.getElementById("dispatchCost").textContent="₹"+formatNumber(28740);
 document.getElementById("dispatchCo2").textContent="426 kg";
})()
