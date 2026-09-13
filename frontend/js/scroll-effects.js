(() => {
  const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  const root = document.documentElement;
  const body = document.body;

  const progress = document.createElement("div");
  progress.className = "scroll-progress";
  progress.setAttribute("aria-hidden", "true");
  progress.innerHTML = "<span></span>";
  document.body.appendChild(progress);
  const progressBar = progress.querySelector("span");

  const cue = document.createElement("div");
  cue.className = "scroll-cue";
  cue.setAttribute("aria-hidden", "true");
  cue.innerHTML = '<span>Scroll to explore</span><i></i>';
  document.body.appendChild(cue);

  const targets = [
    document.querySelector(".page-head"),
    ...document.querySelectorAll(".page > .grid, .page > .card, .page > .forecast-toolbar, .page > .footer-note"),
  ].filter(Boolean);

  targets.forEach((target, index) => {
    target.classList.add("scroll-reveal");
    target.style.setProperty("--reveal-delay", `${Math.min(index * 55, 330)}ms`);
  });

  if (reducedMotion || !("IntersectionObserver" in window)) {
    targets.forEach((target) => target.classList.add("is-visible"));
  } else {
    const observer = new IntersectionObserver((entries, instance) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        instance.unobserve(entry.target);
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
    targets.forEach((target) => observer.observe(target));
  }

  let framePending = false;
  let previousScroll = window.scrollY;
  const scheduleFrame = window.requestAnimationFrame || ((callback) => window.setTimeout(callback, 16));

  function updateScrollState() {
    framePending = false;
    const scrollTop = window.scrollY || window.pageYOffset || 0;
    const maxScroll = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
    const progressValue = Math.min(1, Math.max(0, scrollTop / maxScroll));
    progressBar.style.transform = `scaleX(${progressValue})`;
    body.classList.toggle("has-scrolled", scrollTop > 12);
    body.dataset.scrollDirection = scrollTop > previousScroll ? "down" : "up";
    previousScroll = scrollTop;

    if (!reducedMotion) {
      const offset = Math.min(scrollTop, 420) * 0.035;
      root.style.setProperty("--page-parallax", `${offset.toFixed(2)}px`);
    }
  }

  function requestScrollUpdate() {
    if (framePending) return;
    framePending = true;
    scheduleFrame(updateScrollState);
  }

  window.addEventListener("scroll", requestScrollUpdate, { passive: true });
  window.addEventListener("resize", requestScrollUpdate, { passive: true });
  requestScrollUpdate();
})();
