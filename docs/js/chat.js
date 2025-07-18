document.getElementById('send-button').addEventListener('click', sendMessage);
document.getElementById('user-input').addEventListener('keypress', function (e) {
  if (e.key === 'Enter') sendMessage();
});

function sendMessage() {
  const input = document.getElementById('user-input');
  const text = input.value.trim();
  if (text === '') return;

  appendMessage('user', text);
  input.value = '';
  input.focus();

  // Show typing placeholder (with animation class)
  const typingEl = appendMessage('assistant', 'Mr. M is typing...', true);
  typingEl.classList.add('typing');

  fetch('http://127.0.0.1:5000/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: text })
  })
    .then(response => response.json())
    .then(data => {
      // Simulate typing delay
      setTimeout(() => {
        typingEl.remove();
        appendMessage('assistant', data.reply);
      }, 700);
    })
    .catch(error => {
      console.error('Error:', error);
      typingEl.remove();
      appendMessage('assistant', 'Sorry, there was an error processing your request.');
    });
}

function appendMessage(sender, text, isTyping = false) {
  const chatWindow = document.getElementById('chat-window');
  const div = document.createElement('div');
  div.className = `message ${sender}`;
  if (isTyping) {
    div.textContent = text;
  } else {
    div.innerHTML = sanitizeHTML(text); // Supports bold, links, etc.
  }

  chatWindow.appendChild(div);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return div;
}

function sanitizeHTML(str) {
  // Basic sanitization: supports <strong>, <em>, <br>, <a href="">
  return str
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\n/g, "<br>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank">$1</a>');
}

window.onload = () => {
  document.getElementById('user-input').focus();
};
