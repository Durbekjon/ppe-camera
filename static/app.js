const $ = (id) => document.getElementById(id);
const LABEL = { helmet: 'Kaskasiz', vest: 'Jiletsiz', entry: 'Taqiqlangan hududda' };
const STATUS = { safe: 'Xavfsiz', danger: 'Xavf', zone: 'Xavfli zona', offline: 'Kamera yo\'q' , blocked: 'Kamera to\'silgan', stopped: 'Kamera to\'xtatilgan' };

// ---------- sound ----------
let soundOn = false, audioCtx = null, lastIncident = null, lastVoice = null, lastReviews = null;

$('btn-sound').onclick = () => {
  soundOn = true;
  audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
  audioCtx.resume();
  $('btn-sound').textContent = '🔊 Ovoz yoqilgan';
  $('btn-sound').classList.add('on');
  beep(880, 0.12, 0.2);
};

function beep(freq, seconds, volume, at = 0) {
  if (!audioCtx) return;
  const osc = audioCtx.createOscillator(), gain = audioCtx.createGain();
  osc.type = 'square'; osc.frequency.value = freq; gain.gain.value = volume;
  osc.connect(gain).connect(audioCtx.destination);
  osc.start(audioCtx.currentTime + at); osc.stop(audioCtx.currentTime + at + seconds);
}

function playAlert(incident) {
  if (!soundOn) return;
  const zone = !!incident.zone;
  const key = incident.missing === 'entry' ? 'entry' : zone ? 'zone' : incident.missing;
  const audio = $('a-' + key);
  let delay = 0;
  if (zone) { for (let i = 0; i < 4; i++) beep(i % 2 ? 660 : 990, 0.2, 0.5, i * 0.22); delay = 900; }
  audio.volume = zone ? 1.0 : 0.45;   // the danger-zone warning is deliberately louder
  audio.currentTime = 0;
  setTimeout(() => audio.play().catch(() => beep(700, 0.5, 0.4)), delay);  // beep if the voice file is missing
}

// ---------- cameras ----------
let selected = '', cameraNames = [];  // '' = the first camera
let liveOpen = false;  // the live video opens only after a camera is picked on the 3D map
const withCamera = (url) => selected ? `${url}${url.includes('?') ? '&' : '?'}camera=${encodeURIComponent(selected)}` : url;

