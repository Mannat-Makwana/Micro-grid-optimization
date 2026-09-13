(async()=>{
 try {
  const f=await api.getForecast();
  const stats=a=>({current:a[0],peak:Math.max(...a),avg:a.reduce((x,y)=>x+y,0)/a.length});
  [["demand",f.demand],["solar",f.solar],["wind",f.wind]].forEach(([k,a])=>{
   const s=stats(a); document.getElementById(k+"Current").textContent=s.current.toFixed(1)+" kW";
   document.getElementById(k+"Peak").textContent=s.peak.toFixed(1)+" kW"; document.getElementById(k+"Avg").textContent=s.avg.toFixed(1)+" kW";
  });
  document.getElementById("forecastUpdated").textContent=new Date(f.updated).toLocaleString("en-IN",{dateStyle:"medium",timeStyle:"short"});
  document.getElementById("demandNote").textContent="Forecast range: "+Math.min(...f.demand).toFixed(1)+"–"+Math.max(...f.demand).toFixed(1)+" kW across "+f.demand.length+" controller intervals.";
  document.getElementById("renewableNote").textContent="Solar and wind availability together peak at "+Math.max(...f.renewable).toFixed(1)+" kW in the supplied forecast.";
  new Chart(document.getElementById("forecastChart"),{type:"line",data:{labels:f.times,datasets:[
   {label:"Demand forecast",data:f.demand,borderColor:"#182126",backgroundColor:"rgba(24,33,38,.04)",fill:true,tension:.35,borderWidth:2.5},
   {label:"Solar availability",data:f.solar,borderColor:"#e9a72b",backgroundColor:"rgba(233,167,43,.12)",fill:true,tension:.35},
   {label:"Wind availability",data:f.wind,borderColor:"#3578b8",backgroundColor:"rgba(53,120,184,.09)",fill:true,tension:.35}
  ]},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:"index",intersect:false},plugins:{legend:{position:"bottom",labels:{boxWidth:10,usePointStyle:true,font:{size:10}}}},scales:{x:{grid:{display:false},ticks:{maxTicksLimit:12,font:{size:10}}},y:{beginAtZero:true,title:{display:true,text:"Power (kW)"}}}}});
 } catch(error) { showDataError(error); }
})()
