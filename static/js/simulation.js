/**
 * MAT-VLAB — Virtual Tensile Simulation Engine
 */

let simData = null;
let currentStep = 0;
let isPlaying = false;
let playInterval = null;
let plotInitialized = false;

// Initialize Simulation
function initSimulation() {
  const matSelect = document.getElementById('sim-material');
  const diamInput = document.getElementById('sim-diameter');
  const lengthInput = document.getElementById('sim-gauge-length');

  if (!matSelect) return;

  const materialSlug = matSelect.value;
  const diameter = parseFloat(diamInput.value) || 10.0;
  const gaugeLength = parseFloat(lengthInput.value) || 50.0;

  // Reset state
  pauseSimulation();
  currentStep = 0;

  // Fetch simulation curve data from backend
  fetch(`/api/simulation-data?material=${materialSlug}&diameter=${diameter}&gauge_length=${gaugeLength}`)
    .then(res => res.json())
    .then(data => {
      simData = data;
      resetVisuals();
      initPlot();
      updateStepDisplay(0);
      showToast(`Loaded ${data.material_name} simulation model. Ready to test!`, 'info');
    })
    .catch(err => {
      console.error("Simulation load failed", err);
      showToast('Failed to load simulation data', 'danger');
    });
}

function initPlot() {
  const plotDiv = document.getElementById('sim-plot');
  if (!plotDiv || !simData) return;

  const traceAll = {
    x: simData.readings.map(r => r.strain),
    y: simData.readings.map(r => r.stress_mpa),
    mode: 'lines',
    line: { color: 'rgba(43, 108, 176, 0.25)', width: 2, dash: 'dot' },
    name: 'Theoretical Envelope',
    hoverinfo: 'none'
  };

  const traceProgress = {
    x: [0],
    y: [0],
    mode: 'lines+markers',
    line: { color: '#0f2b48', width: 3 },
    marker: { color: '#2b6cb0', size: 6 },
    name: 'Current Trajectory'
  };

  const traceCurrent = {
    x: [0],
    y: [0],
    mode: 'markers',
    marker: { color: '#dc2626', size: 12, symbol: 'cross' },
    name: 'Current State'
  };

  const maxStrain = Math.max(...simData.readings.map(r => r.strain)) * 1.1;
  const maxStress = Math.max(...simData.readings.map(r => r.stress_mpa)) * 1.15;

  const layout = {
    title: {
      text: `SIMULATION DATA: Stress-Strain Curve — ${simData.material_name}`,
      font: { color: '#0f2b48', size: 14, family: 'Poppins', weight: 700 }
    },
    paper_bgcolor: '#ffffff',
    plot_bgcolor: '#f8fafc',
    xaxis: {
      title: { text: 'Engineering Strain, ε (mm/mm)', font: { color: '#334155', size: 12, family: 'Inter' } },
      tickfont: { color: '#475569', family: 'Inter' },
      gridcolor: '#e2e8f0',
      range: [0, maxStrain],
      zerolinecolor: '#cbd5e1'
    },
    yaxis: {
      title: { text: 'Engineering Stress, σ (MPa)', font: { color: '#334155', size: 12, family: 'Inter' } },
      tickfont: { color: '#475569', family: 'Inter' },
      gridcolor: '#e2e8f0',
      range: [0, maxStress],
      zerolinecolor: '#cbd5e1'
    },
    margin: {
      l: window.innerWidth < 576 ? 45 : 55,
      r: window.innerWidth < 576 ? 15 : 25,
      t: window.innerWidth < 576 ? 35 : 45,
      b: window.innerWidth < 576 ? 40 : 45
    },
    showlegend: false,
    hovermode: 'closest'
  };

  const config = {
    responsive: true,
    displayModeBar: true,
    displaylogo: false,
    modeBarButtonsToRemove: ['lasso2d', 'select2d']
  };

  Plotly.newPlot(plotDiv, [traceAll, traceProgress, traceCurrent], layout, config);
  plotInitialized = true;
}

