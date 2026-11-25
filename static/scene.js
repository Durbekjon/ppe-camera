// Isometric site map: one building per camera, coloured by its state. Pure CSS 3D, no library.
(() => {
  const scene = document.getElementById('scene'), world = document.getElementById('world');
  const VIEW = { rx: 58, rz: -42, zoom: 1 };
  let view = { ...VIEW };
  const STATE_TEXT = { safe: 'Xavfsiz', danger: 'Xavf', zone: 'Xavfli zona', offline: 'Uzilgan' };
  const B = { w: 190, d: 130, h: 72 };  // building size in ground pixels

  function apply() {
    world.style.setProperty('--rx', view.rx + 'deg');
    world.style.setProperty('--rz', view.rz + 'deg');
    world.style.setProperty('--zoom', view.zoom);
  }

  function box(cls, x, y, w, d, h) {
    const el = document.createElement('div');
    el.className = 'obj ' + cls;
    el.style.cssText = `--x:${x}px;--y:${y}px;--w:${w}px;--d:${d}px;--h:${h}px`;
    for (const f of ['back', 'left', 'front', 'side', 'top']) {
      const face = document.createElement('div'); face.className = 'face ' + f; el.append(face);
    }
    return el;
  }

  function billboard(lift) {
    const b = document.createElement('div'); b.className = 'billboard'; b.style.setProperty('--lift', lift + 'px');
    return b;
  }

  // Fixed scenery: a server block in the middle and a few props. Purely decorative.
  const SERVER = { x: -45, y: -45 };
  function scenery() {
    world.append(box('prop blue', SERVER.x, SERVER.y, 90, 90, 34));
    const tag = billboard(60); tag.style.left = SERVER.x + 45 + 'px'; tag.style.top = SERVER.y + 45 + 'px';
    const l = document.createElement('div'); l.className = 'label'; l.innerHTML = '<b>Server</b><span class="st">tahlil · 1 kompyuter</span>';
    tag.append(l); world.append(tag);
    [[-470, -430, 40, 40, 110], [-410, -430, 40, 40, 80], [380, -470, 70, 70, 26], [400, 380, 60, 120, 30]]
      .forEach(([x, y, w, d, h]) => world.append(box('prop', x, y, w, d, h)));
    [[-480, 300], [-430, 350], [440, -300], [470, 200], [-200, 460], [180, -470]]
      .forEach(([x, y]) => world.append(box('tree', x, y, 22, 22, 22)));
  }

  // Building positions around the server, up to 4 cameras.
  const SPOTS = [[-360, -60], [170, -60], [-95, -330], [-95, 220]];
  let built = '';
  const buildings = new Map();

  function build(cameras) {
    world.querySelectorAll('.building, .path, .camtag, .crew, .empty-map').forEach((e) => e.remove());
    buildings.clear();
    cameras.slice(0, SPOTS.length).forEach((cam, i) => {
      const [x, y] = SPOTS[i];
      // data path from the building to the server
      const cx = x + B.w / 2, cy = y + B.d / 2, sx = SERVER.x + 45, sy = SERVER.y + 45;
      const path = document.createElement('div'); path.className = 'path';
      path.style.left = cx + 'px'; path.style.top = cy + 'px';
      path.style.width = Math.hypot(sx - cx, sy - cy) + 'px';
      path.style.transform = `translateZ(1px) rotate(${Math.atan2(sy - cy, sx - cx)}rad)`;
      world.append(path);

      const b = box('building', x, y, B.w, B.d, B.h);
      b.tabIndex = 0;
      b.setAttribute('role', 'button');
      b.setAttribute('aria-label', cam.name);
      const halo = document.createElement('div'); halo.className = 'halo'; b.prepend(halo);
      const tag = billboard(B.h + 26);
      const label = document.createElement('div'); label.className = 'label';
      tag.append(label); b.append(tag);
      const crew = document.createElement('div'); crew.className = 'crew';
      b.append(crew);
      const choose = () => { if (typeof selectCamera === 'function') selectCamera(cam.name); };
      b.addEventListener('click', () => { if (!moved) choose(); });
      b.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); choose(); } });
      world.append(b);
      buildings.set(cam.name, { el: b, label, crew });
    });
  }

  function crewFor(entry, people, violators) {
    const key = people + ':' + violators;
    if (entry.crew.dataset.key === key) return;
    entry.crew.dataset.key = key;
    entry.crew.replaceChildren();
    const shown = Math.min(people, 8);
    for (let i = 0; i < shown; i++) {
      const spot = billboard(0);
      spot.style.left = 24 + (i % 4) * 44 + 'px';
      spot.style.top = B.d + 26 + Math.floor(i / 4) * 30 + 'px';
      const w = document.createElement('div'); w.className = 'worker' + (i < violators ? ' bad' : '');
      spot.append(w); entry.crew.append(spot);
    }
  }

  window.sceneUpdate = (s) => {
    const cams = s.cameras || [];
    const names = cams.map((c) => c.name).join('\u0000');
    if (names !== built) { built = names; build(cams); }
    for (const cam of cams) {
      const entry = buildings.get(cam.name);
      if (!entry) continue;
      entry.el.className = `obj building ${cam.status}${cam.name === s.name ? ' selected' : ''}`;
      entry.label.innerHTML = '';
      const b = document.createElement('b'); b.textContent = cam.name;
      const st = document.createElement('span'); st.className = 'st';
      st.textContent = `${STATE_TEXT[cam.status] || cam.status} · ${cam.people} kishi · ${cam.fps} FPS`;
      entry.label.append(b, st);
      crewFor(entry, cam.connected ? cam.people : 0, cam.connected ? cam.violators : 0);
    }
    // header figures
    const online = cams.filter((c) => c.connected).length;
    const people = cams.reduce((n, c) => n + (c.connected ? c.people : 0), 0);
    const violators = cams.reduce((n, c) => n + (c.connected ? c.violators : 0), 0);
    setText('kpi-people', people);
    setText('kpi-violators', `qoidabuzar: ${violators}`);
    setText('kpi-cameras', `${online}/${cams.length}`);
    setText('kpi-cameras-sub', online === cams.length ? 'hammasi onlayn' : `${cams.length - online} ta uzilgan`);
    setText('live-name', s.name || '');
    if (s.last_incident_id !== lastIncident) { lastIncident = s.last_incident_id; loadToday(); }
  };

  function setText(id, value) { const el = document.getElementById(id); if (el && el.textContent !== String(value)) el.textContent = value; }

  let lastIncident = null;
  async function loadToday() {
    try {
      const d = new Date(), day = new Date(d - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
      const r = await getJSON('/api/report?date=' + day);
      setText('kpi-total', r.total);
      setText('kpi-zone', `zonada: ${r.zone}`);
    } catch (e) { /* the dashboard already shows the server as unreachable */ }
  }
  setInterval(loadToday, 30000);  // also picks up false-alarm marks

  // ---------- interaction: drag to rotate, wheel to zoom ----------
  let dragging = false, moved = false, start = null;
  scene.addEventListener('pointerdown', (e) => {
    dragging = true; moved = false; start = { x: e.clientX, y: e.clientY, rx: view.rx, rz: view.rz };
  });
  window.addEventListener('pointermove', (e) => {
    if (!dragging) return;
    const dx = e.clientX - start.x, dy = e.clientY - start.y;
    if (!moved && Math.hypot(dx, dy) < 5) return;
    if (!moved) { moved = true; scene.classList.add('dragging'); }
    view.rz = start.rz + dx * 0.35;
    view.rx = Math.min(80, Math.max(20, start.rx - dy * 0.25));
    apply();
  });
  window.addEventListener('pointerup', () => {
    if (!dragging) return;
    dragging = false; scene.classList.remove('dragging');
    setTimeout(() => { moved = false; }, 0);  // let the click handler see whether this was a drag
  });
  const zoom = (f) => { view.zoom = Math.min(1.8, Math.max(0.5, view.zoom * f)); apply(); };
  scene.addEventListener('wheel', (e) => { e.preventDefault(); zoom(e.deltaY < 0 ? 1.08 : 1 / 1.08); }, { passive: false });
  scene.addEventListener('keydown', (e) => {
    const k = { ArrowLeft: () => (view.rz -= 8), ArrowRight: () => (view.rz += 8),
      ArrowUp: () => (view.rx = Math.min(80, view.rx + 4)), ArrowDown: () => (view.rx = Math.max(20, view.rx - 4)) }[e.key];
    if (k) { e.preventDefault(); k(); apply(); }
    if (e.key === '+' || e.key === '=') zoom(1.12);
    if (e.key === '-') zoom(1 / 1.12);
  });
  document.getElementById('map-zoom-in').onclick = () => zoom(1.15);
  document.getElementById('map-zoom-out').onclick = () => zoom(1 / 1.15);
  document.getElementById('map-reset').onclick = () => { view = { ...VIEW }; apply(); };

  // fit the scene to small screens
  const fit = () => { VIEW.zoom = scene.clientWidth < 500 ? 0.42 : scene.clientWidth < 700 ? 0.6 : scene.clientWidth < 1100 ? 0.82 : 1; };
  fit(); view.zoom = VIEW.zoom;
  window.addEventListener('resize', () => { fit(); });

  // ---------- top navigation follows the scroll ----------
  const links = [...document.querySelectorAll('.tabs a')];
  const watch = new IntersectionObserver((entries) => {
    for (const e of entries) if (e.isIntersecting) {
      links.forEach((a) => a.classList.toggle('active', a.getAttribute('href') === '#' + e.target.id));
    }
  }, { rootMargin: '-40% 0px -55% 0px' });
  links.forEach((a) => { const t = document.querySelector(a.getAttribute('href')); if (t) watch.observe(t); });

  scenery();
  apply();
  loadToday();
})();
