document.addEventListener("DOMContentLoaded", () => {
  const page = document.body.dataset.page;
  const nav = document.querySelectorAll(".nav a");
  nav.forEach(a => {
    if (a.dataset.page === page) a.classList.add("active");
  });
  const menu = document.querySelector(".mobile-menu");
  const sidebar = document.querySelector(".sidebar");
  if(menu) menu.addEventListener("click", () => sidebar.classList.toggle("open"));
  const status = document.querySelector("[data-system-status]");
  if(status){
    status.textContent = MicrogridMockData.system.status;
  }
  const time = document.querySelector("[data-current-time]");
  if(time){
    const d = new Date(MicrogridMockData.system.timestamp);
    time.textContent = d.toLocaleString("en-IN",{dateStyle:"medium",timeStyle:"short"});
  }
});
function formatNumber(n){ return new Intl.NumberFormat("en-IN").format(n); }
function escapeHtml(s){ return String(s).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m])); }
