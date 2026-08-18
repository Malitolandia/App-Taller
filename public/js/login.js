const form = document.getElementById('login-form');
const errorBox = document.getElementById('error-box');
const submitBtn = document.getElementById('submit-btn');

function getNextParam() {
  const params = new URLSearchParams(window.location.search);
  return params.get('next') || '/admin.html';
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  errorBox.innerHTML = '';
  submitBtn.disabled = true;
  submitBtn.textContent = 'Ingresando…';

  const password = document.getElementById('password').value;

  try {
    const res = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    });
    const data = await res.json();

    if (!res.ok) {
      errorBox.innerHTML = `<div class="alert-error">${data.error || 'Error al iniciar sesión'}</div>`;
      submitBtn.disabled = false;
      submitBtn.textContent = 'Ingresar';
      return;
    }

    window.location.href = getNextParam();
  } catch (err) {
    errorBox.innerHTML = `<div class="alert-error">Error de conexión. Intenta de nuevo.</div>`;
    submitBtn.disabled = false;
    submitBtn.textContent = 'Ingresar';
  }
});
