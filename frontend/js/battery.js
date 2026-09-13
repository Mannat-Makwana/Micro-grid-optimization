(async()=>{
 try {
  const b=await api.getBatteryStatus();
  const set=(id,v)=>document.getElementById(id).textContent=v;
  set("batterySoc",b.soc+"%");set("capacity",b.capacity+" kWh");set("available",b.availableEnergy+" kWh");
  set("power",b.power+" kW "+b.direction.toLowerCase());set("reserve",b.reserve+"%");set("charge",b.maxCharge+" kW");set("discharge",b.maxDischarge+" kW");
  document.getElementById("batteryState").textContent=b.direction;
  document.querySelector(".soc-ring").style.background="conic-gradient(var(--battery) 0 "+b.soc+"%,#edf0f2 "+b.soc+"% 100%)";
  new Chart(document.getElementById("socChart"),{type:"line",data:{labels:b.socTrajectory.map((_,i)=>i+1),datasets:[
   {label:"Planned SOC",data:b.socTrajectory,borderColor:"#7561a8",backgroundColor:"rgba(117,97,168,.12)",fill:true,tension:.35,borderWidth:2},
   {label:"Minimum reserve",data:b.socTrajectory.map(()=>b.reserve),borderColor:"#b64d4d",borderDash:[6,5],pointRadius:0,borderWidth:1.5}
  ]},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:"index",intersect:false},plugins:{legend:{position:"bottom",labels:{boxWidth:10,usePointStyle:true,font:{size:10}}}},scales:{x:{grid:{display:false},ticks:{maxTicksLimit:12,font:{size:10},callback:(value)=>"H"+value}},y:{min:0,max:100,title:{display:true,text:"SOC (%)"}}}}});
 } catch(error) { showDataError(error); }
})()