// Called by the 3D map (scroll = true) and by the small camera tiles inside the live card (scroll = false).
function selectCamera(name, scroll = true) {
  const changed = name !== selected;
  if (changed || !liveOpen) {
    selected = name;
    setDrawing(false);
    zones = []; showZones();
    $('video').src = withCamera('/video?t=' + Date.now());
    loadZones();
  }
  liveOpen = true;
  $('live').hidden = false;
  $('pick-hint').hidden = true;
  document.body.classList.add('live-open');
  redraw();
  if (scroll) $('live').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function closeLive() {
  liveOpen = false;
  setDrawing(false);
  $('video').removeAttribute('src');  // stop the stream while nobody watches it
  $('live').hidden = true;
  $('pick-hint').hidden = false;
  document.body.classList.remove('live-open');
  $('map').scrollIntoView({ behavior: 'smooth', block: 'start' });
}
$('btn-close-live').onclick = closeLive;

// "Jonli video" in the top menu: without a chosen camera, point at the map instead.
document.querySelector('.tabs a[href="#live"]').addEventListener('click', (e) => {
  if (liveOpen) return;
  e.preventDefault();
  $('map').scrollIntoView({ behavior: 'smooth', block: 'start' });
  const hint = $('pick-hint');
  hint.classList.remove('flash'); void hint.offsetWidth; hint.classList.add('flash');
});

function showCameras(list, current) {
  cameraNames = list.map((c) => c.name);
  const box = $('cameras');
  box.hidden = list.length < 2;
  if (box.hidden) return;
  if (box.children.length !== list.length) {
    box.replaceChildren(...list.map((c) => {
      const tile = document.createElement('button');
      const img = document.createElement('img'); img.alt = '';
      const label = document.createElement('span');
      tile.append(img, label);
      tile.onclick = () => selectCamera(c.name, false);
      return tile;
    }));
  }
  list.forEach((c, i) => {
    const tile = box.children[i];
    tile.className = `tile ${c.status}${c.name === current ? ' selected' : ''}`;
    tile.querySelector('span').textContent = `${c.name} · ${STATUS[c.status]} · ${c.fps} FPS`;
  });
}

setInterval(() => {  // refresh the small pictures once a second
  if ($('cameras').hidden || !liveOpen) return;
  [...$('cameras').children].forEach((tile, i) => {
    const img = tile.querySelector('img');
    if (img.dataset.busy) return;
    img.dataset.busy = '1';
    img.onload = img.onerror = () => delete img.dataset.busy;
    img.src = `/api/frame?camera=${encodeURIComponent(cameraNames[i])}&t=${Date.now()}`;
  });
}, 1000);

// ---------- status ----------
async function getJSON(url, options) {
  const r = await fetch(url, options);
  if (r.status === 401) location.href = '/login';
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
  return r.json();
}

function chip(id, text, cls) { const el = $(id); el.textContent = text; el.className = 'chip ' + (cls || ''); }

let serverDown = false;

async function poll() {
  try {
    const asked = selected;
    const s = await getJSON(withCamera('/api/status'));
    if (asked !== selected) return;  // another camera was picked meanwhile
    if (serverDown) {  // the stream dies with the server
      serverDown = false;
      if (liveOpen) $('video').src = withCamera('/video?t=' + Date.now());
    }
    // the header shows the most serious camera, so danger elsewhere is not missed
    const many = s.cameras.length > 1;
    $('status').textContent = STATUS[s.overall.status] + (many && s.overall.status !== 'safe' ? ` · ${s.overall.camera}` : '');
    $('status').className = 'status ' + s.overall.status;
    showCameras(s.cameras, s.name);
    if (window.sceneUpdate) window.sceneUpdate(s);  // 3D site map (scene.js)
    $('wrap').classList.toggle('alarm', s.status === 'zone');
    $('offline').hidden = s.camera;
    showRunning(s.running);
    chip('chip-camera', 'Kamera: ' + (!s.running ? "to'xtatilgan" : s.camera ? 'ulangan' : 'uzilgan'), s.camera ? 'ok' : s.running ? 'bad' : '');
    chip('chip-fps', 'FPS: ' + s.fps);
    chip('chip-people', `Ishchilar: ${s.people} · Qoidabuzarlar: ${s.violators}`, s.violators ? 'bad' : '');
    $('demo').checked = s.demo;
    // voice warnings (including reminders) are separate from new incidents
    if (lastVoice !== null && s.voice.seq !== lastVoice && s.voice.seq > 0) playAlert(s.voice);
    lastVoice = s.voice.seq;
    // a mark made elsewhere (Telegram button, another tab)
    if (lastReviews !== null && s.reviews !== lastReviews) { loadIncidents(); loadReport(); }
    lastReviews = s.reviews;
    if (lastIncident === null) { lastIncident = s.last_incident_id; loadIncidents(); loadReport(); }
    else if (s.last_incident_id > lastIncident) {
      await loadIncidents();
      lastIncident = s.last_incident_id;
      loadReport();
    }
  } catch (e) {
    if (e.message === NO_CAMERA && selected) { forgetCamera(); return; }
    serverDown = true;
    $('status').textContent = 'Server javob bermayapti';
    $('status').className = 'status offline';
  }
}

// ---------- incidents ----------
const STATUS_LABEL = { "yangi": "Yangi", "ko'rildi": "Ko'rildi", "hal_qilindi": "Hal qilindi" };
const NEXT_STATUS = { "yangi": "ko'rildi", "ko'rildi": "hal_qilindi", "hal_qilindi": "yangi" };

async function loadIncidents() {
  const st = $('filter-status')?.value || '';
  const ms = $('filter-missing')?.value || '';
  const dt = $('filter-date')?.value || '';
  await loadZoneFilter();
  const zn = $('filter-zone').value;
  let url = '/api/incidents?limit=50';
  if (st) url += '&status=' + encodeURIComponent(st);
  if (ms) url += '&missing=' + encodeURIComponent(ms);
  if (dt) url += '&date=' + encodeURIComponent(dt);
  // option values carry a prefix, so a zone called "1" cannot be mistaken for "any zone"
  if (zn === 'any') url += '&zone=1';
  else if (zn === 'none') url += '&zone=0';
  else if (zn) url += '&zone_name=' + encodeURIComponent(zn.slice(5));

  const list = await getJSON(url);
  const ul = $('incidents');
  ul.replaceChildren();
  if (!list.length) {
    const li = document.createElement('li');
    li.className = 'empty'; li.textContent = 'Hozircha hodisa yo\'q';
    ul.append(li);
  }
  for (const it of list) {
    const li = document.createElement('li');
    if (it.zone) li.className = 'zone';
    if (it.false_alarm) li.classList.add('false-alarm');
    let picture;
    if (it.snapshot) {
      picture = document.createElement('a');
      picture.href = '/snapshots/' + it.snapshot; picture.target = '_blank';
      const img = document.createElement('img');
      img.src = picture.href; img.alt = 'Surat'; img.loading = 'lazy';
      picture.append(img);
    } else {
      picture = document.createElement('span');
      picture.className = 'no-photo'; picture.textContent = "Surat o'chirilgan";
    }
    picture.classList.add('thumb');
    const div = document.createElement('div');
    div.className = 'body';
    const what = document.createElement('div');
    what.className = 'what';
    const title = document.createElement('b');
    title.textContent = it.missing.split(',').map((m) => LABEL[m] || m).join(', ');
    what.append(title);
    if (it.zone) { const b = document.createElement('span'); b.className = 'badge'; b.textContent = it.zone_name || 'Xavfli zona'; what.append(b); }

    const stBadge = document.createElement('span');
    const curSt = it.status || 'yangi';
    stBadge.className = 'status-badge status-' + (curSt === "ko'rildi" ? "korildi" : curSt);
    stBadge.textContent = STATUS_LABEL[curSt] || curSt;
    stBadge.title = "Holatni o'zgartirish uchun bosing";
    stBadge.onclick = async () => {
      const next = NEXT_STATUS[curSt] || 'yangi';
      try {
        await getJSON(`/api/incidents/${it.id}/status`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status: next })
        });
        await loadIncidents();
      } catch (err) { $('hint').textContent = err.message; }
    };
    what.append(stBadge);

    const when = document.createElement('div');
    when.className = 'when'; when.title = it.ts;
    when.textContent = `№${it.id} · ${shortTime(it.ts)}` + (cameraNames.length > 1 && it.camera ? ` · ${it.camera}` : '');
    const mark = document.createElement('button');
    mark.className = 'mark';
    mark.textContent = it.false_alarm ? 'Belgini olib tashlash' : "Noto'g'ri signal";
    mark.onclick = async () => {
      mark.disabled = true;
      try {
        await getJSON(`/api/incidents/${it.id}/false-alarm`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ value: !it.false_alarm }),
        });
        await loadIncidents();
        loadReport();
      } catch (err) { mark.disabled = false; $('hint').textContent = err.message; }
    };
    if (it.false_alarm) when.textContent += " · hisobotga kirmaydi";
    div.append(what, when, mark);
    li.append(picture, div);
    ul.append(li);
  }
  const count = $('incident-count');
  count.hidden = !list.length;
  count.textContent = list.length >= 50 ? 'oxirgi 50' : `${list.length} ta`;
  $('filters-clear').hidden = !FILTERS.some((id) => $(id).value);
  return list;
}

