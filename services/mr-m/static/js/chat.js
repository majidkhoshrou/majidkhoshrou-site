// === Turnstile helpers =====================================================
const TRUST_HINT_KEY = "mrM_trusted_until";
const TRUST_HINT_MS  = 2 * 60 * 60 * 1000; // 2 hours

function isClientTrusted() {
  const until = Number(localStorage.getItem(TRUST_HINT_KEY) || 0);
  return Date.now() < until;
}
function markClientTrusted() {
  localStorage.setItem(TRUST_HINT_KEY, String(Date.now() + TRUST_HINT_MS));
}

function waitForTurnstile(maxWaitMs = 10000, checkEveryMs = 50) {
  return new Promise((resolve) => {
    const start = Date.now();
    const check = () => {
      if (window.turnstile) return resolve(true);
      if (Date.now() - start >= maxWaitMs) return resolve(false);
      setTimeout(check, checkEveryMs);
    };
    check();
  });
}

let turnstileWidgetId = null;
async function ensureTurnstileRendered() {
  // Wait briefly for the script to load if it's async/defer
  const available = await waitForTurnstile();
  if (!window.TURNSTILE_SITE_KEY || !available) return null;
  if (turnstileWidgetId) return turnstileWidgetId;

  let el = document.getElementById('cf-turnstile');
  if (!el) {
    el = document.createElement('div');
    el.id = 'cf-turnstile';
    el.style.display = 'none';
    document.body.appendChild(el);
  }
  turnstileWidgetId = turnstile.render(el, {
    sitekey: window.TURNSTILE_SITE_KEY,
    size: "invisible",
    action: window.TURNSTILE_ACTION || "chat",
    callback: () => {}
  });
  return turnstileWidgetId;
}

async function getTurnstileTokenIfNeeded(force = false) {
  if (!force && isClientTrusted()) return null;
  if (!window.TURNSTILE_SITE_KEY) return null;

  const widgetId = await ensureTurnstileRendered();
  if (!widgetId) return null;

  // 1) Try the current response first
  try {
    let token = turnstile.getResponse(widgetId);
    if (typeof token === 'string' && token.length > 0) return token;

    // 2) Try executing (may return previous token)
    token = await turnstile.execute(widgetId, {
      action: window.TURNSTILE_ACTION || "chat"
    });
    if (typeof token === 'string' && token.length > 0) return token;

    // 3) If we still don't have a token, reset then execute once more
    try { turnstile.reset(widgetId); } catch {}
    token = await turnstile.execute(widgetId, {
      action: window.TURNSTILE_ACTION || "chat"
    });
    if (typeof token === 'string' && token.length > 0) return token;

    return null;
  } catch (e) {
    console.warn("Turnstile token fetch failed:", e);
    return null;
  }
}


// === Original bindings ======================================================

document.getElementById('send-button').addEventListener('click', sendMessage);
document.getElementById('user-input').addEventListener('keypress', function (e) {
  if (e.key === 'Enter') sendMessage();
});

function updateQuotaBanner() {
  fetch('/api/quota')
    .then(res => res.json())
    .then(data => {
      const banner = document.getElementById('quota-banner');
      banner.innerHTML = `📊 You have ${data.remaining} of ${data.limit} messages left today.`;

      banner.className = 'quota-banner'; // reset
      if (data.remaining === 0) {
        banner.classList.add('quota-red');
      } else if (data.remaining <= 2) {
        banner.classList.add('quota-orange');
      } else {
        banner.classList.add('quota-green');
      }
    })
    .catch(err => {
      console.warn("Failed to update quota banner:", err);
    });
}

