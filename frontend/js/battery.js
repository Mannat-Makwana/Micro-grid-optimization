(async()=>{
 const b=await api.getBatteryStatus(), p=await api.getDispatchPlan();
 const set=(id,v)=>document.getElementById(id).textContent=v;
 set("batterySoc",b.soc+"%");set("capacity",b.capacity+" kWh");set("available",b.availableEnergy+" kWh");
 set("power",b.power+" kW "+b.direction.toLowerCase());set("reserve",b.reserve+"%");set("charge",b.maxCharge+" kW");set("discharge",b.maxDischarge+" kW");
 const state=document.getElementById("batteryState"); state.textContent=b.direction;
 const chart=new Chart(document.getElementById("socChart"),{type:"line",data:{labels:p.times,datasets:[
  {label:"Planned SOC",data:p.soc,borderColor:"#7561a8",backgroundColor:"rgba(117,97,168,.12)",fill:true,tension:.35,borderWidth:2},
  {label:"Minimum reserve",data:p.times.map(()=>b.reserve),borderColor:"#b64d4d",borderDash:[6,5],pointRadius:0,borderWidth:1.5}
 ]},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:"index",intersect:false},plugins:{legend:{position:"bottom",labels:{boxWidth:10,usePointStyle:true,font:{size:10}}}},scales:{x:{grid:{display:false},ticks:{maxTicksLimit:12,font:{size:10}}},y:{min:0,max:100,title:{display:true,text:"SOC (%)"}}}}});
})()