// "2026-11-26 10:56:44" -> "10:56" today, "25.11 10:56" on other days
function shortTime(ts) {
  const [day, time = ''] = ts.split(' ');
  const hm = time.slice(0, 5);
  return day === today() ? `bugun ${hm}` : `${day.slice(8, 10)}.${day.slice(5, 7)} ${hm}`;
}

const FILTERS = ['filter-status', 'filter-missing', 'filter-zone', 'filter-date'];
FILTERS.forEach((id) => { $(id).onchange = loadIncidents; });
$('filters-clear').onclick = () => { FILTERS.forEach((id) => { $(id).value = ''; }); loadIncidents(); };

async function loadZoneFilter() {
  const { names } = await getJSON('/api/incidents/zone-names');
  const select = $('filter-zone'), chosen = select.value;
  const options = [['', 'Barchasi'], ['any', 'Zonada (hammasi)'], ['none', 'Zonadan tashqari'],
    ...names.map((n) => ['name:' + n, n])];
  if (select.options.length === options.length && options.every(([v], i) => select.options[i].value === v)) return;
  select.replaceChildren(...options.map(([value, text]) => new Option(text, value)));
  select.value = options.some(([v]) => v === chosen) ? chosen : '';
}

// ---------- report ----------
function today() { const d = new Date(); return new Date(d - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10); }

