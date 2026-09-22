/**
 * TypeSafe DocEval — Soft SaaS Dashboard Application Logic
 */

document.addEventListener('DOMContentLoaded', () => {
  // App State
  const state = {
    presets: {},
    dimensionsMeta: [],
    samples: [],
    currentPreset: 'general',
    weights: {
      clarity: 0.25,
      completeness: 0.25,
      actionability: 0.25,
      technical_depth: 0.25,
    },
    lastResult: null,
    isEvaluating: false,
  };

  // DOM Elements
  const presetGrid = document.getElementById('preset-grid');
  const toggleWeightsBtn = document.getElementById('toggle-weights-btn');
  const customWeightsDrawer = document.getElementById('custom-weights-drawer');
  const samplesPills = document.getElementById('samples-pills');
  const docTitleInput = document.getElementById('doc-title-input');
  const docContentTextarea = document.getElementById('doc-content-textarea');
  const statWords = document.getElementById('stat-words');
  const statLines = document.getElementById('stat-lines');
  const fileUploadInput = document.getElementById('file-upload-input');
  const editorContainer = document.getElementById('editor-container');
  const dropOverlay = document.getElementById('drop-overlay');
  const evaluateBtn = document.getElementById('evaluate-btn');
  const evaluateSpinner = document.getElementById('evaluate-spinner');
  const evaluateIcon = document.getElementById('evaluate-icon');
  const evaluateBtnText = document.getElementById('evaluate-btn-text');
  const resultsSection = document.getElementById('results-section');
  const resultsDocTitle = document.getElementById('results-doc-title');
  const overallScoreDisplay = document.getElementById('overall-score-display');
  const overallProgressBar = document.getElementById('overall-progress-bar');
  const qualityBadge = document.getElementById('quality-badge');
  const tPreset = document.getElementById('t-preset');
  const tTokens = document.getElementById('t-tokens');
  const gateStatusText = document.getElementById('gate-status-text');
  const qualityGateNotice = document.getElementById('quality-gate-notice');
  const gateNoticeIcon = document.getElementById('gate-notice-icon');
  const gateMsg = document.getElementById('gate-msg');
  const dimensionCardsGrid = document.getElementById('dimension-cards-grid');
  const copyMarkdownBtn = document.getElementById('copy-markdown-btn');
  const downloadCsvBtn = document.getElementById('download-csv-btn');
  const copyJsonBtn = document.getElementById('copy-json-btn');
  const toastContainer = document.getElementById('toast-container');
  const refreshSamplesBtn = document.getElementById('refresh-samples-btn');

  // Sliders & Quality Inputs
  const weightInputs = {
    clarity: document.getElementById('weight-clarity'),
    completeness: document.getElementById('weight-completeness'),
    actionability: document.getElementById('weight-actionability'),
    technical_depth: document.getElementById('weight-technical_depth'),
  };
  const weightVals = {
    clarity: document.getElementById('weight-val-clarity'),
    completeness: document.getElementById('weight-val-completeness'),
    actionability: document.getElementById('weight-val-actionability'),
    technical_depth: document.getElementById('weight-val-technical_depth'),
  };
  const gateFailUnder = document.getElementById('gate-fail-under');
  const gateMinClarity = document.getElementById('gate-min-clarity');
  const gateMinDepth = document.getElementById('gate-min-depth');


  // Initialize
  init();

  async function init() {
    setupEventListeners();
    await loadPresets();
    await loadSamples();
    updateDocStats();
  }

  function setupEventListeners() {
    if (refreshSamplesBtn) {
      refreshSamplesBtn.addEventListener('click', async () => {
        showToast('Syncing sample documents...');
        await loadSamples();
      });
    }

    // Preset cards click
    presetGrid.querySelectorAll('.preset-card').forEach(card => {
      card.addEventListener('click', () => {
        selectPreset(card.dataset.preset);
      });
      card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          selectPreset(card.dataset.preset);
        }
      });
    });

    // Toggle custom weights drawer
    toggleWeightsBtn.addEventListener('click', toggleDrawer);

    // Weight sliders
    Object.keys(weightInputs).forEach(dimId => {
      if (weightInputs[dimId]) {
        weightInputs[dimId].addEventListener('input', (e) => {
          const val = parseFloat(e.target.value);
          state.weights[dimId] = val;
          if (weightVals[dimId]) {
            weightVals[dimId].textContent = val.toFixed(2);
          }
        });
      }
    });

    // Document text & stats
    docContentTextarea.addEventListener('input', updateDocStats);

    // Keyboard shortcut: Cmd/Ctrl + Enter to evaluate
    document.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault();
        runEvaluation();
      }
    });

    // File drag & drop
    ['dragenter', 'dragover'].forEach(name => {
      editorContainer.addEventListener(name, (e) => {
        e.preventDefault();
        dropOverlay.classList.remove('hidden');
      });
    });
    ['dragleave', 'drop'].forEach(name => {
      editorContainer.addEventListener(name, (e) => {
        e.preventDefault();
        dropOverlay.classList.add('hidden');
      });
    });
    editorContainer.addEventListener('drop', (e) => {
      const files = e.dataTransfer.files;
      if (files && files[0]) {
        handleFile(files[0]);
      }
    });

    // File upload input
    fileUploadInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files[0]) {
        handleFile(e.target.files[0]);
      }
    });

    // Evaluate button
    evaluateBtn.addEventListener('click', runEvaluation);

    // Export buttons
    copyMarkdownBtn.addEventListener('click', copyMarkdownPRTable);
    downloadCsvBtn.addEventListener('click', downloadCSV);
    copyJsonBtn.addEventListener('click', copyJSON);
  }

  function toggleDrawer() {
    const isHidden = customWeightsDrawer.classList.toggle('hidden');
    toggleWeightsBtn.setAttribute('aria-expanded', !isHidden);
    const arrow = toggleWeightsBtn.querySelector('svg');
    if (arrow) {
      arrow.style.transform = isHidden ? 'rotate(0deg)' : 'rotate(180deg)';
      arrow.style.transition = 'transform 200ms ease';
    }
  }

  // Load Presets
  async function loadPresets() {
    try {
      const res = await fetch('/api/presets');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      state.presets = data.presets;
      state.dimensionsMeta = data.dimensions;
    } catch (err) {
      console.warn('Failed to load presets, using defaults:', err);
    }
  }

  // Load Samples
  async function loadSamples() {
    try {
      const res = await fetch('/api/samples');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      state.samples = data.samples || [];
      renderSamplePills();
    } catch (err) {
      samplesPills.innerHTML = '<span class="hint-text">Could not load sample files.</span>';
      console.warn('Failed to load samples:', err);
    }
  }

  function renderSamplePills() {
    if (!state.samples.length) {
      samplesPills.innerHTML = '<span class="hint-text">No samples found in repository.</span>';
      return;
    }

    samplesPills.innerHTML = '';
    state.samples.forEach((sample, idx) => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = `sample-chip ${idx === 0 ? 'active' : ''}`;
      chip.id = `sample-pill-${idx}`;
      chip.textContent = `${sample.name} · ${sample.word_count}w`;
      chip.addEventListener('click', () => {
        selectSample(sample, chip);
      });
      samplesPills.appendChild(chip);
    });

    // Auto-select first sample
    if (state.samples.length > 0) {
      selectSample(state.samples[0], samplesPills.children[0]);
    }
  }

  function selectSample(sample, chipElement) {
    samplesPills.querySelectorAll('.sample-chip').forEach(p => p.classList.remove('active'));
    if (chipElement) chipElement.classList.add('active');

    docTitleInput.value = sample.title || sample.name;
    docContentTextarea.value = sample.text;
    updateDocStats();

    // Auto-select best preset
    if (sample.name.includes('api')) {
      selectPreset('api-spec');
    } else if (sample.name.includes('onboarding')) {
      selectPreset('onboarding');
    } else if (sample.name.includes('rfc')) {
      selectPreset('rfc');
    }
  }

  function selectPreset(presetKey) {
    state.currentPreset = presetKey;
    presetGrid.querySelectorAll('.preset-card').forEach(card => {
      const isActive = card.dataset.preset === presetKey;
      card.classList.toggle('active', isActive);
      card.setAttribute('aria-checked', isActive);
    });

    if (state.presets[presetKey]) {
      const pWeights = state.presets[presetKey];
      Object.keys(pWeights).forEach(dimId => {
        state.weights[dimId] = pWeights[dimId];
        if (weightInputs[dimId]) {
          weightInputs[dimId].value = pWeights[dimId];
        }
        if (weightVals[dimId]) {
          weightVals[dimId].textContent = pWeights[dimId].toFixed(2);
        }
      });
    }
    tPreset.textContent = presetKey.charAt(0).toUpperCase() + presetKey.slice(1);
  }

  function handleFile(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      docContentTextarea.value = e.target.result;
      const cleanTitle = file.name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');
      docTitleInput.value = cleanTitle.charAt(0).toUpperCase() + cleanTitle.slice(1);
      updateDocStats();
      showToast(`Loaded ${file.name}`);
    };
    reader.readAsText(file);
  }

  function updateDocStats() {
    const text = docContentTextarea.value;
    const words = text.trim() ? text.trim().split(/\s+/).length : 0;
    const lines = text.split('\n').length;
    statWords.textContent = `${words} words`;
    statLines.textContent = `${lines} lines`;
  }

  // Run Evaluation
  async function runEvaluation() {
    if (state.isEvaluating) return;
    const text = docContentTextarea.value.trim();
    if (!text) {
      showToast('Please enter document content or select a sample', 'error');
      docContentTextarea.focus();
      return;
    }

    setEvaluatingState(true);

    const payload = {
      text: text,
      title: docTitleInput.value.trim() || 'Untitled Document',
      filename: `${(docTitleInput.value.trim() || 'doc').toLowerCase().replace(/\s+/g, '-')}.md`,
      preset: state.currentPreset,
      weights: state.weights,
    };

    try {
      const res = await fetch('/api/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || `Evaluation failed with HTTP ${res.status}`);
      }

      const data = await res.json();
      state.lastResult = data;
      renderResults(data);
      showToast('Evaluation completed');
      resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setEvaluatingState(false);
    }
  }

  function setEvaluatingState(loading) {
    state.isEvaluating = loading;
    evaluateBtn.disabled = loading;
    evaluateSpinner.classList.toggle('hidden', !loading);
    evaluateIcon.classList.toggle('hidden', loading);
    evaluateBtnText.textContent = loading ? 'Evaluating...' : 'Evaluate Document';
  }

  // Render Evaluation Results
  function renderResults(data) {
    const res = data.result;
    const dims = data.dimensions;
    const docMeta = data.document;

    resultsSection.classList.remove('hidden');
    resultsDocTitle.textContent = `${docMeta.title} (${docMeta.word_count} words)`;

    // 1. Executive Overall Score
    const overall = res.overall;
    overallScoreDisplay.textContent = overall.toFixed(3);
    const overallPct = Math.round(overall * 100);
    overallProgressBar.style.width = `${overallPct}%`;

    // Quality Gate Thresholds
    const failUnderVal = parseFloat(gateFailUnder.value);
    let passed = true;
    let gateViolations = [];

    if (!isNaN(failUnderVal) && overall < failUnderVal) {
      passed = false;
      gateViolations.push(`Overall (${overall.toFixed(3)}) is below required ${failUnderVal.toFixed(3)}`);
    }

    const minClarityVal = parseFloat(gateMinClarity.value);
    if (!isNaN(minClarityVal) && res.dimensions.clarity && res.dimensions.clarity.score < minClarityVal) {
      passed = false;
      gateViolations.push(`Clarity (${res.dimensions.clarity.score.toFixed(2)}) < ${minClarityVal.toFixed(2)}`);
    }

    const minDepthVal = parseFloat(gateMinDepth.value);
    if (!isNaN(minDepthVal) && res.dimensions.technical_depth && res.dimensions.technical_depth.score < minDepthVal) {
      passed = false;
      gateViolations.push(`Tech Depth (${res.dimensions.technical_depth.score.toFixed(2)}) < ${minDepthVal.toFixed(2)}`);
    }

    // Soft Status Badges (Dot + Label)
    if (overall >= 0.70 && passed) {
      qualityBadge.className = 'status-tag status-tag-pass';
      qualityBadge.innerHTML = '<span>Approved</span>';
      overallProgressBar.style.backgroundColor = 'var(--status-pass-text)';
      gateStatusText.textContent = 'Passed';
    } else if (overall >= 0.45 && passed) {
      qualityBadge.className = 'status-tag status-tag-warn';
      qualityBadge.innerHTML = '<span>Needs Review</span>';
      overallProgressBar.style.backgroundColor = 'var(--status-warn-text)';
      gateStatusText.textContent = 'Passed with Notes';
    } else {
      qualityBadge.className = 'status-tag status-tag-fail';
      qualityBadge.innerHTML = '<span>Revision Needed</span>';
      overallProgressBar.style.backgroundColor = 'var(--status-fail-text)';
      gateStatusText.textContent = 'Failed';
    }

    // Telemetry details
    tPreset.textContent = state.currentPreset.charAt(0).toUpperCase() + state.currentPreset.slice(1);
    tTokens.textContent = res.usage_tokens ? `${res.usage_tokens.toLocaleString()}` : 'Cached';

    // Gate notice banner
    qualityGateNotice.classList.remove('hidden');
    if (gateViolations.length === 0) {
      qualityGateNotice.className = 'gate-notice-box pass';
      gateNoticeIcon.textContent = '✓';
      gateMsg.textContent = 'All quality threshold requirements satisfied';
    } else {
      qualityGateNotice.className = 'gate-notice-box fail';
      gateNoticeIcon.textContent = '✕';
      gateMsg.textContent = gateViolations.join('; ');
    }

    // 2. Render Dimension Cards (Matching "Onboarding" style from reference image)
    dimensionCardsGrid.innerHTML = '';
    const avatarIcons = {
      clarity: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`,
      completeness: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 11 12 14 22 4"></polyline><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path></svg>`,
      actionability: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>`,
      technical_depth: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="4" width="16" height="16" rx="2" ry="2"></rect><rect x="9" y="9" width="6" height="6"></rect><line x1="9" y1="1" x2="9" y2="4"></line><line x1="15" y1="1" x2="15" y2="4"></line><line x1="9" y1="20" x2="9" y2="23"></line><line x1="15" y1="20" x2="15" y2="23"></line></svg>`,
    };

    dims.forEach(dim => {
      const dimResult = res.dimensions[dim.id];
      if (!dimResult) return;

      const card = document.createElement('div');
      card.className = 'dim-card';
      card.id = `dim-card-${dim.id}`;

      const roundedLevel = Math.min(dim.max_level, Math.max(0, Math.round(dimResult.score)));
      const matchedCriterion = dim.criteria[roundedLevel] || '';
      const normPct = Math.round(dimResult.normalized * 100);

      // Build flat horizontal probability bars
      const probs = dimResult.probabilities || {};
      let flatBarsHtml = '';
      for (let lvl = 0; lvl <= dim.max_level; lvl++) {
        const p = probs[lvl] || 0.0;
        const pct = Math.round(p * 100);
        const isActive = lvl === roundedLevel;
        flatBarsHtml += `
          <div class="flat-bar-row" title="Level ${lvl}: ${pct}%&#10;${dim.criteria[lvl] || ''}">
            <span>Level ${lvl}</span>
            <div class="flat-bar-track">
              <div class="flat-bar-fill ${isActive ? 'active' : ''}" style="width: ${pct}%;"></div>
            </div>
            <span class="flat-bar-pct">${pct}%</span>
          </div>
        `;
      }

      const confPct = Math.round(dimResult.confidence * 100);

      card.innerHTML = `
        <div class="dim-card-header">
          <div class="dim-name-group">
            <span class="dim-card-title">${dim.label}</span>
            <span class="dim-weight-label">Weight ${(dim.weight * 100).toFixed(0)}%</span>
          </div>
          <span class="status-tag status-tag-neutral">
            <span>${confPct}% conf</span>
          </span>
        </div>

        <div class="dim-score-banner">
          <div>
            <span class="dim-score-number">${dimResult.score.toFixed(2)}</span>
            <span class="dim-score-scale">/ ${dim.max_level}.0</span>
          </div>
          <span class="status-tag ${normPct >= 70 ? 'status-tag-pass' : normPct >= 40 ? 'status-tag-warn' : 'status-tag-fail'}">
            <span>${normPct}% benchmark</span>
          </span>
        </div>

        <div class="dim-progress-track">
          <div class="dim-progress-fill fill-${dim.id}" style="width: ${normPct}%;"></div>
        </div>

        <div class="dim-criterion-box">
          <span class="criterion-header">Level ${roundedLevel} Assessment:</span>
          ${matchedCriterion}
        </div>

        <div class="flat-prob-section">
          <div class="flat-prob-title">Probability Distribution</div>
          <div class="flat-bar-list">
            ${flatBarsHtml}
          </div>
        </div>
      `;

      dimensionCardsGrid.appendChild(card);
    });
  }

  // Export Utilities
  function copyMarkdownPRTable() {
    if (!state.lastResult) return;
    const res = state.lastResult.result;
    const dims = state.lastResult.dimensions;
    const doc = state.lastResult.document;

    const headers = ['Document', ...dims.map(d => d.label), 'Overall'];
    const row = [
      `\`${doc.name}\``,
      ...dims.map(d => {
        const a = res.dimensions[d.id];
        return `${a.score.toFixed(2)} *(${Math.round(a.confidence * 100)}%)*`;
      }),
      `**${res.overall.toFixed(3)}**`,
    ];

    const md = [
      '### 📄 Document Quality Evaluation',
      '',
      `| ${headers.join(' | ')} |`,
      `| ${headers.map(() => '---').join(' | ')} |`,
      `| ${row.join(' | ')} |`,
      '',
      `> Evaluated with **TypeSafe System One (Jev)** using \`${state.currentPreset}\` preset.`,
    ].join('\n');

    navigator.clipboard.writeText(md).then(() => {
      showToast('Markdown PR table copied to clipboard');
    });
  }

  function downloadCSV() {
    if (!state.lastResult) return;
    const res = state.lastResult.result;
    const dims = state.lastResult.dimensions;
    const doc = state.lastResult.document;

    const headers = ['Document', 'Overall', ...dims.map(d => `${d.label} Score`), ...dims.map(d => `${d.label} Confidence`)];
    const row = [
      `"${doc.name}"`,
      res.overall.toFixed(4),
      ...dims.map(d => res.dimensions[d.id].score.toFixed(4)),
      ...dims.map(d => res.dimensions[d.id].confidence.toFixed(4)),
    ];

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), row.join(',')].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `${doc.name.replace(/\.[^/.]+$/, '')}-eval.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast('CSV downloaded');
  }

  function copyJSON() {
    if (!state.lastResult) return;
    navigator.clipboard.writeText(JSON.stringify(state.lastResult, null, 2)).then(() => {
      showToast('JSON copied to clipboard');
    });
  }

  function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = 'toast';
    if (type === 'error') {
      toast.style.borderColor = 'var(--status-red-border)';
      toast.style.color = 'var(--status-red-text)';
      toast.style.backgroundColor = 'var(--status-red-bg)';
    }
    toast.textContent = message;
    toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 250ms ease';
      setTimeout(() => toast.remove(), 250);
    }, 3000);
  }
});
