document.addEventListener("DOMContentLoaded", () => {
  const page = document.body.dataset.page;
  const nav = document.querySelectorAll(".nav a");
  nav.forEach(a => {
    if (a.dataset.page === page) a.classList.add("active");
  });
  const menu = document.querySelector(".mobile-menu");
  const sidebar = document.querySelector(".sidebar");
  if(menu) menu.addEventListener("click", () => sidebar.classList.toggle("open"));
  loadSystemChrome();
});
function formatNumber(n){ return new Intl.NumberFormat("en-IN").format(n); }
function escapeHtml(s){ return String(s).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m])); }

async function loadSystemChrome(){
  try {
    const system = await api.getSystemStatus();
    document.querySelectorAll("[data-system-status]").forEach((element) => {
      element.textContent = system.status;
    });
    const timestamp = document.querySelector("[data-current-time]");
    if(timestamp){
      timestamp.textContent = new Date(system.timestamp).toLocaleString("en-IN", {dateStyle:"medium", timeStyle:"short"});
    }
    const systemName = document.querySelector("[data-system-name]");
    if(systemName) systemName.textContent = system.name;
    const source = document.querySelector("[data-data-source]");
    if(source) source.textContent = system.source;
    const pill = document.querySelector("[data-system-pill]");
    if(pill) pill.textContent = system.status;
  } catch(error) {
    document.querySelectorAll("[data-system-status]").forEach((element) => {
      element.textContent = "Data unavailable";
    });
    showDataError(error);
  }
}

function showDataError(error){
  const existing = document.querySelector(".data-error");
  if(existing) return;
  const banner = document.createElement("div");
  banner.className = "data-error";
  banner.innerHTML = `<strong>Live data unavailable</strong><span>${escapeHtml(error.message || "Start the API and generate a controller result.")}</span>`;
  document.querySelector(".page")?.prepend(banner);
}