const PLOT_H = 150;  // px height of the tallest bar

// One stacked bar per item: { n, z (part in a zone), label, title, cls }. Writes into `chart`.
function drawBars(chart, items, emptyText) {
  const max = Math.max(1, ...items.map((d) => d.n));
  chart.replaceChildren();
  chart.style.gridTemplateColumns = `repeat(${items.length}, minmax(0, 1fr))`;
  chart.classList.toggle('dense', items.length > 31);
  for (const d of items) {
    const col = document.createElement('div');
    col.className = 'col' + (d.cls ? ' ' + d.cls : '');
    col.title = d.title;
    const plot = document.createElement('div'); plot.className = 'plot';
    const num = document.createElement('span'); num.className = 'n';
    num.textContent = d.n && items.length <= 31 ? d.n : '';
    const stack = document.createElement('div'); stack.className = 'stack';
    if (d.n) {
      const h = Math.max(4, Math.round((d.n / max) * PLOT_H));
      stack.style.height = h + 'px';
      const base = document.createElement('i'); base.className = 'b';
      const zone = document.createElement('i'); zone.className = 'z';
      zone.style.height = Math.round((d.z / d.n) * h) + 'px';
      stack.append(base, zone);
    } else stack.classList.add('zero');
    plot.append(num, stack);
    const label = document.createElement('span'); label.className = 'h'; label.textContent = d.label;
    col.append(plot, label);
    chart.append(col);
  }
  if (emptyText && !items.some((d) => d.n)) {
    const empty = document.createElement('div'); empty.className = 'chart-empty'; empty.textContent = emptyText;
    chart.append(empty);
  }
}

function dayBefore(iso) { const d = new Date(`${iso}T00:00:00Z`); d.setUTCDate(d.getUTCDate() - 1); return d.toISOString().slice(0, 10); }

async function loadReport() {
  loadTrend();
  const day = $('report-date').value || today();
  const [r, prev] = await Promise.all([getJSON('/api/report?date=' + day), getJSON('/api/report?date=' + dayBefore(day))]);
  const isToday = day === today();
  $('stat-total').textContent = r.total;
  const diff = r.total - prev.total, delta = $('stat-delta');
  delta.textContent = `${isToday ? 'kechaga' : 'oldingi kunga'} nisbatan ${diff > 0 ? '+' : ''}${diff}`;
  delta.className = 'delta ' + (diff > 0 ? 'up' : diff < 0 ? 'down' : '');
  $('stat-zone').textContent = r.zone;
  $('stat-zone-share').textContent = r.total ? `jamining ${Math.round((r.zone / r.total) * 100)}%` : '';
  const max = Math.max(...r.by_hour), peak = r.by_hour.indexOf(max);
  $('stat-peak').textContent = max ? String(peak).padStart(2, '0') + ':00' : '—';
  $('stat-peak-n').textContent = max ? `${max} ta buzilish` : 'buzilish yo\'q';
  const nowHour = new Date().getHours();
  drawBars($('chart'), r.by_hour.map((n, h) => ({
    n, z: (r.zone_by_hour || [])[h] || 0,
    label: h % 3 === 0 ? String(h).padStart(2, '0') : '',
    title: `${String(h).padStart(2, '0')}:00–${String(h).padStart(2, '0')}:59 — ${n} ta` + (n ? ` (zonada: ${(r.zone_by_hour || [])[h] || 0})` : ''),
    cls: [max && n === max ? 'peak' : '', isToday && h === nowHour ? 'now' : ''].join(' ').trim(),
  })), isToday ? 'Bugun hali buzilish yo\'q' : 'Bu kunda buzilish yo\'q');
}
$('report-date').value = today();
$('report-date').onchange = loadReport;

