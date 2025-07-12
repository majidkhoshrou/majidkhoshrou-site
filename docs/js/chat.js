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
  input.focus();

  // Show typing indicator
  appendMessage('assistant', 'Assistant is typing...');

  fetch('http://127.0.0.1:5000/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: text })
  })
  .then(response => response.json())
  .then(data => {
    // Remove the typing indicator
    const chatWindow = document.getElementById('chat-window');
    const lastMessage = chatWindow.querySelector('.message.assistant:last-child');
    if (lastMessage && lastMessage.textContent === 'Assistant is typing...') {
      lastMessage.remove();
    }
    appendMessage('assistant', data.reply);
  })
  .catch(error => {
    console.error('Error:', error);
    const chatWindow = document.getElementById('chat-window');
    const lastMessage = chatWindow.querySelector('.message.assistant:last-child');
    if (lastMessage && lastMessage.textContent === 'Assistant is typing...') {
      lastMessage.remove();
    }
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

window.onload = function() {
  document.getElementById('user-input').focus();
};
