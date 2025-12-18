let settingsData = null;

document.addEventListener('DOMContentLoaded', loadSettings);

async function loadSettings() {
  try {
    settingsData = await fetchJSON('/api/settings');
    renderThresholds();
    renderScoringWeights();
    renderQualityScores();
    renderAppSettings();
  } catch (error) {
    showToast('Failed to load settings', 'error');
  }
}

function renderThresholds() {
  const container = document.getElementById('thresholds-container');
  const thresholds = settingsData.thresholds || {};
  
  if (Object.keys(thresholds).length === 0) {
    container.innerHTML = '<p class="muted">No thresholds configured.</p>';
    return;
  }
  
  let html = '';
  for (const [key, config] of Object.entries(thresholds)) {
    const value = config.value || 0;
    const min = config.min || 0;
    const max = config.max || 100;
    
    html += `
      <div class="setting-item">
        <label>${escapeHtml(key.replace(/_/g, ' ').toUpperCase())}</label>
        <p class="description">${escapeHtml(config.description || '')}</p>
        <input type="range" 
               id="threshold_${key}" 
               min="${min}" max="${max}" 
               value="${value}"
               oninput="updateThresholdDisplay('${key}', this.value)" />
        <div class="value-display" id="threshold_${key}_display">${value}%</div>
        <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">
          Group: ${escapeHtml(config.group || 'N/A')} | 
          Allow blank: ${config.allow_blank ? 'Yes' : 'No'}
        </div>
      </div>
    `;
  }
  
  container.innerHTML = html;
}

function updateThresholdDisplay(key, value) {
  document.getElementById(`threshold_${key}_display`).textContent = `${value}%`;
}

async function saveThresholds() {
  try {
    const thresholds = settingsData.thresholds || {};
    
    for (const key of Object.keys(thresholds)) {
      const input = document.getElementById(`threshold_${key}`);
      if (input) {
        thresholds[key].value = parseFloat(input.value);
      }
    }
    
    settingsData.thresholds = thresholds;
    const result = await postJSON('/api/settings', settingsData);
    
    if (result.ok) {
      showToast('Thresholds saved successfully', 'success');
    } else {
      showToast(result.error || 'Failed to save', 'error');
    }
  } catch (error) {
    showToast('Failed to save thresholds', 'error');
  }
}

function renderScoringWeights() {
  const container = document.getElementById('scoring-container');
  const weights = settingsData.scoring?.field_weights || {};
  
  if (Object.keys(weights).length === 0) {
    container.innerHTML = '<p class="muted">No scoring weights configured.</p>';
    return;
  }
  
  let html = '';
  for (const [field, weight] of Object.entries(weights)) {
    html += `
      <div class="setting-item">
        <label>${escapeHtml(field.replace(/_/g, ' ').toUpperCase())}</label>
        <p class="description">Weight for ${field} in overall matching score</p>
        <input type="range" 
               id="weight_${field}" 
               min="0" max="1" step="0.05"
               value="${weight}"
               oninput="updateWeightDisplay('${field}', this.value)" />
        <div class="value-display" id="weight_${field}_display">${(weight * 100).toFixed(0)}%</div>
      </div>
    `;
  }
  
  container.innerHTML = html;
}

function updateWeightDisplay(field, value) {
  document.getElementById(`weight_${field}_display`).textContent = `${(value * 100).toFixed(0)}%`;
}

async function saveScoringWeights() {
  try {
    const weights = settingsData.scoring?.field_weights || {};
    
    for (const field of Object.keys(weights)) {
      const input = document.getElementById(`weight_${field}`);
      if (input) {
        weights[field] = parseFloat(input.value);
      }
    }
    
    if (!settingsData.scoring) settingsData.scoring = {};
    settingsData.scoring.field_weights = weights;
    
    const result = await postJSON('/api/settings', settingsData);
    
    if (result.ok) {
      showToast('Scoring weights saved', 'success');
    } else {
      showToast(result.error || 'Failed to save', 'error');
    }
  } catch (error) {
    showToast('Failed to save scoring weights', 'error');
  }
}