function isoDaysAgo(n) { const d = new Date(`${today()}T00:00:00Z`); d.setUTCDate(d.getUTCDate() - n); return d.toISOString().slice(0, 10); }

function trendQuery() {
  const choice = $('trend-days').value;
  if (choice !== 'custom') return 'days=' + encodeURIComponent(choice);
  const start = $('trend-start').value, end = $('trend-end').value;
  return start && end ? `start=${start}&end=${end}` : null;
}

let trendRequest = 0;

async function loadTrend() {
  const query = trendQuery(), mine = ++trendRequest;
  const button = $('btn-export-xlsx'), chart = $('trend-chart'), error = $('trend-error');
  const fail = (message) => { error.textContent = message; chart.replaceChildren(); button.classList.add('disabled'); button.removeAttribute('href'); };
  if (!query) return fail('Ikkala sanani ham tanlang.');
  let res;
  try { res = await getJSON('/api/trend?' + query); }
  catch (err) { if (mine === trendRequest) fail(err.message); return; }
  if (mine !== trendRequest) return;  // a newer choice is already loading
  error.textContent = '';
  button.classList.remove('disabled');
  button.href = `/api/export.xlsx?start=${res.start}&end=${res.end}`;  // exactly the period on screen
  const step = Math.ceil(res.days.length / 10);  // keep date labels readable
  const now = today(), total = res.days.reduce((s, d) => s + d.total, 0);
  drawBars(chart, res.days.map((d, i) => ({
    n: d.total, z: d.zone,
    label: d.date === now && res.days.length <= 14 ? 'Bugun' : i % step === 0 ? `${d.date.slice(8, 10)}.${d.date.slice(5, 7)}` : '',
    title: `${d.date} — ${d.total} ta (zonada: ${d.zone})`,
    cls: d.date === $('report-date').value ? 'now' : '',
  })), 'Bu davrda buzilish yo\'q');
  $('stat-period').textContent = total;
  $('stat-period-sub').textContent = `${res.days.length} kun · kuniga o'rtacha ${(total / res.days.length).toFixed(1)}`;
}

$('trend-days').onchange = () => {
  const custom = $('trend-days').value === 'custom';
  $('trend-range').hidden = !custom;
  if (custom && !$('trend-start').value) { $('trend-start').value = isoDaysAgo(13); $('trend-end').value = today(); }
  loadTrend();
};
$('trend-start').onchange = $('trend-end').onchange = loadTrend;

// ---------- danger zone drawing ----------
const canvas = $('canvas'), ctx = canvas.getContext('2d');
let drawing = false, points = [], zones = [];

function redraw() {
  const r = canvas.getBoundingClientRect();
  canvas.width = r.width; canvas.height = r.height;
  ctx.clearRect(0, 0, r.width, r.height);
  if (!drawing || !points.length) return;
  ctx.beginPath();
  points.forEach(([x, y], i) => ctx[i ? 'lineTo' : 'moveTo'](x * r.width, y * r.height));
  if (points.length > 2) ctx.closePath();
  ctx.fillStyle = 'rgba(229,72,77,.25)'; ctx.strokeStyle = '#ffd43b'; ctx.lineWidth = 2;
  ctx.fill(); ctx.stroke();
  ctx.fillStyle = '#ffd43b';
  for (const [x, y] of points) { ctx.beginPath(); ctx.arc(x * r.width, y * r.height, 5, 0, 7); ctx.fill(); }
}

function setDrawing(on) {
  drawing = on; points = [];
  canvas.classList.toggle('drawing', on);
  $('btn-draw').classList.toggle('active', on);
  $('btn-save').hidden = $('btn-cancel').hidden = !on;
  $('zone-form').hidden = !on;
  if (on) { $('zone-form').reset(); $('zone-form').elements.name.value = nextName(); }
  $('hint').textContent = on ? 'Video ustiga bosib nuqtalar qo\'ying (kamida 3 ta), so\'ng "Saqlash" tugmasini bosing.' : '';
  redraw();
}

