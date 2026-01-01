/**
 * MatchEng UI Components - Reusable UI component functions
 */

/**
 * Show a toast notification
 * @param {string} message - Message to display
 * @param {string} type - Type: 'success', 'error', 'info', 'warning'
 * @param {number} duration - Duration in milliseconds (default: 3000)
 */
function showToast(message, type = 'info', duration = 3000) {
  const toast = document.getElementById('toast');
  if (!toast) return;
  
  toast.textContent = message;
  toast.className = `toast toast-${type}`;
  toast.hidden = false;
  
  setTimeout(() => {
    toast.hidden = true;
  }, duration);
}

/**
 * Set status message
 * @param {string} elementId - ID of status element
 * @param {string} message - Status message
 * @param {string} type - Type: 'success', 'error', 'info', 'warning'
 */
function setStatus(elementId, message, type = 'info') {
  const element = document.getElementById(elementId);
  if (!element) return;
  
  element.textContent = message;
  element.className = `status ${type}`;
  element.hidden = false;
}

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
  if (text == null) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Format number with locale
 * @param {number} num - Number to format
 * @returns {string} Formatted number
 */
function formatNumber(num) {
  if (num == null) return '0';
  return Number(num).toLocaleString();
}

/**
 * Format date
 * @param {string|Date} date - Date to format
 * @returns {string} Formatted date
 */
function formatDate(date) {
  if (!date) return '';
  const d = new Date(date);
  return d.toLocaleDateString();
}

/**
 * Format date and time
 * @param {string|Date} date - Date to format
 * @returns {string} Formatted date and time
 */
function formatDateTime(date) {
  if (!date) return '';
  const d = new Date(date);
  return d.toLocaleString();
}

/**
 * Create a standardized card element
 * @param {string} title - Card title
 * @param {string} content - Card content HTML
 * @param {Object} options - Options: {id, className, actions}
 * @returns {string} Card HTML
 */
function createCard(title, content, options = {}) {
  const id = options.id ? ` id="${escapeHtml(options.id)}"` : '';
  const className = options.className ? ` ${options.className}` : '';
  const actions = options.actions ? `<div class="card-actions">${options.actions}</div>` : '';
  
  return `
    <div class="card${className}"${id}>
      <h2>${escapeHtml(title)}</h2>
      ${content}
      ${actions}
    </div>
  `;
}

/**
 * Create a standardized stat card
 * @param {string} label - Stat label
 * @param {string|number} value - Stat value
 * @param {string} subtitle - Optional subtitle
 * @returns {string} Stat card HTML
 */
function createStatCard(label, value, subtitle = '') {
  return `
    <div class="stat-card">
      <h3>${escapeHtml(label)}</h3>
      <div class="stat-value">${escapeHtml(String(value))}</div>
      ${subtitle ? `<div class="stat-subtitle">${escapeHtml(subtitle)}</div>` : ''}
    </div>
  `;
}

/**
 * Create a progress bar
 * @param {number} percent - Progress percentage (0-100)
 * @param {string} text - Optional progress text
 * @returns {string} Progress bar HTML
 */
function createProgressBar(percent, text = '') {
  return `
    <div class="progress-bar">
      <div class="progress-fill" style="width: ${Math.min(100, Math.max(0, percent))}%"></div>
    </div>
    ${text ? `<p class="muted" style="margin-top: 0.5rem;">${escapeHtml(text)}</p>` : ''}
  `;
}

/**
 * Create an action card with CTA button
 * @param {string} title - Card title
 * @param {string} description - Card description
 * @param {string} buttonText - Button text
 * @param {string} buttonOnClick - Button onclick handler
 * @param {string} buttonClass - Button class (default: 'btn-primary btn-large')
 * @returns {string} Action card HTML
 */
function createActionCard(title, description, buttonText, buttonOnClick, buttonClass = 'btn-primary btn-large') {
  return `
    <div class="card action-card">
      <div class="action-card-content">
        <div>
          <h3>${escapeHtml(title)}</h3>
          <p class="muted">${escapeHtml(description)}</p>
        </div>
        <div class="action-card-actions">
          <button class="${buttonClass}" onclick="${buttonOnClick}">
            ${escapeHtml(buttonText)}
          </button>
        </div>
      </div>
    </div>
  `;
}

/**
 * Debounce function
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * Format file size
 * @param {number} bytes - File size in bytes
 * @returns {string} Formatted file size
 */
function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Get quality class based on score
 * @param {number} score - Quality score (0-100)
 * @returns {string} Quality class: 'high', 'medium', 'low'
 */
function getQualityClass(score) {
  if (score >= 80) return 'high';
  if (score >= 50) return 'medium';
  return 'low';
}

// Export functions for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    showToast,
    setStatus,
    escapeHtml,
    formatNumber,
    formatDate,
    formatDateTime,
    createCard,
    createStatCard,
    createProgressBar,
    createActionCard,
    debounce,
    formatFileSize,
    getQualityClass
  };
}

