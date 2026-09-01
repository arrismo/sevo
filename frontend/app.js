const form = document.querySelector('#ask-form');
const question = document.querySelector('#question');
const askButton = document.querySelector('#ask');
const catchUpButton = document.querySelector('#catch-up');
const result = document.querySelector('#result');

function setBusy(isBusy, label) {
  askButton.disabled = isBusy;
  catchUpButton.disabled = isBusy;
  if (label) label.firstElementChild.textContent = isBusy ? 'Checking…' : label === askButton ? 'Ask Sevo' : 'Catch me up';
}

async function showResponse(url, options, activeButton) {
  setBusy(true, activeButton);
  result.hidden = true;
  result.classList.remove('error');

  try {
    const response = await fetch(url, options);
    if (!response.ok) throw new Error('Request failed');
    const payload = await response.json();
    result.textContent = payload.answer || payload.summary;
    if (payload.unavailable_sources?.length) {
      result.textContent += `\n\nUnavailable: ${payload.unavailable_sources.join(', ')}. Other sources were still checked.`;
    }
  } catch (_) {
    result.textContent = 'Sevo could not answer right now. Please try again.';
    result.classList.add('error');
  } finally {
    result.hidden = false;
    setBusy(false, activeButton);
  }
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  const message = question.value.trim();
  if (!message) return;
  showResponse('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  }, askButton);
});

catchUpButton.addEventListener('click', () => {
  showResponse('/api/catch-up', { method: 'POST' }, catchUpButton);
});
