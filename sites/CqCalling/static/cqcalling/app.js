const cycleCount = 40;
const cycles = Array.from({ length: cycleCount }, (_, index) => index + 1);

const cycleGrid = document.querySelector("#cycleGrid");
const signalText = document.querySelector("#signalText");
const scenarioSelect = document.querySelector("#scenarioSelect");
const demoBtn = document.querySelector("#demoBtn");
const applyTextBtn = document.querySelector("#applyTextBtn");
const calculateBtn = document.querySelector("#calculateBtn");
const clearBtn = document.querySelector("#clearBtn");
const chart = document.querySelector("#fitChart");
const ctx = chart.getContext("2d");
const cqValue = document.querySelector("#cqValue");
const irValue = document.querySelector("#irValue");
const r2Value = document.querySelector("#r2Value");
const qcValue = document.querySelector("#qcValue");
const fitDetails = document.querySelector("#fitDetails");
const pipeline = document.querySelector("#pipeline");
const qcList = document.querySelector("#qcList");
const instrumentOutput = document.querySelector("#instrumentOutput");
const copyJsonBtn = document.querySelector("#copyJsonBtn");
const chartTabs = document.querySelectorAll(".tab[data-chart-mode]");

const inputs = [];
let chartMode = "fit";
let lastAnalysis = null;

init();

function init() {
  // Build the 40-cycle input grid once, then hydrate it with a demo signal.
  buildCycleInputs();
  const demoSignals = generateDemoSignals();
  setSignals(demoSignals);
  calculateAndRender();

  demoBtn.addEventListener("click", () => {
    setSignals(generateDemoSignals(scenarioSelect.value));
    calculateAndRender();
  });

  applyTextBtn.addEventListener("click", () => {
    const parsed = parseSignalText(signalText.value);
    if (parsed.length !== cycleCount) {
      showError(`Ë´ãËº∏?•Â?Â•?${cycleCount} ?ãÊï∏?º„ÄÇÁõÆ?çË???${parsed.length} ?ã„ÄÇ`);
      return;
    }
    setSignals(parsed);
    calculateAndRender();
  });

  calculateBtn.addEventListener("click", calculateAndRender);

  clearBtn.addEventListener("click", () => {
    setSignals(Array(cycleCount).fill(""));
    drawEmptyChart();
    setResults(null);
    fitDetails.classList.remove("error");
    fitDetails.innerHTML = "<p>?¢Á? demo ?ñËº∏??40 ÈªûÊï∏?ºÂ??ãÂ?Ë®àÁ???/p>";
  });

  chartTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      chartMode = tab.dataset.chartMode;
      chartTabs.forEach((item) => item.classList.toggle("active", item === tab));
      if (lastAnalysis) drawChart(lastAnalysis.signals, lastAnalysis);
    });
  });
  copyJsonBtn.addEventListener("click", async () => {
    await navigator.clipboard.writeText(instrumentOutput.textContent);
    copyJsonBtn.textContent = "Â∑≤Ë?Ë£?;
    setTimeout(() => {
      copyJsonBtn.textContent = "Ë§áË£Ω";
    }, 1200);
  });
  window.addEventListener("resize", () => calculateAndRender(false));
}

function buildCycleInputs() {
  cycleGrid.innerHTML = "";
  cycles.forEach((cycle) => {
    const label = document.createElement("label");
    label.className = "cycle-cell";
    label.innerHTML = `<span>Cycle ${cycle}</span>`;

    const input = document.createElement("input");
    input.type = "number";
    input.min = "0";
    input.max = "100";
    input.step = "0.01";
    input.inputMode = "decimal";
    input.addEventListener("input", () => syncTextareaFromInputs());
    input.addEventListener("change", () => calculateAndRender(false));

    label.appendChild(input);
    cycleGrid.appendChild(label);
    inputs.push(input);
  });
}

