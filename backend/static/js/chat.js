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

      // Apply color styles
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

function sendMessage() {
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

  fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: text, history })  // 👈 include history
  })
    
  .then(async (response) => {
    let data = {};
    try {
      data = await response.json();
    } catch (err) {
      console.error("Failed to parse JSON:", err);
    }

    setTimeout(() => {
      typingEl.remove();

      let message;

      if (response.status === 429) {
        message = data?.reply || data?.error || "You've hit your daily limit. Try again tomorrow.";
      } else if (!response.ok && data.error) {
        message = data.error;
      } else if (data.reply) {
        message = data.reply;
      } else {
        message = "Sorry, something went wrong.";
      }

      // ✅ SAFEGUARD to prevent undefined errors
      if (typeof message !== 'string') {
        console.warn("⚠️ Invalid message from server:", message);
        message = "[Sorry, something went wrong.]";
      }

      // ✅ Decide role: system (for errors) or assistant (for normal response)
      const role = (response.status === 429 || data.error) ? 'system' : 'assistant';

      appendMessage(role, message);

      // ✅ Update quota banner after message is sent
      updateQuotaBanner();

      // ✅ Disable input if rate limit is hit
      if (response.status === 429) {
        document.getElementById('user-input').disabled = true;
        document.getElementById('send-button').disabled = true;
      }

      // ✅ Only save normal assistant replies to chat history
      if (role === 'assistant') {
        saveMessage('assistant', message);
      }
    }, 700);

  })


    .catch(error => {
      console.error('Error:', error);
      typingEl.remove();
      const errorMsg = 'Sorry, there was an error processing your request.';
      appendMessage('assistant', errorMsg);
      saveMessage('assistant', errorMsg);
    });
}




function appendMessage(sender, text, isTyping = false) {
  const chatWindow = document.getElementById('chat-window');
  const div = document.createElement('div');

  // Add custom class for 'system' messages (like rate limits or errors)
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
    .replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank">$1</a>');
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

window.onload = () => {
  sessionStorage.removeItem('chatHistory');  // 👈 Clear chat on refresh
  loadChatHistory();  // Will now load empty history
  document.getElementById('user-input').focus();

  updateQuotaBanner();  // ✅ Fetch and show quota with correct color
};


