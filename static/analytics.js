// Analytics page JavaScript

document.addEventListener('DOMContentLoaded', loadProcessedFiles);

async function loadProcessedFiles() {
  try {
    const response = await fetch('/api/processed-files');
    const files = await response.json();
    
    const select = document.getElementById('fileSelect');
    select.innerHTML = '<option value="">-- Select a file --</option>';
    
    files.forEach(file => {
      if (file.has_analytics) {
        const option = document.createElement('option');
        option.value = file.analytics_filename;
        option.textContent = `${file.filename} (${formatDate(file.modified)})`;
        select.appendChild(option);
      }
    });
    
    // Auto-select if only one file or if coming from upload
    if (files.length === 1 && files[0].has_analytics) {
      select.value = files[0].analytics_filename;
      loadAnalytics();
    }
  } catch (error) {
    console.error('Failed to load processed files:', error);
  }
}

async function loadAnalytics() {
  const select = document.getElementById('fileSelect');
  const filename = select.value;
  const container = document.getElementById('analyticsContainer');
  
  if (!filename) {
    container.innerHTML = `
      <div class="no-data">
        <h3>No File Selected</h3>
        <p>Select a processed file above to view its analytics, or <a href="/upload">upload a new file</a>.</p>
      </div>
    `;
    return;
  }
  
  container.innerHTML = '<div class="loading">Loading analytics...</div>';
  
  try {
    const response = await fetch(`/api/analytics/${filename}`);
    const analytics = await response.json();
    
    if (analytics.error) {
      container.innerHTML = `<div class="no-data"><h3>Error</h3><p>${analytics.error}</p></div>`;
      return;
    }
    
    renderAnalytics(analytics, container);
  } catch (error) {
    container.innerHTML = `<div class="no-data"><h3>Error</h3><p>Failed to load analytics.</p></div>`;
  }
}

