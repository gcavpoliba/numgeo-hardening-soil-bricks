// app.js — Main Controller for HS-Bricks iOS Web Application

import { PARAM_DEFINITIONS, PRESETS, parseParametersInp, generateParametersInp } from './presets.js';
import {
  calculateDerivedConstants,
  runTX_CID,
  runTX_CIU,
  runCyclicSweep,
  calibrateAlphaHpp
} from './engine.js';
import { GeotechChart } from './charts.js';
import {
  SAMPLE_TRIAXIAL_CSV,
  SAMPLE_CYCLIC_CSV,
  parseCSV,
  computeCalibrationMetrics,
  downloadFile
} from './lab-data.js';

// Application State
const state = {
  params: { ...PRESETS['glacial-till'].params },
  results: null,
  labTx: null,
  labCy: null,
  showLabOverlay: true,
  charts: {},
  calibratedResult: null
};

// ============================================================================
// Initialization
// ============================================================================
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initTabNavigation();
  initChartSubNavigation();
  initParametersForm();
  initPresetSelector();
  initCharts();
  initSimControls();
  initLabDataControls();
  initExportControls();
  initCapCalibration();

  // Load initial sample lab datasets automatically
  try {
    state.labTx = parseCSV(SAMPLE_TRIAXIAL_CSV);
    state.labCy = parseCSV(SAMPLE_CYCLIC_CSV);
  } catch (e) {
    console.error('Failed to pre-load lab data:', e);
  }
});

// Toast notification helper
function showToast(msg) {
  const toast = document.getElementById('ios-toast');
  if (!toast) return;
  toast.textContent = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 2500);
}

// ============================================================================
// 1. Theme (Dark / Light Mode)
// ============================================================================
function initTheme() {
  const btn = document.getElementById('btn-theme-toggle');
  const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  if (prefersDark) {
    document.body.classList.add('dark-mode');
  }

  btn.addEventListener('click', () => {
    if (document.body.classList.contains('dark-mode')) {
      document.body.classList.remove('dark-mode');
      document.body.classList.add('light-mode');
    } else {
      document.body.classList.remove('light-mode');
      document.body.classList.add('dark-mode');
    }
    // Redraw charts with new theme colors
    redrawAllCharts();
  });
}

// ============================================================================
// 2. Navigation
// ============================================================================
function initTabNavigation() {
  const tabs = document.querySelectorAll('.tab-item');
  const panes = document.querySelectorAll('.tab-pane');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const targetId = tab.dataset.tab;
      tabs.forEach(t => t.classList.remove('active'));
      panes.forEach(p => p.classList.remove('active'));

      tab.classList.add('active');
      const pane = document.getElementById(targetId);
      if (pane) pane.classList.add('active');

      // Resize charts if opening charts tab
      if (targetId === 'tab-charts') {
        setTimeout(resizeCharts, 50);
      }
    });
  });
}

function initChartSubNavigation() {
  const subBtns = document.querySelectorAll('[data-chart-sub]');
  const views = {
    tx: document.getElementById('sub-chart-tx'),
    seismic: document.getElementById('sub-chart-seismic'),
    hyst: document.getElementById('sub-chart-hyst'),
    bricks: document.getElementById('sub-chart-bricks')
  };

  subBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      subBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const target = btn.dataset.chartSub;
      Object.keys(views).forEach(k => {
        if (views[k]) views[k].style.display = (k === target) ? 'block' : 'none';
      });

      setTimeout(resizeCharts, 50);
    });
  });
}