function renderQualityScores() {
  const container = document.getElementById('quality-container');
  const qualityScores = settingsData.quality_scores || {};
  
  if (Object.keys(qualityScores).length === 0) {
    container.innerHTML = '<p class="muted">No quality scores configured.</p>';
    return;
  }
  
  let html = '';
  
  for (const [category, config] of Object.entries(qualityScores)) {
    const criteria = config.criteria || {};
    
    html += `
      <div class="quality-section">
        <h3>${escapeHtml(category.toUpperCase())} Quality Criteria</h3>
        <div class="quality-grid">
    `;
    
    for (const [criteriaKey, criteriaConfig] of Object.entries(criteria)) {
      html += `
        <div class="quality-item">
          <div class="quality-item-header">
            <label>${escapeHtml(criteriaKey.replace(/_/g, ' '))}</label>
          </div>
          <p class="description">${escapeHtml(criteriaConfig.description || '')}</p>
          <div class="quality-inputs">
            <div class="input-group">
              <label>Percentage</label>
              <input type="number" 
                     id="quality_${category}_${criteriaKey}_pct" 
                     value="${criteriaConfig.percentage || 100}"
                     min="0" max="100" />
            </div>
            <div class="input-group">
              <label>Max Points</label>
              <input type="number" 
                     id="quality_${category}_${criteriaKey}_pts" 
                     value="${criteriaConfig.max_points || 0}"
                     min="0" />
            </div>
          </div>
        </div>
      `;
    }
    
    html += '</div></div>';
  }
  
  container.innerHTML = html;
}

async function saveQualityScores() {
  try {
    const qualityScores = settingsData.quality_scores || {};
    
    for (const [category, config] of Object.entries(qualityScores)) {
      const criteria = config.criteria || {};
      
      for (const criteriaKey of Object.keys(criteria)) {
        const pctInput = document.getElementById(`quality_${category}_${criteriaKey}_pct`);
        const ptsInput = document.getElementById(`quality_${category}_${criteriaKey}_pts`);
        
        if (pctInput) criteria[criteriaKey].percentage = parseInt(pctInput.value) || 0;
        if (ptsInput) criteria[criteriaKey].max_points = parseInt(ptsInput.value) || 0;
      }
    }
    
    settingsData.quality_scores = qualityScores;
    const result = await postJSON('/api/settings', settingsData);
    
    if (result.ok) {
      showToast('Quality scores saved', 'success');
    } else {
      showToast(result.error || 'Failed to save', 'error');
    }
  } catch (error) {
    showToast('Failed to save quality scores', 'error');
  }
}

function renderAppSettings() {
  const container = document.getElementById('app-container');
  const appConfig = settingsData.app || {};
  const matchingConfig = settingsData.matching || {};
  const mlConfig = settingsData.ml || {};
  
  let html = `
    <div class="setting-item">
      <label>Upload Folder</label>
      <input type="text" id="app_upload_folder" value="${escapeHtml(appConfig.upload_folder || '')}" />
    </div>
    <div class="setting-item">
      <label>Output Folder</label>
      <input type="text" id="app_output_folder" value="${escapeHtml(appConfig.output_folder || '')}" />
    </div>
    <div class="setting-item">
      <label>Max File Size (MB)</label>
      <input type="number" id="app_max_file_size" value="${appConfig.max_file_size_mb || 50}" min="1" />
    </div>
    <div class="setting-item">
      <label>Batch Size</label>
      <input type="number" id="matching_batch_size" value="${matchingConfig.batch_size || 5000}" min="100" />
    </div>
    <div class="setting-item">
      <label>ML Enabled</label>
      <select id="ml_enabled">
        <option value="true" ${mlConfig.enabled ? 'selected' : ''}>Yes</option>
        <option value="false" ${!mlConfig.enabled ? 'selected' : ''}>No</option>
      </select>
    </div>
    <div class="setting-item">
      <label>ML Confidence Threshold</label>
      <input type="number" id="ml_confidence" value="${mlConfig.confidence_threshold || 0.75}" min="0" max="1" step="0.05" />
    </div>
  `;
  
  container.innerHTML = html;
}

async function saveAppSettings() {
  try {
    settingsData.app = settingsData.app || {};
    settingsData.matching = settingsData.matching || {};
    settingsData.ml = settingsData.ml || {};
    
    settingsData.app.upload_folder = document.getElementById('app_upload_folder').value;
    settingsData.app.output_folder = document.getElementById('app_output_folder').value;
    settingsData.app.max_file_size_mb = parseInt(document.getElementById('app_max_file_size').value) || 50;
    settingsData.matching.batch_size = parseInt(document.getElementById('matching_batch_size').value) || 5000;
    settingsData.ml.enabled = document.getElementById('ml_enabled').value === 'true';
    settingsData.ml.confidence_threshold = parseFloat(document.getElementById('ml_confidence').value) || 0.75;
    
    const result = await postJSON('/api/settings', settingsData);
    
    if (result.ok) {
      showToast('Application settings saved', 'success');
    } else {
      showToast(result.error || 'Failed to save', 'error');
    }
  } catch (error) {
    showToast('Failed to save application settings', 'error');
  }
}

