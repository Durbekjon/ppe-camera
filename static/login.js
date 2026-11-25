document.getElementById('login').onsubmit = async (e) => {
  e.preventDefault();
  const error = document.getElementById('error');
  error.textContent = '';
  try {
    const r = await fetch('/api/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(Object.fromEntries(new FormData(e.target))),
    });
    if (r.ok) location.href = '/';
    else error.textContent = (await r.json().catch(() => ({}))).detail || 'Kirib bo\'lmadi';
  } catch (err) { error.textContent = 'Server javob bermayapti'; }
};