canvas.onclick = (e) => {
  const r = canvas.getBoundingClientRect();
  points.push([(e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height]);
  redraw();
};
$('btn-draw').onclick = () => setDrawing(!drawing);
$('btn-cancel').onclick = () => setDrawing(false);

function nextName() {
  let n = 1;
  while (zones.some((z) => z.name.toLowerCase() === `zona ${n}`)) n++;
  return `Zona ${n}`;
}

function showZones() {
  const ul = $('zones');
  ul.replaceChildren();
  zones.forEach((z, i) => {
    const li = document.createElement('li');
    const text = document.createElement('span');
    const rule = z.rule === 'no_entry' ? 'hech kim kirmasin' : 'himoya vositasi shart';
    text.textContent = `${z.name} · ${rule} · ${z.start ? `${z.start}–${z.end}` : 'doim'}`;
    const del = document.createElement('button');
    del.className = 'admin-only'; del.textContent = "O'chirish";
    del.onclick = () => saveZones(zones.filter((_, j) => j !== i), `"${z.name}" o'chirildi.`);
    li.append(text, del);
    ul.append(li);
  });
}

async function saveZones(next, message) {
  try {
    const r = await getJSON(withCamera('/api/zones'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ zones: next }) });
    zones = r.zones;
    showZones();
    $('hint').textContent = message;
    return true;
  } catch (err) { $('hint').textContent = err.message; return false; }
}

$('zone-form').onsubmit = (e) => { e.preventDefault(); $('btn-save').click(); };
$('btn-save').onclick = async () => {
  if (points.length < 3) { $('hint').textContent = 'Kamida 3 ta nuqta kerak.'; return; }
  const zone = { ...Object.fromEntries(new FormData($('zone-form'))), points };
  if (await saveZones([...zones, zone], 'Zona saqlandi.')) {
    const message = $('hint').textContent;
    setDrawing(false);
    $('hint').textContent = message;
  }
};
async function loadZones() {
  const asked = selected;
  const r = await getJSON(withCamera('/api/zones'));
  if (asked === selected) { zones = r.zones; showZones(); }
}
loadZones();
window.addEventListener('resize', redraw);

// The server was restarted with other cameras: the chosen name is gone, so use the first camera.
const NO_CAMERA = "Bunday kamera yo'q";
function forgetCamera() {
  selected = '';
  $('cameras').replaceChildren();
  if (liveOpen) { $('video').src = withCamera('/video?t=' + Date.now()); loadZones(); }
}

// ---------- start / stop the camera ----------
let running = true;
function showRunning(on) {
  running = on;
  const b = $('btn-run');
  b.textContent = on ? "⏹ To'xtatish" : '▶ Boshlash';
  b.classList.toggle('stopped', !on);
  $('offline-text').textContent = on ? 'Kamera uzildi. Qayta ulanmoqda…' : "Kamera to'xtatilgan: tahlil va ogohlantirishlar o'chiq.";
  $('btn-start-big').hidden = on;
  $('wrap').classList.toggle('stopped', !on);
}
async function setRunning(on) {
  const b = $('btn-run');
  b.disabled = $('btn-start-big').disabled = true;
  try {
    const r = await getJSON(withCamera('/api/camera/run'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ on }) });
    showRunning(r.running);
    if (r.running && liveOpen) $('video').src = withCamera('/video?t=' + Date.now());
    $('hint').textContent = r.running ? 'Kamera ishga tushdi. Rasm bir necha soniyada chiqadi.' : "Kamera to'xtatildi. Qayta yoqish uchun ▶ Boshlash.";
  } catch (e) {
    if (e.message === NO_CAMERA) {
      forgetCamera();
      $('hint').textContent = "Kameralar ro'yxati o'zgargan (server qayta ishga tushgan). Yana bir marta bosing.";
    } else $('hint').textContent = 'Bajarilmadi: ' + e.message;
  } finally {
    b.disabled = $('btn-start-big').disabled = false;
  }
}
$('btn-run').onclick = () => {
  if (running && !confirm(`"${selected || 'Kamera'}" to'xtatilsinmi? To'xtatilganda buzilishlar aniqlanmaydi.`)) return;
  setRunning(!running);
};
$('btn-start-big').onclick = () => setRunning(true);

