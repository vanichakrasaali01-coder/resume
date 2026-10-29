const menuButton = document.querySelector('.menu-button');
const navLinks = document.querySelector('.nav-links');

menuButton.addEventListener('click', () => {
  const open = navLinks.classList.toggle('open');
  menuButton.setAttribute('aria-expanded', String(open));
});

navLinks.querySelectorAll('a').forEach(link => link.addEventListener('click', () => {
  navLinks.classList.remove('open');
}));

const form = document.querySelector('#appointment-form');
form.addEventListener('submit', async event => {
  event.preventDefault();
  const submitButton = form.querySelector('button[type="submit"]');
  const message = form.querySelector('.form-message');
  const data = Object.fromEntries(new FormData(form));
  const phoneDigits = data.phone.replace(/\D/g, '');

  message.textContent = '';
  if (data.name.trim().length < 2) {
    message.textContent = 'Please enter your full name.';
    return;
  }
  if (phoneDigits.length < 10) {
    message.textContent = 'Please enter a valid phone number.';
    return;
  }

  submitButton.disabled = true;
  submitButton.textContent = 'Sending request...';
  try {
    const response = await fetch('/api/appointment-requests', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Request could not be submitted.');
    message.textContent = `Thank you${data.name.trim() ? ', ' + data.name.trim() : ''}. Your request has been received. Our care team will contact you shortly.`;
    form.reset();
  } catch (error) {
    message.textContent = error.message;
  } finally {
    submitButton.disabled = false;
    submitButton.innerHTML = 'Request appointment →';
  }
});
