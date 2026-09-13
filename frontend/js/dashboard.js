(async()=>{
 try {
  const [c, alerts, p] = await Promise.all([
   api.getCurrentMicrogridState(), api.getAlerts(), api.getDispatchPlan()
  ]);
  const set=(id,v)=>{const e=document.getElementById(id);if(e)e.textContent=v;};
  const pct=(value,total)=>total>0?Math.min(100,Math.round(value/total*100)):0;
  set("demand",`${c.demand} kW`); set("solar",`${c.solar} kW`); set("solarAvail",`Available: ${c.solarAvailable} kW`);
  set("wind",`${c.wind} kW`); set("windAvail",`Available: ${c.windAvailable} kW`);
  set("soc",`${c.batterySoc}%`); set("batteryPower",`${c.batteryPower} kW ${c.batteryDirection.toLowerCase()}`); set("reserve",`Reserve: ${c.batteryReserve}%`);
  set("diesel",`${c.diesel} kW`); set("cost",`₹${formatNumber(c.operatingCost)}/hr`); set("co2",`${c.co2} kg/hr`);
  document.getElementById("solarBar").style.width=pct(c.solar,c.solarAvailable)+"%";
  document.getElementById("windBar").style.width=pct(c.wind,c.windAvailable)+"%";
  document.getElementById("batteryBar").style.width=c.batterySoc+"%";

  const mix=[c.solar,c.wind,Math.max(c.batterySignedPower,0),c.diesel];
  const total=mix.reduce((sum,value)=>sum+value,0);
  const degrees=mix.map(value=>value/Math.max(total,1)*100);
  document.querySelector(".donut").style.background=`conic-gradient(var(--solar) 0 ${degrees[0]}%,var(--wind) ${degrees[0]}% ${degrees[0]+degrees[1]}%,var(--battery) ${degrees[0]+degrees[1]}% ${degrees[0]+degrees[1]+degrees[2]}%,var(--diesel) ${degrees[0]+degrees[1]+degrees[2]}% 100%)`;
  set("mixDemand",`${c.demand} kW`);
  [["mixSolar",c.solar],["mixWind",c.wind],["mixBattery",Math.max(c.batterySignedPower,0)],["mixDiesel",c.diesel]].forEach(([id,value])=>set(id,`${value} kW · ${total?Math.round(value/total*100):0}%`));
  set("recommendSolar",`${c.solar} kW`); set("recommendWind",`${c.wind} kW`); set("recommendBattery",`${Math.abs(c.batterySignedPower)} kW ${c.batteryDirection === "Discharging" ? "↓" : c.batteryDirection === "Charging" ? "↑" : "—"}`); set("recommendDiesel",`${c.diesel} kW`);
  document.getElementById("alerts").innerHTML=alerts.map(a=>`<div class="alert ${a.severity}"><span class="alert-dot"></span><div><strong>${escapeHtml(a.title)}</strong><p>${escapeHtml(a.detail)}</p></div><time>${escapeHtml(a.time)}</time></div>`).join("");
  document.getElementById("why").textContent = c.batteryDirection === "Discharging"
   ? "Renewable generation is being used first. The battery is covering the remaining demand while the controller protects the configured reserve."
   : c.batteryDirection === "Charging"
    ? "Available renewable generation exceeds immediate demand, so the controller is storing the surplus for later hours."
    : "The controller is balancing renewable generation and diesel backup without battery movement in this interval.";

  new Chart(document.getElementById("dispatchChart"),{type:"line",data:{labels:p.times,datasets:[
   {label:"Demand",data:p.demand,borderColor:"#182126",backgroundColor:"rgba(24,33,38,.04)",borderWidth:2.5,tension:.35,fill:true},
   {label:"Solar",data:p.solar,borderColor:"#e9a72b",backgroundColor:"rgba(233,167,43,.14)",fill:true,tension:.35},
   {label:"Wind",data:p.wind,borderColor:"#3578b8",backgroundColor:"rgba(53,120,184,.10)",fill:true,tension:.35},
   {label:"Battery discharge",data:p.batteryDischarge,borderColor:"#7561a8",backgroundColor:"rgba(117,97,168,.09)",fill:true,tension:.35},
   {label:"Diesel",data:p.diesel,borderColor:"#69727a",backgroundColor:"rgba(105,114,122,.07)",fill:true,tension:.35}
  ]},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:"index",intersect:false},plugins:{legend:{position:"bottom",labels:{boxWidth:10,usePointStyle:true,font:{size:10}}},tooltip:{callbacks:{label:ctx=>` ${ctx.dataset.label}: ${ctx.raw} kW`}}},scales:{x:{grid:{display:false},ticks:{maxTicksLimit:12,font:{size:10}}},y:{title:{display:true,text:"Power (kW)"},beginAtZero:true,grid:{color:"#edf0f2"}}}}});
 } catch(error) { showDataError(error); }
})()
