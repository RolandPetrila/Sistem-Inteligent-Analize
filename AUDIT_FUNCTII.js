const LS_KEY = 'ris_audit_key';

function saveKey() {
  const v = document.getElementById('risKeyInput').value.trim();
  const status = document.getElementById('keyStatus');
  if (v) { sessionStorage.setItem(LS_KEY, v); status.textContent = 'salvata in sesiune'; }
  else { sessionStorage.removeItem(LS_KEY); status.textContent = ''; }
}

function restoreKey() {
  const v = sessionStorage.getItem(LS_KEY);
  if (v) {
    document.getElementById('risKeyInput').value = v;
    document.getElementById('keyStatus').textContent = 'incarcata din sesiune';
  }
}

async function liveTest(btn) {
  const method = btn.dataset.method, path = btn.dataset.path;
  if (path.includes('{')) {
    btn.textContent = 'are parametri — vezi curl';
    btn.className = 'btn-test result-fail';
    setTimeout(() => { btn.textContent = 'Testeaza live'; btn.className = 'btn-test'; }, 3000);
    return;
  }
  const key = sessionStorage.getItem(LS_KEY) || '';
  btn.disabled = true; const orig = btn.textContent; btn.textContent = '...';
  try {
    const res = await fetch(path, { method, headers: key ? {'X-RIS-Key': key} : {} });
    btn.textContent = res.ok ? ('OK ' + res.status) : ('EROARE ' + res.status);
    btn.className = 'btn-test ' + (res.ok ? 'result-ok' : 'result-fail');
  } catch (e) {
    btn.textContent = 'EROARE retea'; btn.className = 'btn-test result-fail';
  }
  setTimeout(() => { btn.disabled = false; btn.textContent = orig; btn.className = 'btn-test'; }, 4000);
}

async function liveTestProvider(btn) {
  const provider = btn.dataset.provider;
  const key = sessionStorage.getItem(LS_KEY) || '';
  btn.disabled = true; const orig = btn.textContent; btn.textContent = '...';
  try {
    const res = await fetch('/api/settings/test/' + provider, { method: 'POST', headers: key ? {'X-RIS-Key': key} : {} });
    const data = await res.json().catch(() => ({}));
    const ok = res.ok && data.ok !== false;
    btn.textContent = ok ? 'OK' : ('EROARE: ' + (data.message || res.status));
    btn.className = 'btn-test ' + (ok ? 'result-ok' : 'result-fail');
  } catch (e) {
    btn.textContent = 'EROARE retea'; btn.className = 'btn-test result-fail';
  }
  setTimeout(() => { btn.disabled = false; btn.textContent = orig; btn.className = 'btn-test'; }, 5000);
}

function filterEp(mode, activeBtn) {
  document.querySelectorAll('.filters button').forEach(b => b.classList.remove('active'));
  activeBtn.classList.add('active');
  document.querySelectorAll('.ep-table tbody tr').forEach(tr => {
    let show = true;
    if (mode === 'tested') show = tr.dataset.tested === 'true';
    else if (mode === 'untested') show = tr.dataset.tested === 'false';
    else if (mode === 'safe') show = !!tr.querySelector('.btn-test');
    tr.style.display = show ? '' : 'none';
  });
  document.querySelectorAll('.cat-block').forEach(block => {
    const visible = [...block.querySelectorAll('tbody tr')].some(tr => tr.style.display !== 'none');
    block.style.display = visible ? '' : 'none';
  });
}

document.addEventListener('DOMContentLoaded', () => {
  restoreKey();
  document.getElementById('saveKeyBtn').addEventListener('click', saveKey);
  document.querySelectorAll('.filters button[data-filter]').forEach(b => {
    b.addEventListener('click', () => filterEp(b.dataset.filter, b));
  });
  document.querySelectorAll('button[data-kind="endpoint"]').forEach(b => {
    b.addEventListener('click', () => liveTest(b));
  });
  document.querySelectorAll('button[data-kind="provider"]').forEach(b => {
    b.addEventListener('click', () => liveTestProvider(b));
  });
});
