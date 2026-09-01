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

function escapeHtml(value) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function renderInlineMarkdown(value) {
  return escapeHtml(value).replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');
}

function renderMessage(value) {
  const lines = String(value || '').split(/\r?\n/);
  const blocks = [];
  let paragraph = [];
  let list = [];

  const flushParagraph = () => {
    if (!paragraph.length) return;
    blocks.push(`<p>${paragraph.map(renderInlineMarkdown).join('<br>')}</p>`);
    paragraph = [];
  };

  const flushList = () => {
    if (!list.length) return;
    blocks.push(`<ul>${list.map((item) => `<li>${renderInlineMarkdown(item)}</li>`).join('')}</ul>`);
    list = [];
  };

  for (const line of lines) {
    const item = line.match(/^\s*[-*]\s+(.+)$/);
    if (item) {
      flushParagraph();
      list.push(item[1]);
    } else if (line.trim() === '') {
      flushParagraph();
      flushList();
    } else {
      flushList();
      paragraph.push(line);
    }
  }

  flushParagraph();
  flushList();
  return blocks.join('');
}

async function showResponse(url, options, activeButton) {
  setBusy(true, activeButton);
  result.hidden = true;
  result.classList.remove('error');

  try {
    const response = await fetch(url, options);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || 'Request failed');
    let message = payload.answer || payload.summary || '';
    if (payload.unavailable_sources?.length) {
      message += `\n\nUnavailable: ${payload.unavailable_sources.join(', ')}. Other sources were still checked.`;
    }
    result.innerHTML = renderMessage(message);
  } catch (error) {
    result.textContent = error.message || 'Sevo could not answer right now. Please try again.';
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
