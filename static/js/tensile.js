/**
 * MAT-VLAB — Manual Data Entry & Tensile Analysis Controller
 */

let rowCounter = 0;

function updateAreaDisplay() {
  const diamInput = document.getElementById('specimen-diameter');
  const areaDisplay = document.getElementById('calculated-area');
  if (!diamInput || !areaDisplay) return;

  const d = parseFloat(diamInput.value);
  if (d > 0) {
    const area = (Math.PI * Math.pow(d, 2)) / 4.0;
    areaDisplay.value = area.toFixed(3) + ' mm²';
  } else {
    areaDisplay.value = '—';
  }
}

function addReadingRow(load = '', ext = '') {
  const tableBody = document.getElementById('readings-table-body');
  if (!tableBody) return;

  rowCounter++;
  const tr = document.createElement('tr');
  tr.id = `row-${rowCounter}`;
  tr.innerHTML = `
    <td class="text-center font-mono text-muted reading-num" data-label="Reading #">${rowCounter}</td>
    <td data-label="Load (N)">
      <input type="number" step="any" min="0" inputmode="decimal" class="form-control form-lab-control font-mono input-load" placeholder="e.g. 10000" value="${load}" required>
    </td>
    <td data-label="Extension (mm)">
      <input type="number" step="any" min="0" inputmode="decimal" class="form-control form-lab-control font-mono input-ext" placeholder="e.g. 0.035" value="${ext}" required>
    </td>
    <td class="text-center" data-label="Action">
      <button type="button" class="btn btn-sm btn-outline-danger" onclick="deleteReadingRow(${rowCounter})" title="Delete row">
        <i class="fas fa-trash-alt me-1 d-sm-none"></i> <span class="d-sm-none">Delete Reading</span><span class="d-none d-sm-inline"><i class="fas fa-trash-alt"></i></span>
      </button>
    </td>
  `;
  tableBody.appendChild(tr);
  updateRowIndices();
}

function deleteReadingRow(rowId) {
  const row = document.getElementById(`row-${rowId}`);
  if (row) {
    row.remove();
    updateRowIndices();
  }
}

function updateRowIndices() {
  const rows = document.querySelectorAll('#readings-table-body tr');
  rows.forEach((r, idx) => {
    const numCell = r.querySelector('.reading-num');
    if (numCell) numCell.textContent = idx + 1;
  });
  const countBadge = document.getElementById('row-count-badge');
  if (countBadge) countBadge.textContent = `${rows.length} readings`;
}

function clearAllRows() {
  const tableBody = document.getElementById('readings-table-body');
  if (tableBody) {
    tableBody.innerHTML = '';
    rowCounter = 0;
    updateRowIndices();
    showToast('Observation table cleared.', 'info');
  }
}

// Load default ASTM mild steel sample data
function loadSampleDataset() {
  clearAllRows();

  const diamInput = document.getElementById('specimen-diameter');
  const lengthInput = document.getElementById('specimen-gauge-length');
  const matSelect = document.getElementById('specimen-material');

  if (diamInput) diamInput.value = "10.0";
  if (lengthInput) lengthInput.value = "50.0";
  if (matSelect) matSelect.value = "Mild Steel (AISI 1018 / IS 2062)";
  updateAreaDisplay();

  const samplePoints = [
    [0, 0.000], [2500, 0.008], [5000, 0.016], [7500, 0.023],
    [10000, 0.031], [12500, 0.039], [15000, 0.047], [17500, 0.055],
    [19500, 0.061], [19800, 0.085], [19400, 0.180], [19500, 0.320],
    [19600, 0.500], [20800, 0.850], [22500, 1.350], [25200, 2.100],
    [28400, 3.150], [31200, 4.400], [33100, 5.700], [34200, 7.100],
    [34500, 8.200], [34200, 9.500], [33000, 10.800], [31100, 12.100],
    [28600, 13.400], [26200, 14.200]
  ];

  samplePoints.forEach(([load, ext]) => {
    addReadingRow(load, ext);
  });

  showToast(`Loaded ${samplePoints.length} standard ASTM mild steel observation readings.`, 'success');
}

// CSV File Upload Parser
function handleCsvUpload(file) {
  if (!file) return;

  const reader = new FileReader();
  reader.onload = function(e) {
    const text = e.target.result;
    const lines = text.split(/\r\n|\n/);
    let parsedCount = 0;

    clearAllRows();

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) continue;

      const cols = line.split(',');
      if (cols.length >= 2) {
        // Check if header line
        const val1 = parseFloat(cols[cols.length - 2]);
        const val2 = parseFloat(cols[cols.length - 1]);

        if (!isNaN(val1) && !isNaN(val2)) {
          // If 3 columns (Reading, Load, Extension), take 2nd and 3rd
          const load = cols.length >= 3 ? parseFloat(cols[1]) : val1;
          const ext = cols.length >= 3 ? parseFloat(cols[2]) : val2;
          addReadingRow(load, ext);
          parsedCount++;
        }
      }
    }

    if (parsedCount > 0) {
      showToast(`Successfully imported ${parsedCount} readings from CSV!`, 'success');
    } else {
      showToast('No valid numeric readings found in CSV file. Ensure columns are Load, Extension.', 'danger');
    }
  };
  reader.readAsText(file);
}