function generateDemoSignals(scenario = "normal") {
  const presets = {
    normal: { baseline: [5, 10], amplitude: [70, 84], cq: [18, 28], k: [0.42, 0.76], noise: [1.2, 2.2] },
    late: { baseline: [5, 10], amplitude: [62, 78], cq: [31, 36], k: [0.28, 0.52], noise: [1.2, 2.5] },
    low: { baseline: [5, 12], amplitude: [18, 32], cq: [22, 31], k: [0.25, 0.48], noise: [1.5, 3.2] },
    noisy: { baseline: [7, 15], amplitude: [55, 78], cq: [18, 30], k: [0.34, 0.68], noise: [4.2, 7.5] },
    none: { baseline: [8, 16], amplitude: [0, 6], cq: [24, 30], k: [0.12, 0.28], noise: [1.8, 3.8] },
    saturated: { baseline: [4, 8], amplitude: [90, 104], cq: [14, 22], k: [0.7, 1.15], noise: [1.0, 2.0] },
  };
  const preset = presets[scenario] || presets.normal;
  const baseline = randomBetween(...preset.baseline);
  const amplitude = randomBetween(...preset.amplitude);
  const cq = randomBetween(...preset.cq);
  const k = randomBetween(...preset.k);
  const noiseLevel = randomBetween(...preset.noise);
  return cycles.map((cycle) => {
    const ideal = baseline + amplitude / (1 + Math.exp(-k * (cycle - cq)));
    const noise = randomBetween(-noiseLevel, noiseLevel) + (cycle < cq - 7 ? randomBetween(-noiseLevel / 2, noiseLevel / 2) : 0);
    return clamp(ideal + noise, 0, 100);
  });
}

function parseSignalText(text) {
  return text
    .split(/[\s,;Ôºå„ÄÅ]+/)
    .map((value) => value.trim())
    .filter(Boolean)
    .map(Number)
    .filter((value) => Number.isFinite(value));
}

function setSignals(signals) {
  inputs.forEach((input, index) => {
    input.value = signals[index] === "" ? "" : formatNumber(signals[index], 2);
    input.classList.remove("invalid");
  });
  syncTextareaFromInputs();
}

function readSignals() {
  let valid = true;
  const values = inputs.map((input) => {
    const value = Number(input.value);
    const ok = Number.isFinite(value) && value >= 0 && value <= 100;
    input.classList.toggle("invalid", !ok);
    if (!ok) valid = false;
    return value;
  });
  if (!valid) return null;
  return values;
}

function syncTextareaFromInputs() {
  signalText.value = inputs.map((input) => input.value).join(", ");
}

