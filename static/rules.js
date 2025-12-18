let rulesData = null;
let editingRuleId = null;

const AVAILABLE_FIELDS = [
  'COMPANY_NAME', 'ADDRESS_LINE_1', 'ADDRESS_LINE_2', 'CITY', 'STATE', 
  'ZIP_CODE', 'ZIP_SUPP', 'PHONE_NUMBER', 'EMAIL_ADDRESS', 'COUNTRY_CODE'
];

document.addEventListener('DOMContentLoaded', loadRules);

async function loadRules() {
  const container = document.getElementById('rules-container');
  container.innerHTML = '<div class="loading">Loading rules...</div>';
  
  try {
    const response = await fetch('/api/rules');
    if (!response.ok) throw new Error('Failed to fetch rules');
    rulesData = await response.json();
    renderRules();
  } catch (error) {
    console.error('Error loading rules:', error);
    container.innerHTML = '<p class="muted">Failed to load rules. Please refresh the page.</p>';
    showToast('Failed to load rules', 'error');
  }
}

function renderRules() {
  const container = document.getElementById('rules-container');
  const rules = rulesData?.rules || {};
  
  if (Object.keys(rules).length === 0) {
    container.innerHTML = '<div class="card"><p class="muted" style="padding: 20px;">No rules configured. Click "+ Add Rule" to create one.</p></div>';
    return;
  }
  
  // Sort by priority
  const sortedRules = Object.entries(rules).sort((a, b) => (a[1].priority || 999) - (b[1].priority || 999));
  
  let html = '';
  for (const [ruleId, rule] of sortedRules) {
    const isEnabled = rule.enabled !== false;
    
    html += `
      <div class="rule-item ${!isEnabled ? 'disabled' : ''}" data-rule-id="${ruleId}">
        <div class="rule-header">
          <div class="rule-title">
            <h3>${escapeHtmlLocal(rule.name || ruleId)}</h3>
            <span class="badge ${isEnabled ? 'enabled' : 'disabled'}">${isEnabled ? 'Enabled' : 'Disabled'}</span>
          </div>
          <div class="rule-actions">
            <button type="button" class="btn-secondary btn-small" onclick="toggleRule('${ruleId}')">${isEnabled ? 'Disable' : 'Enable'}</button>
            <button type="button" class="btn-primary btn-small" onclick="editRule('${ruleId}')">Edit</button>
            <button type="button" class="btn-danger btn-small" onclick="deleteRule('${ruleId}')">Delete</button>
          </div>
        </div>
        
        <div class="rule-meta">
          <span><strong>ID:</strong> ${escapeHtmlLocal(ruleId)}</span>
          <span><strong>Priority:</strong> ${rule.priority || 'N/A'}</span>
          <span><strong>Match Reason:</strong> ${escapeHtmlLocal(rule.match_reason || 'N/A')}</span>
        </div>
        
        ${rule.description ? `<p style="margin-bottom: 12px; color: var(--text-secondary); font-size: 13px;">${escapeHtmlLocal(rule.description)}</p>` : ''}
        
        <div class="rule-conditions">
          <strong style="display: block; margin-bottom: 8px;">Conditions:</strong>
          ${renderConditionsSummary(rule.conditions || [])}
        </div>
      </div>
    `;
  }
  
  container.innerHTML = html;
}

function escapeHtmlLocal(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = String(text);
  return div.innerHTML;
}

function renderConditionsSummary(conditions) {
  if (!conditions || !conditions.length) return '<p class="muted">No conditions defined</p>';
  
  let html = '';
  for (const cond of conditions) {
    const field = cond.field || 'Unknown';
    let desc = '';
    
    if (cond.blank) {
      desc = 'must be BLANK';
    } else if (cond.percentage) {
      desc = `≥ ${cond.percentage}%`;
    } else {
      desc = 'included';
    }
    
    html += `<div class="condition-item">
      <span style="font-weight: 500; min-width: 140px;">${escapeHtmlLocal(field)}</span>
      <span style="color: var(--text-muted);">${desc}</span>
      ${cond.blank_allowed ? '<span class="badge" style="font-size: 10px; margin-left: 8px;">blank ok</span>' : ''}
    </div>`;
  }
  
  return html;
}

function openRuleModal(ruleId = null) {
  editingRuleId = ruleId;
  const modal = document.getElementById('ruleModal');
  const form = document.getElementById('ruleForm');
  const title = document.getElementById('ruleModalTitle');
  
  form.reset();
  document.getElementById('conditionsContainer').innerHTML = '';
  
  if (ruleId && rulesData?.rules?.[ruleId]) {
    const rule = rulesData.rules[ruleId];
    title.textContent = 'Edit Rule';
    document.getElementById('ruleId').value = ruleId;
    document.getElementById('ruleName').value = rule.name || '';
    document.getElementById('ruleDescription').value = rule.description || '';
    document.getElementById('rulePriority').value = rule.priority || 100;
    document.getElementById('ruleMatchReason').value = rule.match_reason || '';
    document.getElementById('ruleEnabled').checked = rule.enabled !== false;
    
    // Load conditions
    if (rule.conditions && rule.conditions.length > 0) {
      rule.conditions.forEach(cond => addCondition(cond));
    } else {
      addCondition();
    }
  } else {
    title.textContent = 'Add Rule';
    document.getElementById('ruleId').value = '';
    document.getElementById('ruleEnabled').checked = true;
    addCondition(); // Add empty condition
  }
  
  modal.hidden = false;
}