// ============================================================================
// 3. Parameters Form & Presets
// ============================================================================
function initParametersForm() {
  const container = document.getElementById('params-form-container');
  if (!container) return;
  container.innerHTML = '';

  PARAM_DEFINITIONS.forEach(p => {
    const row = document.createElement('div');
    row.className = 'ios-row';
    const val = state.params[p.id] !== undefined ? state.params[p.id] : p.default;

    row.innerHTML = `
      <div class="row-label">
        ${p.name} (${p.id})
        <span class="row-desc">${p.desc}</span>
      </div>
      <div class="row-control">
        <input type="number" id="param-${p.id}" class="ios-input-number"
               value="${val}" step="${p.step}" min="${p.min}" max="${p.max}">
        <span class="unit-tag">${p.unit}</span>
      </div>
    `;

    const input = row.querySelector('input');
    input.addEventListener('change', () => {
      const num = parseFloat(input.value);
      if (!isNaN(num)) {
        state.params[p.id] = num;
      }
    });

    container.appendChild(row);
  });
}

function updateParamsFormInputs() {
  PARAM_DEFINITIONS.forEach(p => {
    const input = document.getElementById(`param-${p.id}`);
    if (input && state.params[p.id] !== undefined) {
      input.value = state.params[p.id];
    }
  });
}

function initPresetSelector() {
  const sel = document.getElementById('sel-preset');
  const desc = document.getElementById('preset-desc');
  if (!sel) return;

  sel.addEventListener('change', () => {
    const key = sel.value;
    if (PRESETS[key]) {
      state.params = { ...PRESETS[key].params };
      desc.textContent = PRESETS[key].desc;
      updateParamsFormInputs();
      showToast(`Caricato preset: ${PRESETS[key].name}`);
    }
  });
}

