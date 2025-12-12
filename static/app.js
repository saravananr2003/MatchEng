const form = document.getElementById('uploadForm');
const fileInput = document.getElementById('fileInput');
const uploadBtn = document.getElementById('uploadBtn');

const statusEl = document.getElementById('status');
const resultEl = document.getElementById('result');

const processedEl = document.getElementById('processed');
const matchedEl = document.getElementById('matched');
const newdedupEl = document.getElementById('newdedup');
const errorsEl = document.getElementById('errors');
const downloadLink = document.getElementById('downloadLink');

function setStatus(msg, kind = 'info') {
  statusEl.hidden = false;
  statusEl.className = `status ${kind}`;
  statusEl.textContent = msg;
}

function clearStatus() {
  statusEl.hidden = true;
  statusEl.textContent = '';
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  clearStatus();
  resultEl.hidden = true;

  const file = fileInput.files?.[0];
  if (!file) {
    setStatus('Please select a CSV file.', 'error');
    return;
  }

  uploadBtn.disabled = true;
  setStatus('Uploading and matching...', 'info');

  try {
    const fd = new FormData();
    fd.append('file', file);

    const resp = await fetch('/api/upload', {
      method: 'POST',
      body: fd,
    });

    const data = await resp.json();
    if (!resp.ok) {
      setStatus(data?.error || 'Upload failed', 'error');
      if (data?.missing) {
        setStatus(`Upload failed: missing columns: ${data.missing.join(', ')}`, 'error');
      }
      return;
    }

    processedEl.textContent = data.stats.processed;
    matchedEl.textContent = data.stats.matched_existing;
    newdedupEl.textContent = data.stats.new_dedup;
    errorsEl.textContent = data.stats.errors;

    downloadLink.href = data.download_url;

    resultEl.hidden = false;
    setStatus('Done. Download the annotated CSV.', 'success');
  } catch (err) {
    setStatus(`Unexpected error: ${err}`, 'error');
  } finally {
    uploadBtn.disabled = false;
  }
});