// Submit for analysis
function submitForAnalysis() {
  const diamInput = document.getElementById('specimen-diameter');
  const lengthInput = document.getElementById('specimen-gauge-length');
  const finalLenInput = document.getElementById('specimen-final-length');
  const finalDiamInput = document.getElementById('specimen-final-diameter');
  const matSelect = document.getElementById('specimen-material');
  const expTitleInput = document.getElementById('experiment-title');

  const diameter = parseFloat(diamInput ? diamInput.value : 0);
  const gaugeLength = parseFloat(lengthInput ? lengthInput.value : 0);

  // Validation
  if (!diameter || diameter <= 0) {
    showToast('Please enter a valid original specimen diameter (d₀ > 0 mm).', 'warning');
    if (diamInput) diamInput.focus();
    return;
  }

  if (!gaugeLength || gaugeLength <= 0) {
    showToast('Please enter a valid original gauge length (L₀ > 0 mm).', 'warning');
    if (lengthInput) lengthInput.focus();
    return;
  }

  const rows = document.querySelectorAll('#readings-table-body tr');
  const readings = [];

  rows.forEach((r, idx) => {
    const loadVal = parseFloat(r.querySelector('.input-load').value);
    const extVal = parseFloat(r.querySelector('.input-ext').value);

    if (!isNaN(loadVal) && !isNaN(extVal)) {
      readings.push({
        reading_number: idx + 1,
        load_n: Math.max(0, loadVal),
        extension_mm: Math.max(0, extVal)
      });
    }
  });

  if (readings.length < 2) {
    showToast('Please provide at least 2 observation readings to compute stress-strain properties.', 'warning');
    return;
  }

  const payload = {
    mode: 'MANUAL_ENTRY',
    title: expTitleInput && expTitleInput.value.trim() ? expTitleInput.value.trim() : 'Tensile Test Experiment',
    material_name: matSelect ? matSelect.value : 'Mild Steel',
    original_diameter: diameter,
    original_gauge_length: gaugeLength,
    final_gauge_length: finalLenInput && finalLenInput.value ? parseFloat(finalLenInput.value) : null,
    final_diameter: finalDiamInput && finalDiamInput.value ? parseFloat(finalDiamInput.value) : null,
    readings: readings
  };

  // Call API
  const btnAnalyze = document.getElementById('btn-analyze-data');
  if (btnAnalyze) {
    btnAnalyze.disabled = true;
    btnAnalyze.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Calculating...';
  }

  fetch('/api/calculate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  .then(res => res.json())
  .then(data => {
    if (btnAnalyze) {
      btnAnalyze.disabled = false;
      btnAnalyze.innerHTML = '<i class="fas fa-calculator me-2"></i> Analyze Data';
    }

    if (data.error) {
      showToast(data.error, 'danger');
      return;
    }

    // Save analyzed object in sessionStorage and navigate to results page
    sessionStorage.setItem('matvlab_analysis_data', JSON.stringify({
      ...payload,
      results: data.summary,
      readings: data.computed_readings,
      formulas: data.formulas,
      conclusion: data.conclusion,
      warnings: data.warnings
    }));

    window.location.href = '/results';
  })
  .catch(err => {
    console.error(err);
    if (btnAnalyze) {
      btnAnalyze.disabled = false;
      btnAnalyze.innerHTML = '<i class="fas fa-calculator me-2"></i> Analyze Data';
    }
    showToast('An error occurred while communicating with calculation engine.', 'danger');
  });
}

document.addEventListener('DOMContentLoaded', () => {
  const diamInput = document.getElementById('specimen-diameter');
  if (diamInput) {
    diamInput.addEventListener('input', updateAreaDisplay);
    updateAreaDisplay();
  }

  const btnAddRow = document.getElementById('btn-add-reading');
  if (btnAddRow) btnAddRow.addEventListener('click', () => addReadingRow());

  const btnClear = document.getElementById('btn-clear-readings');
  if (btnClear) btnClear.addEventListener('click', clearAllRows);

  const btnSample = document.getElementById('btn-load-sample');
  if (btnSample) btnSample.addEventListener('click', loadSampleDataset);

  const btnAnalyze = document.getElementById('btn-analyze-data');
  if (btnAnalyze) btnAnalyze.addEventListener('click', submitForAnalysis);

  const fileInput = document.getElementById('csv-file-input');
  if (fileInput) {
    fileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files[0]) {
        handleCsvUpload(e.target.files[0]);
      }
    });
  }

  // Pre-seed 4 empty rows if table is empty
  const tableBody = document.getElementById('readings-table-body');
  if (tableBody && tableBody.children.length === 0) {
    addReadingRow(0, 0.000);
    addReadingRow('', '');
    addReadingRow('', '');
    addReadingRow('', '');
  }
});