// ---------- demo mode + telegram test ----------
$('demo').onchange = async (e) => {
  try {
    await getJSON(withCamera('/api/demo'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ on: e.target.checked }) });
    await loadZones();  // demo video and live camera each keep their own zones
    $('hint').textContent = e.target.checked ? 'Demo rejimi: demo videoning zonalari.' : 'Real kamera: real kameraning zonalari.';
  }
  catch (err) { e.target.checked = !e.target.checked; $('hint').textContent = err.message; }
};
$('btn-telegram').onclick = async () => {
  const r = await getJSON('/api/telegram-test', { method: 'POST' });
  $('system-hint').textContent = r.ok ? 'Telegram: sinov xabari yuborildi.' : 'Telegram xatosi: ' + r.error;
};

// ---------- user ----------
getJSON('/api/me').then((u) => {
  document.body.classList.add('role-' + u.role);
  $('user-name').textContent = `${u.username} (${u.role === 'admin' ? 'admin' : 'nazoratchi'})`;
});
$('btn-logout').onclick = async () => { await getJSON('/api/logout', { method: 'POST' }); location.href = '/login'; };

// ---------- system status ----------
function ago(seconds) {
  if (seconds === null || seconds === undefined) return '';
  if (seconds < 60) return `${seconds} soniya oldin`;
  return seconds < 3600 ? `${Math.floor(seconds / 60)} daqiqa oldin` : `${Math.floor(seconds / 3600)} soat oldin`;
}

async function loadSystem() {
  let s;
  try { s = await getJSON('/api/system'); }
  catch (err) { $('system-age').textContent = '(yangilanmadi)'; return; }  // old rows stay, marked as stale
  $('system-age').textContent = '';
  const t = s.telegram, details = [];
  if (t.level !== 'off') {
    details.push(`navbatda: ${t.waiting}`);
    if (t.last_ok_s !== null) details.push(`oxirgi yuborilgan: ${ago(t.last_ok_s)}`);
    if (t.last_error) details.push(`xato (${ago(t.last_error_s)}): ${t.last_error}`);
  }
  const rows = [
    [t.level, 'Telegram', [t.text, ...details].join(' · ')],
    [s.buttons.level, 'Telegram tugmalari', s.buttons.text],
    [s.skeleton ? 'ok' : 'off', 'Skelet rejimi', s.skeleton ? 'yoqilgan' : "o'chirilgan"],
    [s.blur_faces ? 'ok' : 'warn', 'Yuzni xiralashtirish', s.blur_faces ? 'yoqilgan (saqlanadigan suratlarda)' : "o'chirilgan"],
    [s.retention_days > 0 ? 'ok' : 'warn', 'Suratlar saqlanishi', s.retention_days > 0 ? `${s.retention_days} kun` : "cheklanmagan"],
    [s.local_audio ? 'ok' : 'off', 'Kompyuter karnayi', s.local_audio ? 'yoqilgan' : "o'chirilgan"],
  ];
  $('system').replaceChildren(...rows.map(([level, name, text]) => {
    const li = document.createElement('li');
    li.className = level;
    const b = document.createElement('b'); b.textContent = name;
    const span = document.createElement('span'); span.textContent = text;
    li.append(b, span);
    return li;
  }));
  // the header chip must not say "connected" while deliveries fail
  chip('chip-telegram', 'Telegram: ' + (t.level === 'off' ? 'sozlanmagan' : t.level === 'bad' ? `xato (navbatda ${t.waiting})`
    : t.level === 'warn' ? `qayta yuborilmoqda (${t.retrying})` : 'sozlangan'),
  t.level === 'bad' ? 'bad' : t.level === 'ok' ? 'ok' : '');
}
loadSystem();
setInterval(loadSystem, 5000);

poll();
setInterval(poll, 500);
