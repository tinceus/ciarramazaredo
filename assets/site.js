/* Shared page behaviour: config slots, booking button, mobile menu, intro video, count-up. */
(function () {
  const SITE = window.SITE || {};
  const get = path => path.split('.').reduce((o, k) => (o == null ? o : o[k]), SITE);
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* Config slots: show [data-needs] only when its value is set; fill [data-text] */
  document.querySelectorAll('[data-needs]').forEach(el => {
    const v = get(el.dataset.needs);
    if (v == null || v === '' || (Array.isArray(v) && !v.length)) return;
    el.querySelectorAll('[data-text]').forEach(t => { t.textContent = get(t.dataset.text); });
    el.hidden = false;
  });

  /* Booking: email until a booking link is configured */
  if (SITE.bookingUrl) {
    document.querySelectorAll('[data-book]').forEach(a => {
      a.href = SITE.bookingUrl;
      a.target = '_blank';
      a.rel = 'noopener';
      const label = [...a.childNodes].reverse().find(n => n.nodeType === 3 && n.textContent.trim());
      if (label) label.textContent = ' Book a call';
      else a.textContent = 'Book a call';
    });
  }

  /* Mobile menu */
  const toggle = document.querySelector('.nav-toggle');
  const menu = toggle && document.getElementById(toggle.getAttribute('aria-controls'));
  if (toggle && menu) {
    const set = open => { menu.classList.toggle('open', open); toggle.setAttribute('aria-expanded', String(open)); toggle.textContent = open ? 'Close' : 'Menu'; };
    toggle.addEventListener('click', () => set(!menu.classList.contains('open')));
    menu.addEventListener('click', e => { if (e.target.closest('a')) set(false); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape' && menu.classList.contains('open')) { set(false); toggle.focus(); } });
    document.addEventListener('click', e => { if (menu.classList.contains('open') && !e.target.closest('header')) set(false); });
  }

  /* Intro video: load YouTube only after a click */
  document.querySelectorAll('.video-play').forEach(btn => btn.addEventListener('click', () => {
    const frame = document.createElement('div');
    frame.className = 'video-frame';
    const iframe = document.createElement('iframe');
    iframe.src = 'https://www.youtube-nocookie.com/embed/' + encodeURIComponent(SITE.introVideoId) + '?autoplay=1&rel=0';
    iframe.title = 'Introduction video';
    iframe.allow = 'autoplay; encrypted-media; picture-in-picture';
    iframe.allowFullscreen = true;
    frame.appendChild(iframe);
    btn.replaceWith(frame);
  }));

  /* Count-up once when seen; final value is already in the page */
  const counters = document.querySelectorAll('[data-count]');
  if (!reduce && 'IntersectionObserver' in window) {
    const io = new IntersectionObserver(entries => entries.forEach(e => {
      if (!e.isIntersecting) return;
      io.unobserve(e.target);
      const el = e.target, to = +el.dataset.count, from = +(el.dataset.from || 0), dec = +(el.dataset.decimals || 0);
      const t0 = performance.now(), dur = 900;
      const step = now => {
        const p = Math.min(1, (now - t0) / dur), eased = 1 - Math.pow(1 - p, 3);
        el.textContent = (from + (to - from) * eased).toFixed(dec);
        if (p < 1) requestAnimationFrame(step); else el.textContent = to.toFixed(dec);
      };
      requestAnimationFrame(step);
    }), { threshold: 0.6 });
    counters.forEach(el => { el.textContent = (+(el.dataset.from || 0)).toFixed(+(el.dataset.decimals || 0)); io.observe(el); });
  }
})();
