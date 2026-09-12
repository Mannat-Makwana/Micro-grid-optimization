(async()=>{
 const c=await api.getCurrentMicrogridState(), alerts=await api.getAlerts(), f=await api.getForecast(), p=await api.getDispatchPlan();
 const set=(id,v)=>{const e=document.getElementById(id);if(e)e.textContent=v};
 set("demand",`${c.demand} kW`); set("solar",`${c.solar} kW`); set("solarAvail",`Available: ${c.solarAvailable} kW`);
 set("wind",`${c.wind} kW`); set("windAvail",`Available: ${c.windAvailable} kW`);
 set("soc",`${c.batterySoc}%`); set("batteryPower",`${c.batteryPower} kW ↓`); set("reserve",`Reserve: ${c.batteryReserve}%`);
 set("diesel",`${c.diesel} kW`); set("cost",`₹${formatNumber(c.operatingCost)}/hr`); set("co2",`${c.co2} kg/hr`);
 const solarPct=Math.round(c.solar/c.solarAvailable*100), windPct=Math.round(c.wind/c.windAvailable*100);
 document.getElementById("solarBar").style.width=solarPct+"%"; document.getElementById("windBar").style.width=windPct+"%";
 document.getElementById("batteryBar").style.width=c.batterySoc+"%";
 document.getElementById("alerts").innerHTML=alerts.map(a=>`<div class="alert ${a.severity}"><span class="alert-dot"></span><div><strong>${escapeHtml(a.title)}</strong><p>${escapeHtml(a.detail)}</p></div><time>${a.time}</time></div>`).join("");
 const why = c.batteryPower>0
  ? "Solar and wind generation are being used first because renewable power is available. Battery discharge is supporting current demand while maintaining the configured reserve. Diesel is covering the remaining load."
  : "Renewable generation is being prioritized. Excess renewable energy is being directed to the battery while diesel remains available for residual demand.";
 document.getElementById("why").textContent=why;
 new Chart(document.getElementById("dispatchChart"),{
   type:"line",data:{labels:p.times,datasets:[
    {label:"Demand",data:p.demand,borderColor:"#182126",backgroundColor:"rgba(24,33,38,.04)",borderWidth:2.5,tension:.35,fill:true},
    {label:"Solar",data:p.solar,borderColor:"#e9a72b",backgroundColor:"rgba(233,167,43,.14)",fill:true,tension:.35},
    {label:"Wind",data:p.wind,borderColor:"#3578b8",backgroundColor:"rgba(53,120,184,.10)",fill:true,tension:.35},
    {label:"Battery",data:p.battery.map(v=>Math.max(v,0)),borderColor:"#7561a8",backgroundColor:"rgba(117,97,168,.09)",fill:true,tension:.35},
    {label:"Diesel",data:p.diesel,borderColor:"#69727a",backgroundColor:"rgba(105,114,122,.07)",fill:true,tension:.35}
   ]},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:"index",intersect:false},plugins:{legend:{position:"bottom",labels:{boxWidth:10,usePointStyle:true,font:{size:10}}},tooltip:{callbacks:{label:ctx=>` ${ctx.dataset.label}: ${ctx.raw} kW`}}},scales:{x:{grid:{display:false},ticks:{maxTicksLimit:12,font:{size:10}}},y:{title:{display:true,text:"Power (kW)"},beginAtZero:true,grid:{color:"#edf0f2"}}}}
 });
})()