async function sendMessage() {
  const input = document.getElementById('user-input');
  const text = input.value.trim();
  if (text === '') return;

  appendMessage('user', text);
  saveMessage('user', text);

  input.value = '';
  input.focus();

  const typingEl = appendMessage('assistant', 'Mr M is typing...', true);
  typingEl.classList.add('typing');

  const chat = JSON.parse(sessionStorage.getItem('chatHistory') || '[]');

  // Convert stored chat to OpenAI-compatible format
  const history = chat.map(msg => ({
    role: msg.sender === 'user' ? 'user' : 'assistant',
    content: msg.text
  }));

  // === CHANGED: always fetch a token when a site key exists, then attach it ===
  const actionName = (window.TURNSTILE_ACTION || 'chat');

  let challenge_token = null;
  if (window.TURNSTILE_SITE_KEY) {
    challenge_token = await getTurnstileTokenIfNeeded(true); // force in prod
    if (!challenge_token) {
      typingEl.remove();
      appendMessage('assistant', "Still preparing the verification challenge—please try sending again in a moment.");
      return;
    }
  }

  const body = { message: text, history, action: actionName };
  if (challenge_token) {
    body.recaptcha_token = challenge_token;          // legacy name
    body.recaptcha_action = actionName;              // legacy name
    body["cf-turnstile-response"] = challenge_token; // canonical name
  }
  // === END CHANGE ===

  console.debug("[turnstile] initial token length:", challenge_token ? challenge_token.length : 0);

  let attemptedRetry = false;

  const doRequest = () => fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });

  try {
    let response = await doRequest();
    let data = {};
    try { data = await response.json(); } catch (err) { console.error("Failed to parse JSON:", err); }

    if (response.status === 403 && !attemptedRetry) {
      attemptedRetry = true;
      // Force a fresh token and retry once
      challenge_token = await getTurnstileTokenIfNeeded(true);
      if (challenge_token) {
        body.recaptcha_token = challenge_token;
        body["cf-turnstile-response"] = challenge_token;
      }
      response = await doRequest();
      try { data = await response.json(); } catch {}
    }

    setTimeout(() => {
      typingEl.remove();

      let message;
      if (response.status === 429) {
        message = data?.reply || data?.error || "Rate limit reached.";
      } else if (!response.ok && data.error) {
        message = data.info?.error
          ? `Verification failed: ${data.info.error}`
          : data.error;
      } else if (data.reply) {
        message = data.reply;
      } else if (data.ok && data.message) {
        message = data.message;
      } else {
        message = "Sorry, something went wrong.";
      }

      if (typeof message !== 'string') {
        console.warn("⚠️ Invalid message from server:", message);
        message = "[Sorry, something went wrong.]";
      }

      const role = (response.status === 429 || response.status === 403 || data.error) ? 'system' : 'assistant';
      appendMessage(role, message);

      // Only disable input on DAILY cap, not on BURST
      if (response.status === 429) {
        if (data?.code === 'daily') {
          document.getElementById('user-input').disabled = true;
          document.getElementById('send-button').disabled = true;
        }
      }

      if (response.ok) {
        markClientTrusted(); // harmless hint; server still verifies
      }

      updateQuotaBanner();

      if (role === 'assistant') {
        saveMessage('assistant', message);
      }
    }, 700);

  } catch (error) {
    console.error('Error:', error);
    typingEl.remove();
    const errorMsg = 'Sorry, there was an error processing your request.';
    appendMessage('assistant', errorMsg);
    saveMessage('assistant', errorMsg);
  }
}

// === rendering / storage (unchanged) =======================================

function appendMessage(sender, text, isTyping = false) {
  const chatWindow = document.getElementById('chat-window');
  const div = document.createElement('div');

  if (sender === 'system') {
    div.className = 'message system';
  } else {
    div.className = `message ${sender}`;
  }

  if (isTyping) {
    div.innerHTML = text;
  } else {
    if (typeof text !== 'string') {
      console.warn("⚠️ appendMessage received invalid text:", text);
      text = '[Message not available]';
    }
    div.innerHTML = sanitizeHTML(text);
  }

  chatWindow.appendChild(div);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return div;
}

function sanitizeHTML(str) {
  if (typeof str !== 'string') return '[Message not available]';
  return str
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\n/g, "<br>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
}

function saveMessage(sender, text) {
  const chat = JSON.parse(sessionStorage.getItem('chatHistory') || '[]');
  chat.push({ sender, text });
  sessionStorage.setItem('chatHistory', JSON.stringify(chat));
}

function loadChatHistory() {
  const chat = JSON.parse(sessionStorage.getItem('chatHistory') || '[]');
  chat.forEach(msg => {
    appendMessage(msg.sender, msg.text);
  });
}

// === Context tip helpers =====================================================
const CONTEXT_TIP_KEY = "mrM_context_tip_dismissed"; // used if you add a dismiss button

function hideContextTipIfDismissed() {
  const tip = document.getElementById("context-tip");
  if (!tip) return;
  if (localStorage.getItem(CONTEXT_TIP_KEY) === "1") {
    try { tip.remove(); } catch {}
  }
}

function bindContextTip() {
  const tip = document.getElementById("context-tip");
  if (!tip) return;

  // Inline "Start new chat" button inside the intro block
  const newChatBtn = document.getElementById("new-chat-btn");
  newChatBtn?.addEventListener("click", async () => {
    // Optional: clear server-side history if you implement it
    try { await fetch("/api/clear-chat", { method: "POST" }); } catch {}
    // Clear client-side session history just to be explicit
    sessionStorage.removeItem("chatHistory");
    location.reload();
  });

  // Optional dismiss (only if you add a button with this id)
  const dismissBtn = document.getElementById("dismiss-tip-btn");
  dismissBtn?.addEventListener("click", () => {
    localStorage.setItem(CONTEXT_TIP_KEY, "1");
    try { tip.remove(); } catch {}
  });
}


window.onload = () => {
  sessionStorage.removeItem('chatHistory');
  // Pre-render Turnstile early so the first message has a token
  if (window.TURNSTILE_SITE_KEY) {
    try { ensureTurnstileRendered(); } catch {}
  }
  loadChatHistory();
  document.getElementById('user-input').focus();
  updateQuotaBanner();

    // NEW: context tip behaviors
  hideContextTipIfDismissed();   // hides it if user dismissed previously
  bindContextTip();              // wires up "new chat" (and optional dismiss)
};
