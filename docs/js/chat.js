document.getElementById('send-button').addEventListener('click', sendMessage);
document.getElementById('user-input').addEventListener('keypress', function(e) {
  if (e.key === 'Enter') {
    sendMessage();
  }
});

function sendMessage() {
  const input = document.getElementById('user-input');
  const text = input.value.trim();
  if (text === '') return;

  appendMessage('user', text);
  input.value = '';

  // Simulate a response
  setTimeout(() => {
    appendMessage('assistant', 'This is a placeholder response. Later, I will be powered by an AI model.');
  }, 500);
}

function appendMessage(sender, text) {
  const chatWindow = document.getElementById('chat-window');
  const div = document.createElement('div');
  div.className = 'message ' + sender;
  div.textContent = text;
  chatWindow.appendChild(div);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}
