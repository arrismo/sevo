const form = document.querySelector('#ask-form');
const question = document.querySelector('#question');
const askButton = document.querySelector('#ask');
const catchUpButton = document.querySelector('#catch-up');
const result = document.querySelector('#result');
const systemStatus = document.querySelector('#system-status');

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

function localModelHelp(detail) {
  const message = String(detail || '');
  if (/lm studio|hermes|model|local server|tool-capable/i.test(message)) {
    return 'Local model unavailable. Start the LM Studio local server, load a tool-capable model, then try again.';
  }
  return message || 'Sevo could not answer right now. Please try again.';
}

function updateSystemStatus(payload, ok) {
  systemStatus.classList.remove('checking', 'ok', 'degraded', 'unavailable');

  if (!ok || payload.status === 'degraded') {
    systemStatus.classList.add('unavailable');
    systemStatus.querySelector('span').textContent = localModelHelp(payload.message || payload.detail);
    return;
  }

  if (payload.agent === 'ok') {
    systemStatus.classList.add('ok');
    systemStatus.querySelector('span').textContent = payload.model
      ? `Backend ready · LM Studio connected · ${payload.model}`
      : 'Backend ready · LM Studio connected';
    return;
  }

  if (payload.agent === undefined) {
    systemStatus.classList.add('degraded');
    systemStatus.querySelector('span').textContent = 'Backend ready · local model disabled';
    return;
  }

  systemStatus.classList.add('unavailable');
  systemStatus.querySelector('span').textContent = localModelHelp(payload.message);
}

async function checkHealth() {
  try {
    const response = await fetch('/health', { cache: 'no-store' });
    const payload = await response.json().catch(() => ({}));
    updateSystemStatus(payload, response.ok);
  } catch (error) {
    updateSystemStatus({ message: 'Backend unavailable. Start Sevo and try again.' }, false);
  }
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
    if (!response.ok) throw new Error(localModelHelp(payload.detail || payload.message));
    let message = payload.answer || payload.summary || '';
    if (payload.unavailable_sources?.length) {
      message += `\n\nUnavailable: ${payload.unavailable_sources.join(', ')}. Other sources were still checked.`;
    }
    result.innerHTML = renderMessage(message);
  } catch (error) {
    result.textContent = localModelHelp(error.message);
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

checkHealth();
setInterval(checkHealth, 30000);
