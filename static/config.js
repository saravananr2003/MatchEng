let configData = null;
let editingColumnKey = null;

const statusEl = document.getElementById('status');
const columnsContainer = document.getElementById('columnsContainer');
const addColumnBtn = document.getElementById('addColumnBtn');
const columnModal = document.getElementById('columnModal');
const columnForm = document.getElementById('columnForm');
const closeModal = document.getElementById('closeModal');
const cancelBtn = document.getElementById('cancelBtn');
const modalTitle = document.getElementById('modalTitle');

function setStatus(msg, kind = 'info') {
  statusEl.hidden = false;
  statusEl.className = `status ${kind}`;
  statusEl.textContent = msg;
  setTimeout(() => {
    if (kind === 'success') {
      statusEl.hidden = true;
    }
  }, 3000);
}

function clearStatus() {
  statusEl.hidden = true;
  statusEl.textContent = '';
}

async function loadConfig() {
  try {
    const response = await fetch('/api/config');
    if (!response.ok) {
      throw new Error('Failed to load configuration');
    }
    configData = await response.json();
    renderColumns();
  } catch (error) {
    setStatus(`Error loading configuration: ${error.message}`, 'error');
    columnsContainer.innerHTML = `<div class="loading">Error loading columns. Please refresh the page.</div>`;
  }
}

function renderColumns() {
  if (!configData || !configData.input_columns) {
    columnsContainer.innerHTML = '<div class="loading">No columns configured</div>';
    return;
  }

  const columns = configData.input_columns;
  
  // Group columns by field_type
  const grouped = {};
  for (const [key, col] of Object.entries(columns)) {
    const fieldType = col.field_type || 'Other';
    if (!grouped[fieldType]) {
      grouped[fieldType] = [];
    }
    grouped[fieldType].push({ key, ...col });
  }

  // Sort groups and columns
  const sortedGroups = Object.keys(grouped).sort();
  for (const group of sortedGroups) {
    grouped[group].sort((a, b) => a.label.localeCompare(b.label));
  }

  let html = '';
  for (const fieldType of sortedGroups) {
    html += `<div class="columns-group">
      <div class="group-header">${fieldType}</div>`;
    
    for (const col of grouped[fieldType]) {
      const isActive = col.active !== false;
      const isRequired = col.required === true;
      
      html += `<div class="column-item ${!isActive ? 'inactive' : ''}">
        <div class="column-info">
          <div class="column-header">
            <span class="column-label">${escapeHtml(col.label || col.key)}</span>
            <div class="column-badges">
              ${isRequired ? '<span class="badge required">Required</span>' : '<span class="badge optional">Optional</span>'}
              ${isActive ? '<span class="badge active">Active</span>' : '<span class="badge inactive">Inactive</span>'}
            </div>
          </div>
          ${col.description ? `<div class="column-description">${escapeHtml(col.description)}</div>` : ''}
          <div class="column-details">
            <div class="column-detail-item">
              <strong>Type:</strong> <span>${escapeHtml(col.type || 'string')}</span>
            </div>
            <div class="column-detail-item">
              <strong>Key:</strong> <span>${escapeHtml(col.key)}</span>
            </div>
          </div>
          ${col.alternate_names && col.alternate_names.length > 0 ? `
            <div class="alternate-names">
              <strong>Alternate names:</strong> ${col.alternate_names.map(n => escapeHtml(n)).join(', ')}
            </div>
          ` : ''}
        </div>
        <div class="column-actions">
          <button class="btn-secondary btn-small" onclick="editColumn('${col.key}')">Edit</button>
          <button class="btn-danger btn-small" onclick="toggleColumnActive('${col.key}')">
            ${isActive ? 'Deactivate' : 'Activate'}
          </button>
        </div>
      </div>`;
    }
    
    html += '</div>';
  }

  columnsContainer.innerHTML = html || '<div class="loading">No columns configured</div>';
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function openModal(isEdit = false, columnKey = null) {
  editingColumnKey = columnKey;
  modalTitle.textContent = isEdit ? 'Edit Column' : 'Add Column';
  columnForm.reset();
  document.getElementById('columnKey').value = columnKey || '';
  document.getElementById('columnActive').checked = true;
  
  if (isEdit && columnKey && configData.input_columns[columnKey]) {
    const col = configData.input_columns[columnKey];
    document.getElementById('columnLabel').value = col.label || '';
    document.getElementById('fieldType').value = col.field_type || 'Base Fields';
    document.getElementById('columnDescription').value = col.description || '';
    document.getElementById('columnType').value = col.type || 'string';
    document.getElementById('columnRequired').checked = col.required === true;
    document.getElementById('columnActive').checked = col.active !== false;
    document.getElementById('alternateNames').value = (col.alternate_names || []).join('\n');
  }
  
  columnModal.hidden = false;
}

function closeModalDialog() {
  columnModal.hidden = true;
  editingColumnKey = null;
  columnForm.reset();
}

function editColumn(columnKey) {
  openModal(true, columnKey);
}

async function toggleColumnActive(columnKey) {
  if (!configData.input_columns[columnKey]) return;
  
  const currentActive = configData.input_columns[columnKey].active !== false;
  configData.input_columns[columnKey].active = !currentActive;
  
  await saveConfig();
}

async function saveConfig() {
  try {
    setStatus('Saving configuration...', 'info');
    
    const response = await fetch('/api/config', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(configData),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to save configuration');
    }

    setStatus('Configuration saved successfully!', 'success');
    await loadConfig();
  } catch (error) {
    setStatus(`Error saving configuration: ${error.message}`, 'error');
    // Reload to get latest state
    await loadConfig();
  }
}

// Generate a unique column key from label
function generateColumnKey(label) {
  return label.toUpperCase()
    .replace(/[^A-Z0-9]/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_|_$/g, '');
}

columnForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const formData = new FormData(columnForm);
  const columnKey = formData.get('columnKey') || generateColumnKey(formData.get('label'));
  const label = formData.get('label').trim();
  
  if (!label) {
    setStatus('Column label is required', 'error');
    return;
  }

  // Parse alternate names
  const alternateNamesText = formData.get('alternate_names') || '';
  const alternateNames = alternateNamesText
    .split('\n')
    .map(n => n.trim())
    .filter(n => n.length > 0);

  const columnData = {
    field_type: formData.get('field_type'),
    label: label,
    description: formData.get('description').trim(),
    type: formData.get('type'),
    required: formData.get('required') === 'on',
    active: formData.get('active') === 'on',
    alternate_names: alternateNames,
  };

  // Initialize input_columns if it doesn't exist
  if (!configData.input_columns) {
    configData.input_columns = {};
  }

  // If editing, preserve the original key; if adding, use generated key
  const finalKey = editingColumnKey || columnKey;
  
  // If key changed and it's an edit, we need to remove old key
  if (editingColumnKey && editingColumnKey !== finalKey) {
    delete configData.input_columns[editingColumnKey];
  }

  configData.input_columns[finalKey] = columnData;

  await saveConfig();
  closeModalDialog();
});

addColumnBtn.addEventListener('click', () => {
  openModal(false);
});

closeModal.addEventListener('click', closeModalDialog);
cancelBtn.addEventListener('click', closeModalDialog);

// Close modal on outside click
columnModal.addEventListener('click', (e) => {
  if (e.target === columnModal) {
    closeModalDialog();
  }
});

// Initialize
loadConfig();