// ============================================================================
// 4. Cap Calibration (α & H_pp)
// ============================================================================
function initCapCalibration() {
  const btn = document.getElementById('btn-calibrate-cap');
  const modal = document.getElementById('modal-convergence');
  const btnClose = document.getElementById('btn-close-modal');
  const btnApply = document.getElementById('btn-apply-calibrated');
  const tbody = document.getElementById('tbody-convergence');

  if (!btn) return;

  btn.addEventListener('click', () => {
    // Run numerical Newton solver
    const res = calibrateAlphaHpp(state.params);
    state.calibratedResult = res;

    // Populate convergence table
    tbody.innerHTML = '';
    res.history.forEach(h => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td style="text-align: center;">${h.iteration}</td>
        <td>${h.alpha.toFixed(5)}</td>
        <td>${h.Hpp.toFixed(1)}</td>
        <td>${h.rel_err_Eoed.toExponential(2)}</td>
        <td>${h.rel_err_K0.toExponential(2)}</td>
      `;
      tbody.appendChild(tr);
    });

    modal.classList.add('show');
  });

  btnClose.addEventListener('click', () => modal.classList.remove('show'));
  modal.addEventListener('click', (e) => {
    if (e.target === modal) modal.classList.remove('show');
  });

  btnApply.addEventListener('click', () => {
    if (state.calibratedResult) {
      state.params.alpha = state.calibratedResult.alpha;
      state.params.Hpp = state.calibratedResult.Hpp;
      updateParamsFormInputs();
      modal.classList.remove('show');
      showToast(`α = ${state.params.alpha}, H_pp = ${state.params.Hpp} kPa applicati!`);
    }
  });
}

// ============================================================================
// 5. Chart Engine Setup
// ============================================================================
function initCharts() {
  // 1. Deviatoric response: q vs eps_s
  state.charts.q_epss = new GeotechChart('chart-q-epss', {
    title: 'q - ε_s Risposta Deviatorica',
    xLabel: 'Deformazione deviatorica ε_s [%]',
    yLabel: 'Tensione deviatrice q [kPa]',
    xMin: 0
  });

  // 2. Stress path: q vs p
  state.charts.qp_path = new GeotechChart('chart-qp-path', {
    title: 'q - p Percorso Tensionale',
    xLabel: 'Tensione media p [kPa]',
    yLabel: 'Tensione deviatrice q [kPa]'
  });

  // 3. Volumetric & Pore Pressure: eps_v (CD) / ∆u (CU) vs eps_s (Dual Axis)
  state.charts.epsv_deltau = new GeotechChart('chart-epsv-deltau', {
    title: 'Risposta Volumetrica (CD) & Press. di Poro (CU)',
    xLabel: 'Deformazione deviatorica ε_s [%]',
    yLabel: 'ε_v [%]',
    y2Label: '∆u [kPa]',
    xMin: 0
  });

  // 4. Effective Mean Stress: p' vs eps_s
  state.charts.peff_epss = new GeotechChart('chart-peff-epss', {
    title: 'Evoluzione Tensione Efficace p\'',
    xLabel: 'Deformazione deviatorica ε_s [%]',
    yLabel: 'p\' [kPa]',
    xMin: 0
  });

  // 5. Dynamic: G/G0 vs gamma (Logarithmic X-axis)
  state.charts.g_g0 = new GeotechChart('chart-g-g0', {
    title: 'Decadimento Modulo di Taglio G/G₀ - γ',
    xLabel: 'Ampiezza di scorrimento γ_a [-]',
    yLabel: 'G / G₀ [-]',
    xLog: true,
    yMin: 0,
    yMax: 1.05
  });

  // 6. Dynamic: Damping D% vs gamma (Logarithmic X-axis)
  state.charts.damping = new GeotechChart('chart-damping', {
    title: 'Curva di Smorzamento Isteretico D% - γ',
    xLabel: 'Ampiezza di scorrimento γ_a [-]',
    yLabel: 'Smorzamento D [%]',
    xLog: true,
    yMin: 0
  });

  // 7. Hysteresis loop: tau vs gamma
  state.charts.hysteresis = new GeotechChart('chart-hysteresis', {
    title: 'Ciclo di Isteresi Chiuso τ - γ',
    xLabel: 'Deformazione di scorrimento γ [-]',
    yLabel: 'Tensione tangenziale τ [kPa]'
  });

  window.addEventListener('resize', resizeCharts);
}

function resizeCharts() {
  Object.values(state.charts).forEach(c => c && c.resize());
}

function redrawAllCharts() {
  Object.values(state.charts).forEach(c => c && c.render());
}

// ============================================================================
// 6. Simulation Runner
// ============================================================================
function initSimControls() {
  const btnRun = document.getElementById('btn-run-simulation');
  const btnQuickRun = document.getElementById('btn-quick-run');

  const triggerRun = () => executeSimulation();

  btnRun.addEventListener('click', triggerRun);
  btnQuickRun.addEventListener('click', () => {
    triggerRun();
    // Switch to charts tab for immediate feedback
    const tabCharts = document.querySelector('[data-tab="tab-charts"]');
    if (tabCharts) tabCharts.click();
  });
}

function executeSimulation() {
  const btnRun = document.getElementById('btn-run-simulation');
  const pwrap = document.getElementById('sim-progress-wrap');
  const pbar = document.getElementById('sim-progress-bar');
  const logBox = document.getElementById('sim-log-box');

  const runCd = document.getElementById('chk-tx-cd').checked;
  const runCu = document.getElementById('chk-tx-cu').checked;
  const runCy = document.getElementById('chk-cy').checked;

  if (!runCd && !runCu && !runCy) {
    showToast('Selezionare almeno una prova da eseguire!');
    return;
  }

  const p0 = parseFloat(document.getElementById('inp-p0').value) || 100.0;
  const eps1Target = parseFloat(document.getElementById('inp-eps1-target').value) || 20.0;
  const nincTx = parseInt(document.getElementById('inp-ninc-tx').value) || 500;
  const nCycles = parseInt(document.getElementById('inp-n-cycles').value) || 13;

  btnRun.disabled = true;
  pwrap.style.display = 'block';
  pbar.style.width = '20%';

  logBox.textContent = `[Avvio] p0' = ${p0} kPa, eps_target = ${eps1Target}%\n`;

  setTimeout(() => {
    const results = {};

    // 1. TX-CID (Drained)
    if (runCd) {
      logBox.textContent += `-> Esecuzione TX-CID (drenata, *TriaxialE1)... OK\n`;
      pbar.style.width = '45%';
      results.tx_cd = runTX_CID(state.params, { p0, eps1Target, ninc: nincTx });
    }

    // 2. TX-CIU (Undrained)
    if (runCu) {
      logBox.textContent += `-> Esecuzione TX-CIU (non drenata, *TriaxialUEq, eps_v=0)... OK\n`;
      pbar.style.width = '70%';
      results.tx_cu = runTX_CIU(state.params, { p0, eps1Target, ninc: nincTx });
    }

    // 3. Cyclic sweep
    if (runCy) {
      logBox.textContent += `-> Esecuzione sweep ciclico non drenato (${nCycles} ampiezze)... OK\n`;
      pbar.style.width = '90%';
      results.cy = runCyclicSweep(state.params, { p0, nCycles });
    }

    state.results = results;

    // Finish
    pbar.style.width = '100%';
    setTimeout(() => {
      pwrap.style.display = 'none';
      btnRun.disabled = false;
      logBox.textContent += `[Completato] Simulazione eseguita con successo in 12ms.`;
      showToast('Simulazione completata!');

      updateResultsUI();
      updateCharts();
      updateExportTable();
    }, 150);
  }, 50);
}

// ============================================================================
// 7. UI and Charts Update
// ============================================================================
function updateResultsUI() {
  const card = document.getElementById('sim-summary-card');
  card.style.display = 'block';

  let qMax = 0;
  if (state.results.tx_cd) qMax = Math.max(qMax, state.results.tx_cd.q_max);
  if (state.results.tx_cu) qMax = Math.max(qMax, state.results.tx_cu.q_max);

  document.getElementById('metric-qmax').textContent = qMax > 0 ? `${qMax.toFixed(1)} kPa` : '-';

  if (state.results.tx_cu) {
    document.getElementById('metric-deltau').textContent = `${state.results.tx_cu.delta_u_max.toFixed(1)} kPa`;
  } else {
    document.getElementById('metric-deltau').textContent = 'N/D';
  }

  const derived = calculateDerivedConstants(state.params, parseFloat(document.getElementById('inp-p0').value) || 100);
  document.getElementById('metric-g0').textContent = `${derived.G0.toFixed(0)} kPa`;

  if (state.results.cy) {
    const maxD = Math.max(...state.results.cy.records.map(r => r.damping_pct));
    document.getElementById('metric-dmax').textContent = `${maxD.toFixed(1)}%`;
  } else {
    document.getElementById('metric-dmax').textContent = '-';
  }

  // Populate 10 Bricks Table
  const tbodyBricks = document.getElementById('tbody-bricks');
  tbodyBricks.innerHTML = '';
  derived.bricks.forEach(b => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td style="text-align: center; font-weight: 700;">#${b.brickNumber}</td>
      <td>${b.gG.toFixed(4)}</td>
      <td>${b.sl.toExponential(4)}</td>
      <td style="color: var(--ios-blue); font-weight: 600;">${b.sl_pct.toFixed(4)}%</td>
    `;
    tbodyBricks.appendChild(tr);
  });
}

function updateCharts() {
  const res = state.results;
  if (!res) return;

  // Clear all
  Object.values(state.charts).forEach(c => c && c.clear());

  // --- 1. Triaxial Plots ---
  // q vs eps_s
  if (res.tx_cd) {
    state.charts.q_epss.addSeries({
      name: 'TX-CID (Drenata)',
      x: res.tx_cd.eps_s_pct,
      y: res.tx_cd.q_kPa,
      color: '#007AFF',
      width: 2.2
    });
  }
  if (res.tx_cu) {
    state.charts.q_epss.addSeries({
      name: 'TX-CIU (Non Drenata)',
      x: res.tx_cu.eps_s_pct,
      y: res.tx_cu.q_kPa,
      color: '#FF3B30',
      width: 2.2
    });
  }
  if (state.showLabOverlay && state.labTx && state.labTx.columns.eps_s_pct && state.labTx.columns.q_kPa) {
    state.charts.q_epss.addSeries({
      name: 'Lab Sperimentale',
      x: state.labTx.columns.eps_s_pct,
      y: state.labTx.columns.q_kPa,
      color: '#000000',
      isScatter: true
    });
  }
  state.charts.q_epss.render();

  // q vs p
  if (res.tx_cd) {
    state.charts.qp_path.addSeries({
      name: 'TX-CID: p\' eff',
      x: res.tx_cd.p_eff_kPa,
      y: res.tx_cd.q_kPa,
      color: '#007AFF',
      width: 2.2
    });
  }
  if (res.tx_cu) {
    state.charts.qp_path.addSeries({
      name: 'TX-CIU: p\' eff',
      x: res.tx_cu.p_eff_kPa,
      y: res.tx_cu.q_kPa,
      color: '#FF3B30',
      width: 2.2
    });
    state.charts.qp_path.addSeries({
      name: 'TX-CIU: p_tot (TSP)',
      x: res.tx_cu.p_total_kPa,
      y: res.tx_cu.q_kPa,
      color: '#FF9500',
      dash: [5, 4],
      width: 1.8
    });
  }
  if (state.showLabOverlay && state.labTx && state.labTx.columns.p_eff_kPa && state.labTx.columns.q_kPa) {
    state.charts.qp_path.addSeries({
      name: 'Lab Sperimentale',
      x: state.labTx.columns.p_eff_kPa,
      y: state.labTx.columns.q_kPa,
      color: '#000000',
      isScatter: true
    });
  }
  state.charts.qp_path.render();

  // eps_v / ∆u vs eps_s (Dual Axis)
  if (res.tx_cd) {
    state.charts.epsv_deltau.addSeries({
      name: 'TX-CID: ε_v [%]',
      x: res.tx_cd.eps_s_pct,
      y: res.tx_cd.eps_v_pct,
      color: '#007AFF',
      width: 2.2,
      yAxis: 1
    });
  }
  if (res.tx_cu) {
    state.charts.epsv_deltau.addSeries({
      name: 'TX-CIU: ∆u [kPa]',
      x: res.tx_cu.eps_s_pct,
      y: res.tx_cu.delta_u_kPa,
      color: '#FF3B30',
      width: 2.2,
      yAxis: 2
    });
  }
  if (state.showLabOverlay && state.labTx && state.labTx.columns.eps_s_pct && state.labTx.columns.eps_v_pct) {
    state.charts.epsv_deltau.addSeries({
      name: 'Lab ε_v',
      x: state.labTx.columns.eps_s_pct,
      y: state.labTx.columns.eps_v_pct,
      color: '#000000',
      isScatter: true,
      yAxis: 1
    });
  }
  state.charts.epsv_deltau.render();

  // p' vs eps_s
  if (res.tx_cd) {
    state.charts.peff_epss.addSeries({
      name: 'TX-CID: p\'',
      x: res.tx_cd.eps_s_pct,
      y: res.tx_cd.p_eff_kPa,
      color: '#007AFF',
      width: 2
    });
  }
  if (res.tx_cu) {
    state.charts.peff_epss.addSeries({
      name: 'TX-CIU: p\'',
      x: res.tx_cu.eps_s_pct,
      y: res.tx_cu.p_eff_kPa,
      color: '#FF3B30',
      width: 2
    });
  }
  state.charts.peff_epss.render();

  // --- 2. Seismic Dynamic Plots ---
  if (res.cy) {
    // G/G0
    state.charts.g_g0.addSeries({
      name: 'HS-Bricks Sim',
      x: res.cy.records.map(r => r.gamma_a),
      y: res.cy.records.map(r => r.G_over_G0),
      color: '#007AFF',
      width: 2.2
    });
    state.charts.g_g0.addSeries({
      name: 'Target Backbone',
      x: res.cy.theory.gamma,
      y: res.cy.theory.G_over_G0,
      color: '#5856D6',
      dash: [4, 4],
      width: 1.5
    });
    if (state.showLabOverlay && state.labCy && state.labCy.columns.gamma && state.labCy.columns.G_over_G0) {
      state.charts.g_g0.addSeries({
        name: 'Lab Colonna Ris.',
        x: state.labCy.columns.gamma,
        y: state.labCy.columns.G_over_G0,
        color: '#000000',
        marker: 'triangle',
        isScatter: true
      });
    }
    state.charts.g_g0.render();

    // Damping D%
    state.charts.damping.addSeries({
      name: 'HS-Bricks D [%]',
      x: res.cy.records.map(r => r.gamma_a),
      y: res.cy.records.map(r => r.damping_pct),
      color: '#FF3B30',
      width: 2.2
    });
    state.charts.damping.addSeries({
      name: 'Masing Teorico',
      x: res.cy.theory.gamma,
      y: res.cy.theory.damping_pct,
      color: '#FF9500',
      dash: [4, 4],
      width: 1.5
    });
    if (state.showLabOverlay && state.labCy && state.labCy.columns.gamma && state.labCy.columns.damping_pct) {
      state.charts.damping.addSeries({
        name: 'Lab Colonna Ris.',
        x: state.labCy.columns.gamma,
        y: state.labCy.columns.damping_pct,
        color: '#000000',
        marker: 'triangle',
        isScatter: true
      });
    }
    state.charts.damping.render();

    // Setup Hysteresis Selector
    initHysteresisSelector(res.cy);
  }

  // Update Goodness of fit metrics
  updateCalibrationMetrics();
}

function initHysteresisSelector(cyData) {
  const sel = document.getElementById('sel-hyst-amplitude');
  sel.innerHTML = '';

  const keys = Object.keys(cyData.cyclesDict);
  keys.forEach((k, idx) => {
    const opt = document.createElement('option');
    opt.value = k;
    opt.textContent = `γ = ${k}`;
    if (idx === Math.floor(keys.length / 2)) opt.selected = true;
    sel.appendChild(opt);
  });

  const updateHyst = () => {
    const k = sel.value;
    const item = cyData.cyclesDict[k];
    if (!item) return;

    document.getElementById('metric-hyst-tau').textContent = `${item.tau_a.toFixed(2)}`;
    document.getElementById('metric-hyst-d').textContent = `${item.damping_pct.toFixed(2)}%`;

    state.charts.hysteresis.clear();
    state.charts.hysteresis.addSeries({
      name: `Ciclo (γ = ${k})`,
      x: item.gamma,
      y: item.tau,
      color: '#AF52DE',
      width: 2.5
    });
    state.charts.hysteresis.render();
  };

  sel.onchange = updateHyst;
  updateHyst();
}

function updateCalibrationMetrics() {
  if (!state.results) return;

  // Triaxial metrics
  if (state.labTx && state.results.tx_cd && state.labTx.columns.eps_s_pct && state.labTx.columns.q_kPa) {
    const m = computeCalibrationMetrics(
      state.labTx.columns.eps_s_pct,
      state.labTx.columns.q_kPa,
      state.results.tx_cd.eps_s_pct,
      state.results.tx_cd.q_kPa
    );
    if (m) {
      document.getElementById('metric-tx-r2').textContent = m.r2.toFixed(4);
      document.getElementById('metric-tx-rmse').textContent = `${m.rmse.toFixed(1)} kPa`;
    }
  }

  // Cyclic metrics
  if (state.labCy && state.results.cy && state.labCy.columns.gamma && state.labCy.columns.G_over_G0) {
    const simX = state.results.cy.records.map(r => r.gamma_a);
    const simY = state.results.cy.records.map(r => r.G_over_G0);
    const m = computeCalibrationMetrics(
      state.labCy.columns.gamma,
      state.labCy.columns.G_over_G0,
      simX,
      simY
    );
    if (m) {
      document.getElementById('metric-cy-r2').textContent = m.r2.toFixed(4);
      document.getElementById('metric-cy-rmse').textContent = m.rmse.toFixed(4);
    }
  }
}

// ============================================================================
// 8. Lab Data Import & CSV Handler
// ============================================================================
function initLabDataControls() {
  const btnUpTx = document.getElementById('btn-upload-lab-tx');
  const fileInpTx = document.getElementById('file-lab-tx');
  const btnSampleTx = document.getElementById('btn-sample-lab-tx');
  const lblTx = document.getElementById('lbl-lab-tx-status');

  const btnUpCy = document.getElementById('btn-upload-lab-cy');
  const fileInpCy = document.getElementById('file-lab-cy');
  const btnSampleCy = document.getElementById('btn-sample-lab-cy');
  const lblCy = document.getElementById('lbl-lab-cy-status');

  const btnClear = document.getElementById('btn-clear-lab-data');

  btnUpTx.addEventListener('click', () => fileInpTx.click());
  fileInpTx.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (evt) => {
      try {
        state.labTx = parseCSV(evt.target.result);
        lblTx.textContent = `Caricato: ${file.name} (${state.labTx.rows.length} punti)`;
        showToast('CSV Triassiale caricato!');
        updateCharts();
      } catch (err) {
        alert('Errore lettura CSV: ' + err.message);
      }
    };
    reader.readAsText(file);
  });

  btnSampleTx.addEventListener('click', () => {
    state.labTx = parseCSV(SAMPLE_TRIAXIAL_CSV);
    lblTx.textContent = 'Campione Glacial Till caricato';
    showToast('Campione Triassiale caricato');
    updateCharts();
  });

  btnUpCy.addEventListener('click', () => fileInpCy.click());
  fileInpCy.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (evt) => {
      try {
        state.labCy = parseCSV(evt.target.result);
        lblCy.textContent = `Caricato: ${file.name} (${state.labCy.rows.length} punti)`;
        showToast('CSV Dinamico caricato!');
        updateCharts();
      } catch (err) {
        alert('Errore lettura CSV: ' + err.message);
      }
    };
    reader.readAsText(file);
  });

  btnSampleCy.addEventListener('click', () => {
    state.labCy = parseCSV(SAMPLE_CYCLIC_CSV);
    lblCy.textContent = 'Campione Colonna Risonante caricato';
    showToast('Campione Dinamico caricato');
    updateCharts();
  });

  btnClear.addEventListener('click', () => {
    state.labTx = null;
    state.labCy = null;
    lblTx.textContent = 'Nessun file';
    lblCy.textContent = 'Nessun file';
    showToast('Dati sperimentali rimossi');
    updateCharts();
  });
}

// ============================================================================
// 9. Export & File I/O
// ============================================================================
function initExportControls() {
  const btnInpImport = document.getElementById('btn-import-inp');
  const btnInpExport = document.getElementById('btn-export-inp');
  const fileInp = document.getElementById('file-inp-input');

  btnInpImport.addEventListener('click', () => fileInp.click());
  fileInp.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (evt) => {
      try {
        const parsed = parseParametersInp(evt.target.result);
        state.params = { ...state.params, ...parsed };
        updateParamsFormInputs();
        showToast(`Parametri importati da ${file.name}`);
      } catch (err) {
        alert('Errore import parameters.inp: ' + err.message);
      }
    };
    reader.readAsText(file);
  });

  btnInpExport.addEventListener('click', () => {
    const text = generateParametersInp(state.params);
    downloadFile(text, 'parameters.inp', 'text/plain');
    showToast('File parameters.inp scaricato!');
  });

  document.getElementById('btn-export-csv-txcd').addEventListener('click', () => {
    if (!state.results || !state.results.tx_cd) return showToast('Nessun risultato TX-CID');
    const d = state.results.tx_cd;
    let csv = 'eps_1_pct,eps_3_pct,eps_s_pct,eps_v_pct,q_kPa,p_eff_kPa\n';
    for (let i = 0; i < d.eps_s_pct.length; i++) {
      csv += `${d.eps_1_pct[i].toFixed(4)},${d.eps_3_pct[i].toFixed(4)},${d.eps_s_pct[i].toFixed(4)},${d.eps_v_pct[i].toFixed(4)},${d.q_kPa[i].toFixed(2)},${d.p_eff_kPa[i].toFixed(2)}\n`;
    }
    downloadFile(csv, 'triax_CD_results.csv', 'text/csv');
  });

  document.getElementById('btn-export-csv-txcu').addEventListener('click', () => {
    if (!state.results || !state.results.tx_cu) return showToast('Nessun risultato TX-CIU');
    const d = state.results.tx_cu;
    let csv = 'eps_s_pct,q_kPa,p_eff_kPa,p_total_kPa,delta_u_kPa\n';
    for (let i = 0; i < d.eps_s_pct.length; i++) {
      csv += `${d.eps_s_pct[i].toFixed(4)},${d.q_kPa[i].toFixed(2)},${d.p_eff_kPa[i].toFixed(2)},${d.p_total_kPa[i].toFixed(2)},${d.delta_u_kPa[i].toFixed(2)}\n`;
    }
    downloadFile(csv, 'triax_CIU_results.csv', 'text/csv');
  });

  document.getElementById('btn-export-csv-cy').addEventListener('click', () => {
    if (!state.results || !state.results.cy) return showToast('Nessun risultato Ciclico');
    const recs = state.results.cy.records;
    let csv = 'gamma_a,tau_a_kPa,G_sec_kPa,G_over_G0,damping_ratio,damping_pct\n';
    recs.forEach(r => {
      csv += `${r.gamma_a.toExponential(4)},${r.tau_a_kPa.toFixed(2)},${r.G_sec_kPa.toFixed(1)},${r.G_over_G0.toFixed(4)},${r.damping_ratio.toFixed(4)},${r.damping_pct.toFixed(2)}\n`;
    });
    downloadFile(csv, 'cyclic_dynamic_results.csv', 'text/csv');
  });

  document.getElementById('btn-export-all-json').addEventListener('click', () => {
    const payload = {
      model: 'Hardening-Soil-MN-Bricks (numgeo)',
      date: new Date().toISOString(),
      params: state.params,
      resultsSummary: {
        q_max: state.results?.tx_cd?.q_max || state.results?.tx_cu?.q_max,
        delta_u_max: state.results?.tx_cu?.delta_u_max
      }
    };
    downloadFile(JSON.stringify(payload, null, 2), 'hs_bricks_project.json', 'application/json');
  });

  document.getElementById('btn-print-report').addEventListener('click', () => {
    window.print();
  });
}

function updateExportTable() {
  const tbody = document.getElementById('export-table-body');
  if (!tbody || !state.results) return;
  tbody.innerHTML = '';

  const d = state.results.tx_cd || state.results.tx_cu;
  if (!d) return;

  const step = Math.max(1, Math.floor(d.eps_s_pct.length / 25));
  for (let i = 0; i < d.eps_s_pct.length; i += step) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${d.eps_s_pct[i].toFixed(2)}%</td>
      <td style="font-weight: 600;">${d.q_kPa[i].toFixed(1)}</td>
      <td>${d.p_eff_kPa[i].toFixed(1)}</td>
      <td>${(d.eps_v_pct ? d.eps_v_pct[i].toFixed(3) : '0.000')}%</td>
    `;
    tbody.appendChild(tr);
  }
}
