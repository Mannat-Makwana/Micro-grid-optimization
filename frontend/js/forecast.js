(async()=>{
 const f=await api.getForecast(), p=await api.getDispatchPlan();
 const stats=a=>({current:a[10],peak:Math.max(...a),avg:Math.round(a.reduce((x,y)=>x+y,0)/a.length)});
 [["demand",f.demand],["solar",f.solar],["wind",f.wind]].forEach(([k,a])=>{
   const s=stats(a); document.getElementById(k+"Current").textContent=s.current+" kW";
   document.getElementById(k+"Peak").textContent=s.peak+" kW"; document.getElementById(k+"Avg").textContent=s.avg+" kW";
 });
 new Chart(document.getElementById("forecastChart"),{type:"line",data:{labels:f.times,datasets:[
  {label:"Demand forecast",data:f.demand,borderColor:"#182126",backgroundColor:"rgba(24,33,38,.04)",fill:true,tension:.35,borderWidth:2.5},
  {label:"Solar forecast",data:f.solar,borderColor:"#e9a72b",backgroundColor:"rgba(233,167,43,.12)",fill:true,tension:.35},
  {label:"Wind forecast",data:f.wind,borderColor:"#3578b8",backgroundColor:"rgba(53,120,184,.09)",fill:true,tension:.35}
 ]},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:"index",intersect:false},plugins:{legend:{position:"bottom",labels:{boxWidth:10,usePointStyle:true,font:{size:10}}}},scales:{x:{grid:{display:false},ticks:{maxTicksLimit:12,font:{size:10}}},y:{beginAtZero:true,title:{display:true,text:"Power (kW)"}}}}});
})()
