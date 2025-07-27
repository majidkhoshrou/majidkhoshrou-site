document.getElementById('send-button').addEventListener('click', sendMessage);
document.getElementById('user-input').addEventListener('keypress', function (e) {
  if (e.key === 'Enter') sendMessage();
});

function sendMessage() {
  const input = document.getElementById('user-input');
  const text = input.value.trim();
  if (text === '') return;

  appendMessage('user', text);
  saveMessage('user', text);

  input.value = '';
  input.focus();

  const typingEl = appendMessage('assistant', 'Mr. <i>M</i> is typing...', true);
  typingEl.classList.add('typing');

  fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: text })
  })
    .then(response => response.json())
    .then(data => {
      setTimeout(() => {
        typingEl.remove();
        appendMessage('assistant', data.reply);
        saveMessage('assistant', data.reply);
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
  div.className = `message ${sender}`;
  if (isTyping) {
    div.innerHTML = text;
  } else {
    div.innerHTML = sanitizeHTML(text);
  }
  chatWindow.appendChild(div);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return div;
}

function sanitizeHTML(str) {
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
  loadChatHistory();
  document.getElementById('user-input').focus();
};
