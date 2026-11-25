const $ = (id) => document.getElementById(id);
const LABEL = { helmet: 'Kaskasiz', vest: 'Jiletsiz', entry: 'Taqiqlangan hududda' };
const STATUS = { safe: 'Xavfsiz', danger: 'Xavf', zone: 'Xavfli zona', offline: 'Kamera yo\'q' };

// ---------- sound ----------
let soundOn = false, audioCtx = null, lastIncident = null, lastVoice = null;

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
const withCamera = (url) => selected ? `${url}${url.includes('?') ? '&' : '?'}camera=${encodeURIComponent(selected)}` : url;

function selectCamera(name) {
  if (name === selected) return;
  selected = name;
  setDrawing(false);
  zones = []; showZones();
  $('video').src = withCamera('/video?t=' + Date.now());
  loadZones();
}

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
      tile.onclick = () => selectCamera(c.name);
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
  if ($('cameras').hidden) return;
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
    if (serverDown) { serverDown = false; $('video').src = withCamera('/video?t=' + Date.now()); }  // stream dies with the server
    // the header shows the most serious camera, so danger elsewhere is not missed
    const many = s.cameras.length > 1;
    $('status').textContent = STATUS[s.overall.status] + (many && s.overall.status !== 'safe' ? ` · ${s.overall.camera}` : '');
    $('status').className = 'status ' + s.overall.status;
    showCameras(s.cameras, s.name);
    $('wrap').classList.toggle('alarm', s.status === 'zone');
    $('offline').hidden = s.camera;
    chip('chip-camera', 'Kamera: ' + (s.camera ? 'ulangan' : 'uzilgan'), s.camera ? 'ok' : 'bad');
    chip('chip-fps', 'FPS: ' + s.fps);
    chip('chip-people', `Ishchilar: ${s.people} · Qoidabuzarlar: ${s.violators}`, s.violators ? 'bad' : '');
    chip('chip-telegram', 'Telegram: ' + (s.telegram ? 'ulangan' : 'sozlanmagan'), s.telegram ? 'ok' : '');
    $('demo').checked = s.demo;
    // voice warnings (including reminders) are separate from new incidents
    if (lastVoice !== null && s.voice.seq !== lastVoice && s.voice.seq > 0) playAlert(s.voice);
    lastVoice = s.voice.seq;
    if (lastIncident === null) { lastIncident = s.last_incident_id; loadIncidents(); loadReport(); }
    else if (s.last_incident_id > lastIncident) {
      await loadIncidents();
      lastIncident = s.last_incident_id;
      loadReport();
    }
  } catch (e) {
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
    const div = document.createElement('div');
    const what = document.createElement('div');
    what.className = 'what';
    what.textContent = it.missing.split(',').map((m) => LABEL[m] || m).join(', ');
    if (it.zone) { const b = document.createElement('span'); b.className = 'badge'; b.textContent = it.zone_name || 'XAVFLI ZONA'; what.append(b); }

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
    when.className = 'when'; when.textContent = `№${it.id} · ${it.ts}` + (cameraNames.length > 1 && it.camera ? ` · ${it.camera}` : '');
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
    if (it.false_alarm) when.textContent += " · noto'g'ri signal (hisobotga kirmaydi)";
    div.append(what, when, mark);
    li.append(picture, div);
    ul.append(li);
  }
  $('incident-count').textContent = list.length ? `(oxirgi ${list.length} ta)` : '';
  return list;
}

$('filter-status').onchange = loadIncidents;
$('filter-missing').onchange = loadIncidents;
$('filter-date').onchange = loadIncidents;
$('filter-zone').onchange = loadIncidents;

async function loadZoneFilter() {
  const { names } = await getJSON('/api/incidents/zone-names');
  const select = $('filter-zone'), chosen = select.value;
  const options = [['', 'Zona: Barchasi'], ['any', 'Zonada (hammasi)'], ['none', 'Zonadan tashqari'],
    ...names.map((n) => ['name:' + n, n])];
  if (select.options.length === options.length && options.every(([v], i) => select.options[i].value === v)) return;
  select.replaceChildren(...options.map(([value, text]) => new Option(text, value)));
  select.value = options.some(([v]) => v === chosen) ? chosen : '';
}

// ---------- report ----------
function today() { const d = new Date(); return new Date(d - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10); }

async function loadReport() {
  loadTrend();
  const r = await getJSON('/api/report?date=' + ($('report-date').value || today()));
  $('stat-total').textContent = r.total;
  $('stat-zone').textContent = r.zone;
  const max = Math.max(...r.by_hour);
  $('stat-peak').textContent = max ? String(r.by_hour.indexOf(max)).padStart(2, '0') + ':00' : '—';
  const chart = $('chart');
  chart.replaceChildren();
  r.by_hour.forEach((n, h) => {
    const bar = document.createElement('div'); bar.className = 'bar'; bar.title = `${h}:00 — ${n} ta`;
    const num = document.createElement('span'); num.className = 'n'; num.textContent = n || '';
    const fill = document.createElement('i');
    if (n) fill.style.height = Math.round((n / max) * 140) + 'px'; else fill.className = 'zero';
    const label = document.createElement('span'); label.className = 'h'; label.textContent = String(h).padStart(2, '0');
    bar.append(num, fill, label);
    chart.append(bar);
  });
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
  chart.replaceChildren();
  chart.style.gridTemplateColumns = `repeat(${res.days.length}, minmax(0, 1fr))`;
  chart.style.gap = res.days.length > 60 ? '0' : '2px';
  const max = Math.max(1, ...res.days.map((d) => d.total));
  const step = Math.ceil(res.days.length / 10);  // keep date labels readable
  res.days.forEach((d, i) => {
    const bar = document.createElement('div');
    bar.className = 'bar';
    bar.title = `${d.date} — ${d.total} ta (zonada: ${d.zone})`;
    const num = document.createElement('span'); num.className = 'n'; num.textContent = res.days.length <= 31 ? d.total || '' : '';
    const fill = document.createElement('i');
    if (d.total) fill.style.height = Math.max(2, Math.round((d.total / max) * 140)) + 'px'; else fill.className = 'zero';
    const label = document.createElement('span'); label.className = 'h'; label.textContent = i % step === 0 ? d.date.slice(5) : '';
    bar.append(num, fill, label);
    chart.append(bar);
  });
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

// ---------- demo mode + telegram test ----------
$('demo').onchange = async (e) => {
  try { await getJSON(withCamera('/api/demo'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ on: e.target.checked }) }); }
  catch (err) { e.target.checked = !e.target.checked; $('hint').textContent = err.message; }
};
$('btn-telegram').onclick = async () => {
  const r = await getJSON('/api/telegram-test', { method: 'POST' });
  $('hint').textContent = r.ok ? 'Telegram: sinov xabari yuborildi.' : 'Telegram xatosi: ' + r.error;
};

// ---------- user ----------
getJSON('/api/me').then((u) => {
  document.body.classList.add('role-' + u.role);
  $('user-name').textContent = `${u.username} (${u.role === 'admin' ? 'admin' : 'nazoratchi'})`;
});
$('btn-logout').onclick = async () => { await getJSON('/api/logout', { method: 'POST' }); location.href = '/login'; };

poll();
setInterval(poll, 500);
