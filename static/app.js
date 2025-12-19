// Global utilities

// Theme management
function setTheme(theme) {
  localStorage.setItem('theme', theme);
  document.documentElement.setAttribute('data-theme', theme);
  const switcher = document.getElementById('themeSwitcher');
  if (switcher) switcher.value = theme;
}

function initTheme() {
  const saved = localStorage.getItem('theme') || 'auto';
  const switcher = document.getElementById('themeSwitcher');
  if (switcher) switcher.value = saved;
}

document.addEventListener('DOMContentLoaded', initTheme);

function showToast(message, type = 'info') {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.className = `toast ${type}`;
  toast.hidden = false;
  
  setTimeout(() => {
    toast.hidden = true;
  }, 3000);
}

function setStatus(elementId, message, type = 'info') {
  const el = document.getElementById(elementId);
  if (el) {
    el.textContent = message;
    el.className = `status ${type}`;
    el.hidden = false;
  }
}

function clearStatus(elementId) {
  const el = document.getElementById(elementId);
  if (el) {
    el.hidden = true;
  }
}

async function fetchJSON(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers
    },
    ...options
  });
  return response.json();
}

async function postJSON(url, data) {
  return fetchJSON(url, {
    method: 'POST',
    body: JSON.stringify(data)
  });
}

async function putJSON(url, data) {
  return fetchJSON(url, {
    method: 'PUT',
    body: JSON.stringify(data)
  });
}

async function patchJSON(url, data = {}) {
  return fetchJSON(url, {
    method: 'PATCH',
    body: JSON.stringify(data)
  });
}

async function deleteJSON(url) {
  return fetchJSON(url, {
    method: 'DELETE'
  });
}

// Tab switching
document.addEventListener('DOMContentLoaded', () => {
  const tabBtns = document.querySelectorAll('.tab-btn');
  
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const tabId = btn.dataset.tab;
      
      // Update buttons
      tabBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      
      // Update content
      document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
      });
      document.getElementById(`${tabId}-tab`)?.classList.add('active');
    });
  });
});

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text || '';
  return div.innerHTML;
}