function updateStepDisplay(stepIdx) {
  if (!simData || !simData.readings || stepIdx >= simData.readings.length) return;

  currentStep = stepIdx;
  const r = simData.readings[stepIdx];
  const totalSteps = simData.readings.length;

  // Update slider if present
  const slider = document.getElementById('sim-load-slider');
  if (slider) {
    slider.max = totalSteps - 1;
    slider.value = stepIdx;
  }

  // Telemetry Readouts
  const elLoadN = document.getElementById('telemetry-load-n');
  const elLoadKn = document.getElementById('telemetry-load-kn');
  const elExt = document.getElementById('telemetry-ext');
  const elStress = document.getElementById('telemetry-stress');
  const elStrain = document.getElementById('telemetry-strain');
  const elStatus = document.getElementById('telemetry-status');
  const elProgress = document.getElementById('sim-progress-bar');

  if (elLoadN) elLoadN.textContent = formatNumber(r.load_n, 1);
  if (elLoadKn) elLoadKn.textContent = formatNumber(r.load_n / 1000.0, 2);
  if (elExt) elExt.textContent = formatNumber(r.extension_mm, 3);
  if (elStress) elStress.textContent = formatNumber(r.stress_mpa, 1);
  if (elStrain) elStrain.textContent = (r.strain * 100).toFixed(2) + '%';

  const pctProgress = ((stepIdx / (totalSteps - 1)) * 100).toFixed(0);
  if (elProgress) {
    elProgress.style.width = pctProgress + '%';
    elProgress.textContent = pctProgress + '%';
  }

  // Metallurgical state determination
  let statusText = "Elastic Region (Hookean)";
  let statusBadgeClass = "text-info";

  const maxStressIdx = simData.readings.reduce((maxI, curr, i, arr) => curr.stress_mpa > arr[maxI].stress_mpa ? i : maxI, 0);

  if (stepIdx === totalSteps - 1) {
    statusText = "Specimen Fractured (Cup & Cone Shear)";
    statusBadgeClass = "text-danger";
  } else if (stepIdx > maxStressIdx) {
    statusText = "Localized Necking & Void Coalescence";
    statusBadgeClass = "text-warning";
  } else if (stepIdx > 4) {
    statusText = "Plastic Deformation & Strain Hardening";
    statusBadgeClass = "text-primary";
  }

  if (elStatus) {
    elStatus.textContent = statusText;
    elStatus.className = `telemetry-value ${statusBadgeClass}`;
  }

  // Animate SVG Machine and Specimen
  animateMachineVisual(stepIdx, totalSteps, maxStressIdx);

  // Update Plotly chart
  if (plotInitialized) {
    const activeStrains = simData.readings.slice(0, stepIdx + 1).map(x => x.strain);
    const activeStresses = simData.readings.slice(0, stepIdx + 1).map(x => x.stress_mpa);

    Plotly.restyle('sim-plot', {
      x: [activeStrains, [r.strain]],
      y: [activeStresses, [r.stress_mpa]]
    }, [1, 2]);
  }

  // Check if completed
  if (stepIdx === totalSteps - 1) {
    pauseSimulation();
    const actionCard = document.getElementById('sim-completion-card');
    if (actionCard) actionCard.classList.remove('d-none');
    showToast('Simulation complete: Specimen fractured!', 'success');
  }
}

function animateMachineVisual(stepIdx, totalSteps, maxStressIdx) {
  const normStep = stepIdx / (totalSteps - 1);

  // 1. Move crosshead upwards (SVG translation)
  // Crosshead group ID: #part-crosshead
  const crosshead = document.getElementById('part-crosshead');
  const upperGrip = document.getElementById('part-upper-grip');
  const loadCell = document.getElementById('part-load-cell');

  const maxLift = -40; // pixels upward
  const currentLift = maxLift * normStep;

  if (crosshead) crosshead.style.transform = `translateY(${currentLift}px)`;
  if (upperGrip) upperGrip.style.transform = `translateY(${currentLift}px)`;
  if (loadCell) loadCell.style.transform = `translateY(${currentLift}px)`;

  // 2. Specimen Gauge Section Stretches & Necks
  const gaugeSec = document.getElementById('specimen-gauge-section');
  const neckZone = document.getElementById('specimen-neck-zone');

  if (gaugeSec) {
    // Initial height 80px, width 8px
    const newHeight = 80 + (Math.abs(currentLift) * 0.8);
    gaugeSec.setAttribute('height', newHeight);
    gaugeSec.setAttribute('y', 430 + currentLift);

    if (stepIdx > maxStressIdx) {
      // Localized necking
      const neckFactor = Math.max(3, 8 - (normStep * 4.5));
      gaugeSec.setAttribute('width', neckFactor);
      gaugeSec.setAttribute('x', 400 - (neckFactor / 2));
      if (neckZone) {
        neckZone.setAttribute('opacity', '0.9');
        neckZone.setAttribute('fill', '#ef4444');
      }
    } else {
      gaugeSec.setAttribute('width', 8);
      gaugeSec.setAttribute('x', 396);
      if (neckZone) neckZone.setAttribute('opacity', '0.4');
    }
  }
}

