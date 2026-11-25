const $ = (id) => document.getElementById(id);
const LABEL = { helmet: 'Kaskasiz', vest: 'Jiletsiz' };
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
  const key = zone ? 'zone' : incident.missing;
  const audio = $('a-' + key);
  let delay = 0;
  if (zone) { for (let i = 0; i < 4; i++) beep(i % 2 ? 660 : 990, 0.2, 0.5, i * 0.22); delay = 900; }
  audio.volume = zone ? 1.0 : 0.45;   // the danger-zone warning is deliberately louder
  audio.currentTime = 0;
  setTimeout(() => audio.play().catch(() => beep(700, 0.5, 0.4)), delay);  // beep if the voice file is missing
}

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
    const s = await getJSON('/api/status');
    if (serverDown) { serverDown = false; $('video').src = '/video?' + Date.now(); }  // stream dies with the server
    $('status').textContent = STATUS[s.status];
    $('status').className = 'status ' + s.status;
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
async function loadIncidents() {
  const list = await getJSON('/api/incidents?limit=30');
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
    const a = document.createElement('a');
    a.href = '/snapshots/' + it.snapshot; a.target = '_blank';
    const img = document.createElement('img');
    img.src = a.href; img.alt = 'Surat'; img.loading = 'lazy';
    a.append(img);
    const div = document.createElement('div');
    const what = document.createElement('div');
    what.className = 'what';
    what.textContent = it.missing.split(',').map((m) => LABEL[m] || m).join(', ');
    if (it.zone) { const b = document.createElement('span'); b.className = 'badge'; b.textContent = 'XAVFLI ZONA'; what.append(b); }
    const when = document.createElement('div');
    when.className = 'when'; when.textContent = `№${it.id} · ${it.ts}`;
    div.append(what, when);
    li.append(a, div);
    ul.append(li);
  }
  $('incident-count').textContent = list.length ? `(oxirgi ${list.length} ta)` : '';
  return list;
}

// ---------- report ----------
function today() { const d = new Date(); return new Date(d - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10); }

async function loadReport() {
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

// ---------- danger zone drawing ----------
const canvas = $('canvas'), ctx = canvas.getContext('2d');
let drawing = false, points = [];

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
$('btn-save').onclick = async () => {
  if (points.length < 3) { $('hint').textContent = 'Kamida 3 ta nuqta kerak.'; return; }
  await getJSON('/api/zone', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ points }) });
  setDrawing(false);
  $('hint').textContent = 'Xavfli zona saqlandi.';
};
$('btn-clear').onclick = async () => {
  await getJSON('/api/zone', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ points: [] }) });
  setDrawing(false);
  $('hint').textContent = 'Xavfli zona o\'chirildi.';
};
window.addEventListener('resize', redraw);

// ---------- demo mode + telegram test ----------
$('demo').onchange = async (e) => {
  try { await getJSON('/api/demo', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ on: e.target.checked }) }); }
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
