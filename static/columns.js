let columnsData = null;
let editingColumnName = null;

document.addEventListener('DOMContentLoaded', loadColumns);

async function loadColumns() {
  try {
    columnsData = await fetchJSON('/api/columns');
    renderColumns();
    populateGroupFilter();
  } catch (error) {
    showToast('Failed to load columns', 'error');
  }
}

function populateGroupFilter() {
  const groups = new Set();
  
  for (const col of Object.values(columnsData || {})) {
    if (col.group) groups.add(col.group);
  }
  
  const select = document.getElementById('groupFilter');
  const sortedGroups = Array.from(groups).sort();
  
  sortedGroups.forEach(group => {
    const option = document.createElement('option');
    option.value = group;
    option.textContent = formatGroupName(group);
    select.appendChild(option);
  });
}

function formatGroupName(group) {
  return group.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function renderColumns() {
  const container = document.getElementById('columns-container');
  const searchTerm = document.getElementById('columnSearch')?.value.toLowerCase() || '';
  const groupFilter = document.getElementById('groupFilter')?.value || '';
  
  if (!columnsData || Object.keys(columnsData).length === 0) {
    container.innerHTML = '<div class="card"><p class="muted">No columns configured. Click "Add Column" to create one.</p></div>';
    return;
  }
  
  // Group columns
  const grouped = {};
  
  for (const [colName, colData] of Object.entries(columnsData)) {
    // Apply filters
    if (searchTerm) {
      const searchable = `${colName} ${colData.display_label || ''} ${colData.description || ''}`.toLowerCase();
      if (!searchable.includes(searchTerm)) continue;
    }
    
    if (groupFilter && colData.group !== groupFilter) continue;
    
    const group = colData.group || 'other';
    if (!grouped[group]) grouped[group] = [];
    grouped[group].push({ name: colName, ...colData });
  }
  
  if (Object.keys(grouped).length === 0) {
    container.innerHTML = '<div class="card"><p class="muted">No columns match your search criteria.</p></div>';
    return;
  }
  
  // Sort groups
  const sortedGroups = Object.keys(grouped).sort();
  
  let html = '';
  for (const group of sortedGroups) {
    const columns = grouped[group].sort((a, b) => a.name.localeCompare(b.name));
    
    html += `
      <div class="columns-group">
        <div class="group-header">${formatGroupName(group)}</div>
    `;
    
    for (const col of columns) {
      const alternates = col.alternate_columns || [];
      
      html += `
        <div class="column-item">
          <div class="column-info">
            <div class="column-name">
              ${escapeHtml(col.name)}
              ${col.required ? '<span class="badge required">Required</span>' : ''}
            </div>
            <div class="column-label">${escapeHtml(col.display_label || '')}</div>
            ${col.description ? `<div class="column-description">${escapeHtml(col.description)}</div>` : ''}
            ${alternates.length > 0 ? `
              <div class="column-alts">
                <strong>Alternates:</strong> ${alternates.map(a => escapeHtml(a)).join(', ')}
              </div>
            ` : ''}
          </div>
          <div class="column-actions">
            <button class="btn-secondary btn-small" onclick="editColumn('${escapeHtml(col.name)}')">Edit</button>
            <button class="btn-danger btn-small" onclick="deleteColumn('${escapeHtml(col.name)}')">Delete</button>
          </div>
        </div>
      `;
    }
    
    html += '</div>';
  }
  
  container.innerHTML = html;
}

function filterColumns() {
  renderColumns();
}

function openColumnModal(columnName = null) {
  editingColumnName = columnName;
  const modal = document.getElementById('columnModal');
  const form = document.getElementById('columnForm');
  const title = document.getElementById('columnModalTitle');
  
  form.reset();
  
  if (columnName && columnsData?.[columnName]) {
    const col = columnsData[columnName];
    title.textContent = 'Edit Column';
    document.getElementById('originalColumnName').value = columnName;
    document.getElementById('columnName').value = columnName;
    document.getElementById('displayLabel').value = col.display_label || '';
    document.getElementById('columnDescription').value = col.description || '';
    document.getElementById('columnGroup').value = col.group || 'input-fields';
    document.getElementById('dataType').value = col.data_type || 'string';
    document.getElementById('columnRequired').checked = col.required || false;
    document.getElementById('alternateColumns').value = (col.alternate_columns || []).join('\n');
  } else {
    title.textContent = 'Add Column';
    document.getElementById('originalColumnName').value = '';
  }
  
  modal.hidden = false;
}

function closeColumnModal() {
  document.getElementById('columnModal').hidden = true;
  editingColumnName = null;
}

async function saveColumn(event) {
  event.preventDefault();
  
  const originalName = document.getElementById('originalColumnName').value;
  const columnName = document.getElementById('columnName').value.trim().toUpperCase();
  
  if (!columnName) {
    showToast('Column name is required', 'error');
    return;
  }
  
  // Parse alternate columns
  const alternatesText = document.getElementById('alternateColumns').value;
  const alternates = alternatesText
    .split('\n')
    .map(s => s.trim().toUpperCase())
    .filter(s => s.length > 0);
  
  const columnData = {
    display_label: document.getElementById('displayLabel').value.trim(),
    description: document.getElementById('columnDescription').value.trim(),
    group: document.getElementById('columnGroup').value,
    data_type: document.getElementById('dataType').value,
    required: document.getElementById('columnRequired').checked,
    alternate_columns: alternates
  };
  
  try {
    // If renaming, delete old column first
    if (originalName && originalName !== columnName) {
      await deleteJSON(`/api/columns/${originalName}`);
    }
    
    const result = await putJSON(`/api/columns/${columnName}`, columnData);
    
    if (result.ok) {
      showToast('Column saved successfully', 'success');
      closeColumnModal();
      loadColumns();
    } else {
      showToast(result.error || 'Failed to save column', 'error');
    }
  } catch (error) {
    showToast('Failed to save column', 'error');
  }
}

function editColumn(columnName) {
  openColumnModal(columnName);
}

async function deleteColumn(columnName) {
  if (!confirm(`Are you sure you want to delete column "${columnName}"?`)) return;
  
  try {
    const result = await deleteJSON(`/api/columns/${columnName}`);
    
    if (result.ok) {
      showToast('Column deleted', 'success');
      loadColumns();
    } else {
      showToast(result.error || 'Failed to delete column', 'error');
    }
  } catch (error) {
    showToast('Failed to delete column', 'error');
  }
}

