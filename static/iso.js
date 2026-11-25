// Decorative isometric scene for public pages (login, landing). Shows no real data.
window.buildIsoScene = (world, { spin = true, zoom = 0.9 } = {}) => {
  if (!world) return;
  const box = (cls, x, y, w, d, h) => {
    const el = document.createElement('div');
    el.className = 'obj ' + cls;
    el.style.cssText = `--x:${x}px;--y:${y}px;--w:${w}px;--d:${d}px;--h:${h}px`;
    for (const f of ['back', 'left', 'front', 'side', 'top']) {
      const face = document.createElement('div'); face.className = 'face ' + f; el.append(face);
    }
    world.append(el);
    return el;
  };
  const path = (x1, y1, x2, y2) => {
    const p = document.createElement('div'); p.className = 'path';
    p.style.cssText = `left:${x1}px;top:${y1}px;width:${Math.hypot(x2 - x1, y2 - y1)}px;` +
      `transform:translateZ(1px) rotate(${Math.atan2(y2 - y1, x2 - x1)}rad)`;
    world.append(p);
  };
  const buildings = [[-330, -70, 180, 120, 70], [150, -70, 170, 120, 60], [-90, -320, 180, 110, 80], [-90, 200, 180, 110, 55]];
  for (const [x, y, w, d] of buildings) path(x + w / 2, y + d / 2, 0, 0);
  const made = buildings.map((b) => box('building', ...b));
  box('prop blue', -45, -45, 90, 90, 34);
  [[-470, -430, 40, 40, 110], [-410, -430, 40, 40, 80], [380, -470, 70, 70, 26], [400, 380, 60, 120, 30]]
    .forEach((b) => box('prop', ...b));
  [[-480, 300], [-430, 350], [440, -300], [470, 200], [-200, 460], [180, -470]].forEach(([x, y]) => box('tree', x, y, 22, 22, 22));

  world.style.setProperty('--rx', '58deg');
  world.style.setProperty('--zoom', zoom);
  let rz = -42, last = performance.now();
  const still = !spin || matchMedia('(prefers-reduced-motion: reduce)').matches;
  const tick = (now) => {
    rz += (now - last) * 0.004;  // about one turn every 90 seconds
    last = now;
    world.style.setProperty('--rz', rz + 'deg');
    if (!still) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
  return made;
};
