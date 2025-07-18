fetch('./data/publications.json')
  .then(response => response.json())
  .then(data => {
    const container = document.getElementById('publications');
    if (!container) return;

    // Sort publications by ISO date descending
    data.sort((a, b) => {
      const dateA = new Date(a.date || `${a.year}-01-01`);
      const dateB = new Date(b.date || `${b.year}-01-01`);
      return dateB - dateA;
    });

    data.forEach((pub, index) => {
      const dateStr = pub.date || `${pub.year}-01-01`;
      const displayYear = new Date(dateStr).getFullYear();
      const venueStr = [pub.venue, pub.volume && `Vol. ${pub.volume}`, pub.pages && `pp. ${pub.pages}`]
        .filter(Boolean).join(', ');
      const doiLink = pub.doi
        ? pub.doi.startsWith('http') ? pub.doi : `https://doi.org/${pub.doi}`
        : null;

      const div = document.createElement('div');
      div.className = 'publication-item';
      div.innerHTML = `
        <h3>${pub.title}</h3>
        <p><strong>Authors:</strong> ${pub.authors}</p>
        <p><strong>${capitalize(pub.type)}:</strong> ${venueStr} 
          <time datetime="${dateStr}">(${displayYear})</time>
        </p>
        ${pub.publisher ? `<p><strong>Publisher:</strong> ${pub.publisher}</p>` : ''}
        ${doiLink ? `<p><a href="${doiLink}" target="_blank">View DOI</a></p>` : ''}
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
  el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

// Capitalize helper
function capitalize(str) {
  return str ? str.charAt(0).toUpperCase() + str.slice(1) : '';
}
