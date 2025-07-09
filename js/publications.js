fetch('./data/publications.json')
  .then(response => response.json())
  .then(data => {
    const container = document.getElementById('publications');
    if (!container) return;

    // Sort by year descending
    data.sort((a, b) => (b.year || 0) - (a.year || 0));

    data.forEach((pub, index) => {
      const div = document.createElement('div');
      div.className = 'publication-item';
      div.innerHTML = `
        <h3>${pub.title}</h3>
        <p><strong>Authors:</strong> ${pub.authors}</p>
        <p><strong>Journal:</strong> ${pub.journal || ''}${pub.volume ? `, Vol. ${pub.volume}` : ''}${pub.pages ? `, pp. ${pub.pages}` : ''} (${pub.year})</p>
        <p><strong>Publisher:</strong> ${pub.publisher || ''}</p>
        ${pub.doi ? `<p><a href="https://doi.org/${pub.doi}" target="_blank">View DOI</a></p>` : ''}
        <div class="abstract-actions">
            <button onclick="toggleAbstract(${index})">Read Abstract</button>
            <a href="chat.html?query=${encodeURIComponent('Show me the abstract of ' + pub.title)}" class="chat-link">
                💬 Ask AI Assistant
            </a>
        </div>

        <div id="abstract-${index}" class="abstract-text" style="display:none;">
          <p><strong>Abstract:</strong> ${pub.abstract || 'No abstract available.'}</p>
        </div>
      `;
      container.appendChild(div);
    });
  })
  .catch(error => {
    console.error('Error loading publications:', error);
  });

// Toggle function
function toggleAbstract(index) {
  const el = document.getElementById(`abstract-${index}`);
  if (el.style.display === 'none') {
    el.style.display = 'block';
  } else {
    el.style.display = 'none';
  }
}