async function calculateAndRender(updateTextarea = true) {
  // Core fitting and QC are calculated by Django/Python; JS renders the response.
  const signals = readSignals();
  if (!signals) {
    showError("ÊØè‰?ÈªûÈÉΩ?ÄË¶ÅÊòØ 0-100 ?ÑÊï∏?º„Ä?);
    return;
  }
  if (updateTextarea) syncTextareaFromInputs();

  try {
    const result = await postJson("/api/analyze/", { signals });
    lastAnalysis = result;
    drawChart(result.signals, result);
    setResults(result);
    showFitDetails(result);
    renderPipeline(result);
    renderQc(result.qc);
    renderInstrumentOutput(result);
  } catch (error) {
    showError(error.message || "ÂæåÁ´ØÊºîÁ?Ê≥ïË?ÁÆóÂ§±?ó„Ä?);
  }
}

function sigmoid(x, params) {
  return params.bottom + (params.top - params.bottom) / (1 + Math.exp(-params.k * (x - params.x0)));
}

function drawEmptyChart() {
  const rect = chart.getBoundingClientRect();
  const scale = window.devicePixelRatio || 1;
  chart.width = Math.max(720, Math.floor(rect.width * scale));
  chart.height = Math.floor(chart.width * 0.56);
  ctx.setTransform(scale, 0, 0, scale, 0, 0);
  ctx.clearRect(0, 0, chart.width, chart.height);
}

function drawChart(signals, fit) {
  // The chart is intentionally client-side so users can switch views instantly.
  const rect = chart.getBoundingClientRect();
  const cssWidth = Math.max(720, rect.width || 980);
  const cssHeight = Math.max(380, cssWidth * 0.56);
  const scale = window.devicePixelRatio || 1;
  chart.width = Math.floor(cssWidth * scale);
  chart.height = Math.floor(cssHeight * scale);
  chart.style.height = `${cssHeight}px`;
  ctx.setTransform(scale, 0, 0, scale, 0, 0);

  const padding = { left: 66, right: 28, top: 30, bottom: 56 };
  const width = cssWidth - padding.left - padding.right;
  const height = cssHeight - padding.top - padding.bottom;

  ctx.clearRect(0, 0, cssWidth, cssHeight);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, cssWidth, cssHeight);

  if (chartMode === "residual") {
    drawResidualChart(fit, padding, width, height, cssWidth, cssHeight);
    return;
  }

  const xScale = (cycle) => padding.left + ((cycle - 1) / 39) * width;
  const maxY = chartMode === "corrected" ? Math.max(30, Math.ceil(Math.max(...fit.corrected, fit.top - fit.bottom) / 10) * 10) : 110;
  drawGrid(padding, width, height, cssWidth, cssHeight, maxY);
  const yScale = (value) => padding.top + (1 - clamp(value, 0, maxY) / maxY) * height;

  if (chartMode === "corrected") {
    const correctedFit = { ...fit, bottom: 0, top: fit.top - fit.bottom };
    drawCqLine(correctedFit, xScale, yScale, padding);
    drawFitLine(correctedFit, xScale, yScale);
    drawPoints(fit.corrected, xScale, yScale);
  } else {
    drawCqLine(fit, xScale, yScale, padding);
    drawFitLine(fit, xScale, yScale);
    drawPoints(signals, xScale, yScale);
  }

  drawAxisLabels(padding, width, height, cssWidth, cssHeight, chartMode === "corrected" ? "Baseline Corrected RFU" : "Fluorescence Signal");
}

function drawGrid(padding, width, height, cssWidth, cssHeight, maxY = 110) {
  ctx.strokeStyle = "#e2e8f0";
  ctx.lineWidth = 1;
  ctx.font = "12px Segoe UI, Arial";
  ctx.fillStyle = "#64748b";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";

  const step = maxY <= 40 ? 10 : 20;
  for (let y = 0; y <= maxY; y += step) {
    const py = padding.top + (1 - y / maxY) * height;
    ctx.beginPath();
    ctx.moveTo(padding.left, py);
    ctx.lineTo(cssWidth - padding.right, py);
    ctx.stroke();
    ctx.fillText(String(y), padding.left - 10, py);
  }

  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  for (let x = 1; x <= 40; x += 5) {
    const px = padding.left + ((x - 1) / 39) * width;
    ctx.beginPath();
    ctx.moveTo(px, padding.top);
    ctx.lineTo(px, cssHeight - padding.bottom);
    ctx.stroke();
    ctx.fillText(String(x), px, cssHeight - padding.bottom + 12);
  }

  ctx.strokeStyle = "#94a3b8";
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  ctx.moveTo(padding.left, padding.top);
  ctx.lineTo(padding.left, cssHeight - padding.bottom);
  ctx.lineTo(cssWidth - padding.right, cssHeight - padding.bottom);
  ctx.stroke();
}

function drawFitLine(fit, xScale, yScale) {
  ctx.strokeStyle = "#38bdf8";
  ctx.lineWidth = 3;
  ctx.beginPath();
  for (let index = 0; index <= 390; index += 1) {
    const cycle = 1 + (index / 390) * 39;
    const x = xScale(cycle);
    const y = yScale(sigmoid(cycle, fit));
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.stroke();
}

function drawPoints(signals, xScale, yScale) {
  ctx.fillStyle = "#0ea5e9";
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 1.5;
  signals.forEach((value, index) => {
    const x = xScale(index + 1);
    const y = yScale(value);
    ctx.beginPath();
    ctx.arc(x, y, 4.5, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
  });
}

function drawCqLine(fit, xScale, yScale, padding) {
  if (Number.isFinite(fit.cq) && fit.cq >= 1 && fit.cq <= 40) {
    const x = xScale(fit.cq);
    const cqY = yScale(sigmoid(fit.cq, fit));
    ctx.strokeStyle = "#fb7185";
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(x, padding.top);
    ctx.lineTo(x, cqY);
    ctx.stroke();
    ctx.setLineDash([]);

    ctx.fillStyle = "#fb7185";
    ctx.font = "bold 12px Segoe UI, Arial";
    ctx.textAlign = "left";
    ctx.textBaseline = "bottom";
    ctx.fillText(`Cq ${formatNumber(fit.cq, 2)}`, x + 7, cqY - 6);
  }
}

function drawAxisLabels(padding, width, height, cssWidth, cssHeight, yLabel = "Fluorescence Signal") {
  ctx.fillStyle = "#334155";
  ctx.font = "bold 13px Segoe UI, Arial";
  ctx.textAlign = "center";
  ctx.textBaseline = "bottom";
  ctx.fillText("Cycle", padding.left + width / 2, cssHeight - 12);

  ctx.save();
  ctx.translate(18, padding.top + height / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText(yLabel, 0, 0);
  ctx.restore();

  ctx.textAlign = "right";
  ctx.fillStyle = "#38bdf8";
  ctx.fillText("?¨Â?Á∑?, cssWidth - padding.right, padding.top + 18);
  ctx.fillStyle = "#0ea5e9";
  ctx.fillText("?üÂ?Ë®äË?", cssWidth - padding.right, padding.top + 38);
}

function setResults(result) {
  if (!result) {
    cqValue.textContent = "--";
    irValue.textContent = "--";
    r2Value.textContent = "--";
    qcValue.textContent = "--";
    return;
  }
  cqValue.textContent = result.reportableCq === null ? "N/A" : formatNumber(result.reportableCq, 2);
  irValue.textContent = formatNumber(result.ir, 3);
  r2Value.textContent = formatNumber(result.r2, 4);
  qcValue.textContent = result.qc.overall;
}

function showFitDetails(result) {
  fitDetails.classList.remove("error");
  fitDetails.innerHTML = `
    <p>
      4PL sigmoidÔº?strong>Bottom ${formatNumber(result.bottom, 2)}</strong>??      <strong>Top ${formatNumber(result.top, 2)}</strong>??      <strong>k ${formatNumber(result.k, 4)}</strong>??      <strong>Inflection Cycle ${formatNumber(result.x0, 2)}</strong>??      CqÔºà‰?Ê¨°ÂæÆ?ÜÊ?Â§ßÂÄºÔ???<strong>${result.reportableCq === null ? "N/A" : formatNumber(result.reportableCq, 2)}</strong>
      ${result.reportableCq === null ? `Ôºàraw estimate ${formatNumber(result.cq, 2)}ÔºåQC fail ‰∏çÂ??±Ô?` : ""}Ôº?      inflection cycle ??<strong>${formatNumber(result.cqMaxSlope, 2)}</strong>??    </p>
  `;
}

function showError(message) {
  fitDetails.classList.add("error");
  fitDetails.innerHTML = `<p>${message}</p>`;
  setResults(null);
}

function randomBetween(min, max) {
  return min + Math.random() * (max - min);
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function formatNumber(value, digits) {
  return Number(value).toFixed(digits);
}

function drawResidualChart(fit, padding, width, height, cssWidth, cssHeight) {
  const maxAbs = Math.max(5, Math.ceil(Math.max(...fit.residuals.map(Math.abs)) / 2) * 2);
  const xScale = (cycle) => padding.left + ((cycle - 1) / 39) * width;
  const yScale = (value) => padding.top + (1 - (value + maxAbs) / (2 * maxAbs)) * height;

  ctx.strokeStyle = "#e2e8f0";
  ctx.lineWidth = 1;
  ctx.font = "12px Segoe UI, Arial";
  ctx.fillStyle = "#64748b";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  [-maxAbs, 0, maxAbs].forEach((value) => {
    const y = yScale(value);
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(cssWidth - padding.right, y);
    ctx.stroke();
    ctx.fillText(formatNumber(value, 0), padding.left - 10, y);
  });

  ctx.fillStyle = "#7dd3fc";
  fit.residuals.forEach((value, index) => {
    const x = xScale(index + 1);
    const y = yScale(value);
    ctx.beginPath();
    ctx.arc(x, y, 4.5, 0, Math.PI * 2);
    ctx.fill();
  });

  drawAxisLabels(padding, width, height, cssWidth, cssHeight, "Residual RFU");
}

function renderPipeline(result) {
  const steps = [
    ["Raw input", "40 cycles, RFU range 0-100"],
    ["Baseline correction", `Bottom estimated ${formatNumber(result.bottom, 2)} RFU`],
    ["Python 4PL sigmoid fitting", `Django backend bounded refinement, SSE ${formatNumber(result.sse, 2)}`],
    ["Cq extraction", `Second-derivative maximum Cq ${formatNumber(result.cq, 2)}`],
    ["QC decision", `${result.qc.overall}, confidence ${result.qc.confidence}`],
    ["Instrument output", "Deterministic JSON payload for machine integration"],
  ];
  pipeline.innerHTML = steps
    .map(
      ([name, detail], index) => `
        <div class="pipeline-step">
          <em class="step-index">${index + 1}</em>
          <div><strong>${name}</strong><span>${detail}</span></div>
          <b class="status-pill status-pass">DONE</b>
        </div>
      `
    )
    .join("");
}

function renderQc(qc) {
  qcList.innerHTML = qc.checks
    .map(
      (check) => `
        <div class="qc-item">
          <div><strong>${check.name}</strong><span>${check.value}</span></div>
          <b class="status-pill status-${check.status.toLowerCase()}">${check.status}</b>
        </div>
      `
    )
    .join("");
}

function renderInstrumentOutput(result) {
  // Keep the backend payload visible to show how an instrument could consume it.
  instrumentOutput.textContent = JSON.stringify(result.instrumentOutput, null, 2);
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `HTTP ${response.status}`);
  }
  return data;
}
