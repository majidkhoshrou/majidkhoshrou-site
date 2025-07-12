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

  fetch('http://127.0.0.1:5000/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: text })
  })
  .then(response => response.json())
  .then(data => {
    appendMessage('assistant', data.reply);
  })
  .catch(error => {
    console.error('Error:', error);
    appendMessage('assistant', 'Sorry, there was an error processing your request.');
  });
}

function appendMessage(sender, text) {
  const chatWindow = document.getElementById('chat-window');
  const div = document.createElement('div');
  div.className = 'message ' + sender;
  div.textContent = text;
  chatWindow.appendChild(div);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}