function closeRuleModal() {
  document.getElementById('ruleModal').hidden = true;
  editingRuleId = null;
}

function addCondition(existingCond = null) {
  const container = document.getElementById('conditionsContainer');
  const index = container.children.length;
  
  const fieldOptions = AVAILABLE_FIELDS.map(f => 
    `<option value="${f}" ${existingCond?.field === f ? 'selected' : ''}>${f}</option>`
  ).join('');
  
  const div = document.createElement('div');
  div.className = 'condition-row';
  div.dataset.index = index;
  
  div.innerHTML = `
    <select name="cond_field_${index}" required>
      <option value="">Select Field</option>
      ${fieldOptions}
    </select>
    <input type="number" name="cond_pct_${index}" placeholder="%" min="0" max="100" 
           value="${existingCond?.percentage || ''}" ${existingCond?.blank ? 'disabled' : ''} />
    <label style="display: flex; align-items: center; gap: 4px; font-size: 12px;">
      <input type="checkbox" name="cond_blank_${index}" 
             ${existingCond?.blank ? 'checked' : ''} 
             onchange="toggleBlankCondition(${index})" />
      Blank
    </label>
    <label style="display: flex; align-items: center; gap: 4px; font-size: 12px;">
      <input type="checkbox" name="cond_blankallowed_${index}" 
             ${existingCond?.blank_allowed ? 'checked' : ''} />
      Allow Blank
    </label>
    <button type="button" class="remove-btn" onclick="removeCondition(this)">×</button>
  `;
  
  container.appendChild(div);
}

function toggleBlankCondition(index) {
  const blankCheck = document.querySelector(`[name="cond_blank_${index}"]`);
  const pctInput = document.querySelector(`[name="cond_pct_${index}"]`);
  
  if (blankCheck && pctInput) {
    if (blankCheck.checked) {
      pctInput.disabled = true;
      pctInput.value = '';
    } else {
      pctInput.disabled = false;
    }
  }
}

function removeCondition(btn) {
  const row = btn.closest('.condition-row');
  if (row) row.remove();
}

async function saveRule(event) {
  event.preventDefault();
  
  const form = document.getElementById('ruleForm');
  let ruleId = document.getElementById('ruleId').value.trim();
  
  if (!ruleId) {
    // Generate new ID
    const existingIds = Object.keys(rulesData?.rules || {});
    let num = existingIds.length + 1;
    while (existingIds.includes(`BR${String(num).padStart(3, '0')}`)) num++;
    ruleId = `BR${String(num).padStart(3, '0')}`;
  }
  
  // Collect conditions
  const conditions = [];
  const conditionRows = document.querySelectorAll('.condition-row');
  
  conditionRows.forEach((row) => {
    const idx = row.dataset.index;
    const field = form.querySelector(`[name="cond_field_${idx}"]`)?.value;
    const pct = form.querySelector(`[name="cond_pct_${idx}"]`)?.value;
    const blank = form.querySelector(`[name="cond_blank_${idx}"]`)?.checked || false;
    const blankAllowed = form.querySelector(`[name="cond_blankallowed_${idx}"]`)?.checked || false;
    
    if (field) {
      conditions.push({
        field,
        percentage: pct || '',
        include: true,
        blank: blank,
        blank_allowed: blankAllowed
      });
    }
  });
  
  const ruleData = {
    id: ruleId,
    name: document.getElementById('ruleName').value.trim(),
    description: document.getElementById('ruleDescription').value.trim(),
    priority: parseInt(document.getElementById('rulePriority').value) || 100,
    match_reason: document.getElementById('ruleMatchReason').value.trim(),
    enabled: document.getElementById('ruleEnabled').checked,
    conditions
  };
  
  if (!ruleData.name) {
    showToast('Rule name is required', 'error');
    return;
  }
  
  try {
    const response = await fetch(`/api/rules/${ruleId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(ruleData)
    });
    
    const result = await response.json();
    
    if (result.ok) {
      showToast('Rule saved successfully', 'success');
      closeRuleModal();
      loadRules();
    } else {
      showToast(result.error || 'Failed to save rule', 'error');
    }
  } catch (error) {
    console.error('Error saving rule:', error);
    showToast('Failed to save rule', 'error');
  }
}

function editRule(ruleId) {
  openRuleModal(ruleId);
}

async function toggleRule(ruleId) {
  try {
    const response = await fetch(`/api/rules/${ruleId}/toggle`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' }
    });
    
    const result = await response.json();
    
    if (result.ok) {
      showToast(result.message, 'success');
      loadRules();
    } else {
      showToast(result.error || 'Failed to toggle rule', 'error');
    }
  } catch (error) {
    console.error('Error toggling rule:', error);
    showToast('Failed to toggle rule', 'error');
  }
}

async function deleteRule(ruleId) {
  if (!confirm(`Are you sure you want to delete rule "${ruleId}"?`)) return;
  
  try {
    const response = await fetch(`/api/rules/${ruleId}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' }
    });
    
    const result = await response.json();
    
    if (result.ok) {
      showToast('Rule deleted', 'success');
      loadRules();
    } else {
      showToast(result.error || 'Failed to delete rule', 'error');
    }
  } catch (error) {
    console.error('Error deleting rule:', error);
    showToast('Failed to delete rule', 'error');
  }
}