function playSimulation() {
  if (isPlaying || !simData) return;
  isPlaying = true;

  const btnPlay = document.getElementById('btn-sim-play');
  if (btnPlay) {
    btnPlay.innerHTML = '<i class="fas fa-pause"></i> Pause';
    btnPlay.classList.replace('btn-lab-primary', 'btn-lab-secondary');
  }

  playInterval = setInterval(() => {
    if (currentStep < simData.readings.length - 1) {
      updateStepDisplay(currentStep + 1);
    } else {
      pauseSimulation();
    }
  }, 250);
}

function pauseSimulation() {
  isPlaying = false;
  if (playInterval) {
    clearInterval(playInterval);
    playInterval = null;
  }
  const btnPlay = document.getElementById('btn-sim-play');
  if (btnPlay) {
    btnPlay.innerHTML = '<i class="fas fa-play"></i> Start Test';
    btnPlay.classList.replace('btn-lab-secondary', 'btn-lab-primary');
  }
}

function stepSimulation(delta) {
  pauseSimulation();
  if (!simData) return;
  const target = Math.max(0, Math.min(simData.readings.length - 1, currentStep + delta));
  updateStepDisplay(target);
}

function resetVisuals() {
  pauseSimulation();
  currentStep = 0;

  const crosshead = document.getElementById('part-crosshead');
  const upperGrip = document.getElementById('part-upper-grip');
  const loadCell = document.getElementById('part-load-cell');
  const gaugeSec = document.getElementById('specimen-gauge-section');
  const actionCard = document.getElementById('sim-completion-card');

  if (crosshead) crosshead.style.transform = 'translateY(0px)';
  if (upperGrip) upperGrip.style.transform = 'translateY(0px)';
  if (loadCell) loadCell.style.transform = 'translateY(0px)';

  if (gaugeSec) {
    gaugeSec.setAttribute('height', 80);
    gaugeSec.setAttribute('y', 430);
    gaugeSec.setAttribute('width', 8);
    gaugeSec.setAttribute('x', 396);
  }

  if (actionCard) actionCard.classList.add('d-none');
}

// Transfer simulation data to analysis view
function analyzeSimulationRun() {
  if (!simData) return;
  sessionStorage.setItem('matvlab_analysis_data', JSON.stringify({
    mode: 'VIRTUAL_SIMULATION',
    material_name: simData.material_name,
    original_diameter: simData.diameter_mm,
    original_gauge_length: simData.gauge_length_mm,
    readings: simData.readings
  }));
  window.location.href = '/results';
}

document.addEventListener('DOMContentLoaded', () => {
  const btnInit = document.getElementById('btn-sim-init');
  if (btnInit) btnInit.addEventListener('click', initSimulation);

  const btnPlay = document.getElementById('btn-sim-play');
  if (btnPlay) btnPlay.addEventListener('click', () => isPlaying ? pauseSimulation() : playSimulation());

  const btnStepFwd = document.getElementById('btn-sim-step-fwd');
  if (btnStepFwd) btnStepFwd.addEventListener('click', () => stepSimulation(1));

  const btnStepBack = document.getElementById('btn-sim-step-back');
  if (btnStepBack) btnStepBack.addEventListener('click', () => stepSimulation(-1));

  const btnReset = document.getElementById('btn-sim-reset');
  if (btnReset) btnReset.addEventListener('click', () => { resetVisuals(); updateStepDisplay(0); });

  const slider = document.getElementById('sim-load-slider');
  if (slider) {
    slider.addEventListener('input', (e) => {
      pauseSimulation();
      updateStepDisplay(parseInt(e.target.value));
    });
  }

  const matSelect = document.getElementById('sim-material');
  if (matSelect) {
    matSelect.addEventListener('change', initSimulation);
  }

  const btnAnalyze = document.getElementById('btn-sim-analyze');
  if (btnAnalyze) {
    btnAnalyze.addEventListener('click', analyzeSimulationRun);
  }

  // Auto initialize on load if on simulation page
  if (document.getElementById('sim-plot')) {
    initSimulation();
  }
});