function renderAnalytics(analytics, container) {
  const { summary, data_quality, column_completeness, field_analytics, duplicates, value_distributions } = analytics;
  
  let html = '';
  
  // Summary cards
  html += `
    <div class="analytics-grid">
      <div class="stat-card">
        <h3>Data Quality Grade</h3>
        <div class="stat-value grade grade-${data_quality.grade.toLowerCase()}">${data_quality.grade}</div>
        <div class="stat-subtitle">Overall Score: ${data_quality.overall_score}%</div>
        <div class="quality-bar">
          <div class="quality-bar-fill ${getQualityClass(data_quality.overall_score)}" style="width: ${data_quality.overall_score}%"></div>
        </div>
      </div>
      
      <div class="stat-card">
        <h3>Total Records</h3>
        <div class="stat-value">${summary.total_rows.toLocaleString()}</div>
        <div class="stat-subtitle">${summary.total_columns} columns</div>
      </div>
      
      <div class="stat-card">
        <h3>Completeness Score</h3>
        <div class="stat-value">${data_quality.completeness_score}%</div>
        <div class="stat-subtitle">Average field fill rate</div>
        <div class="quality-bar">
          <div class="quality-bar-fill ${getQualityClass(data_quality.completeness_score)}" style="width: ${data_quality.completeness_score}%"></div>
        </div>
      </div>
      
      <div class="stat-card">
        <h3>Duplicate Records</h3>
        <div class="stat-value">${duplicates.exact_duplicates}</div>
        <div class="stat-subtitle">Exact duplicates found</div>
      </div>
    </div>
  `;
  
  // Field-specific analytics
  if (Object.keys(field_analytics).length > 0) {
    html += '<h2 class="section-title">Field Analytics</h2>';
    html += '<div class="field-stats-grid">';
    
    if (field_analytics.email) {
      html += renderFieldCard('Email', field_analytics.email, [
        { label: 'Total', value: field_analytics.email.total },
        { label: 'Valid', value: field_analytics.email.valid },
        { label: 'Invalid', value: field_analytics.email.invalid },
        { label: 'Validity', value: `${field_analytics.email.validity_pct}%` },
        { label: 'Unique', value: field_analytics.email.unique }
      ]);
    }
    
    if (field_analytics.phone) {
      html += renderFieldCard('Phone', field_analytics.phone, [
        { label: 'Total', value: field_analytics.phone.total },
        { label: 'Valid', value: field_analytics.phone.valid },
        { label: 'Invalid', value: field_analytics.phone.invalid },
        { label: 'Validity', value: `${field_analytics.phone.validity_pct}%` },
        { label: 'Unique', value: field_analytics.phone.unique }
      ]);
    }
    
    if (field_analytics.zip_code) {
      html += renderFieldCard('ZIP Code', field_analytics.zip_code, [
        { label: 'Total', value: field_analytics.zip_code.total },
        { label: 'Valid', value: field_analytics.zip_code.valid },
        { label: 'Invalid', value: field_analytics.zip_code.invalid },
        { label: 'Validity', value: `${field_analytics.zip_code.validity_pct}%` },
        { label: 'Unique', value: field_analytics.zip_code.unique }
      ]);
    }
    
    if (field_analytics.company_name) {
      html += renderFieldCard('Company Name', field_analytics.company_name, [
        { label: 'Total', value: field_analytics.company_name.total },
        { label: 'Unique', value: field_analytics.company_name.unique },
        { label: 'Avg Length', value: `${field_analytics.company_name.avg_length} chars` }
      ]);
    }
    
    if (field_analytics.state) {
      html += renderFieldCard('State Distribution', field_analytics.state, [
        { label: 'Unique States', value: field_analytics.state.unique_states }
      ]);
    }
    
    html += '</div>';
  }
  
  // Duplicate analysis
  if (duplicates.potential_duplicates && Object.keys(duplicates.potential_duplicates).length > 0) {
    html += '<h2 class="section-title">Duplicate Analysis</h2>';
    
    const totalPotentialDups = Object.values(duplicates.potential_duplicates)
      .reduce((sum, d) => sum + d.duplicate_count, 0);
    
    const alertClass = totalPotentialDups === 0 ? 'success' : (totalPotentialDups < 10 ? 'warning' : '');
    
    html += `
      <div class="duplicate-alert ${alertClass}">
        <strong>${totalPotentialDups === 0 ? '✓ No potential duplicates detected' : `⚠ ${totalPotentialDups} potential duplicates detected`}</strong>
        <p style="margin: 0.5rem 0 0; font-size: 0.875rem; color: var(--text-muted);">
          Based on key field combinations (company+phone, company+address, email, phone)
        </p>
      </div>
    `;
    
    html += '<div class="field-stats-grid">';
    for (const [key, data] of Object.entries(duplicates.potential_duplicates)) {
      html += `
        <div class="field-stat-card">
          <h4>${formatDuplicateKey(key)}</h4>
          <div class="field-stat-item">
            <span class="label">Duplicates</span>
            <span class="value">${data.duplicate_count}</span>
          </div>
          <div class="field-stat-item">
            <span class="label">Fields</span>
            <span class="value" style="font-size: 0.75rem">${data.fields.join(', ')}</span>
          </div>
        </div>
      `;
    }
    html += '</div>';
  }
  
  // Value distributions
  if (Object.keys(value_distributions).length > 0) {
    html += '<h2 class="section-title">Value Distributions</h2>';
    html += '<div class="field-stats-grid">';
    
    for (const [field, data] of Object.entries(value_distributions)) {
      if (data.top_values && Object.keys(data.top_values).length > 0) {
        const maxCount = Math.max(...Object.values(data.top_values));
        
        html += `
          <div class="field-stat-card">
            <h4>${formatFieldName(field)}</h4>
            <div class="distribution-chart">
              ${Object.entries(data.top_values).slice(0, 5).map(([value, count]) => `
                <div class="distribution-item">
                  <span class="distribution-label" title="${escapeHtml(value)}">${escapeHtml(value) || '(empty)'}</span>
                  <div class="distribution-bar-container">
                    <div class="distribution-bar" style="width: ${(count / maxCount) * 100}%"></div>
                  </div>
                  <span class="distribution-count">${count}</span>
                </div>
              `).join('')}
            </div>
            <div class="field-stat-item" style="margin-top: 0.75rem; border-top: 1px solid var(--border); padding-top: 0.5rem;">
              <span class="label">Unique Values</span>
              <span class="value">${data.unique_values}</span>
            </div>
          </div>
        `;
      }
    }
    html += '</div>';
  }
  
  // Column completeness table
  html += '<h2 class="section-title">Column Completeness</h2>';
  html += `
    <div class="card">
      <table class="completeness-table">
        <thead>
          <tr>
            <th>Column</th>
            <th>Filled</th>
            <th>Empty</th>
            <th>Completeness</th>
          </tr>
        </thead>
        <tbody>
          ${Object.entries(column_completeness)
            .sort((a, b) => b[1].completeness_pct - a[1].completeness_pct)
            .map(([col, data]) => `
              <tr>
                <td><code>${escapeHtml(col)}</code></td>
                <td>${data.filled.toLocaleString()}</td>
                <td>${data.empty.toLocaleString()}</td>
                <td>
                  <div class="completeness-bar">
                    <div class="completeness-bar-fill ${getQualityClass(data.completeness_pct)}" style="width: ${data.completeness_pct}%"></div>
                    <span class="completeness-bar-text">${data.completeness_pct}%</span>
                  </div>
                </td>
              </tr>
            `).join('')}
        </tbody>
      </table>
    </div>
  `;
  
  container.innerHTML = html;
}

function renderFieldCard(title, data, items) {
  return `
    <div class="field-stat-card">
      <h4>${title}</h4>
      ${items.map(item => `
        <div class="field-stat-item">
          <span class="label">${item.label}</span>
          <span class="value">${typeof item.value === 'number' ? item.value.toLocaleString() : item.value}</span>
        </div>
      `).join('')}
    </div>
  `;
}

function getQualityClass(score) {
  if (score >= 80) return 'high';
  if (score >= 50) return 'medium';
  return 'low';
}

function formatDuplicateKey(key) {
  const labels = {
    'company_phone': 'Company + Phone',
    'company_address': 'Company + Address',
    'email': 'Email Address',
    'phone': 'Phone Number'
  };
  return labels[key] || key;
}

function formatFieldName(field) {
  return field.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function formatDate(isoString) {
  return new Date(isoString).toLocaleDateString();
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text || '';
  return div.innerHTML;
}

