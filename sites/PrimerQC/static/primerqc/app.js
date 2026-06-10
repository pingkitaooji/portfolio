const STORAGE_KEY = "primerqc_primer_records";

let latestResult = null;

const $ = (id) => document.getElementById(id);

function sanitizeSequence(value) {
  return value.toUpperCase().replace(/[^ACGT]/g, "");
}

function validateInputs(forward, reverse) {
  if (forward.length < 12 || reverse.length < 12) {
    throw new Error("Forward and reverse primers must be at least 12 bp.");
  }
  if (forward.length > 35 || reverse.length > 35) {
    throw new Error("Demo input supports primers up to 35 bp.");
  }
}

function renderResult(result) {
  const score = Math.round(result.prediction.probability_usable * 100);
  $("scoreValue").textContent = `${score}%`;
  $("predictionLabel").textContent = `${result.prediction.label} - ${result.prediction.reasons[0]}`;
  $("scoreCard").dataset.status = result.prediction.label.toLowerCase() === "pass"
    ? "pass"
    : result.prediction.label.toLowerCase() === "review"
      ? "review"
      : "fail";

  $("tmDiff").textContent = `${result.features.pair.tm_difference_celsius} C`;
  $("dimerRisk").textContent = result.features.pair.hetero_dimer_proxy;
  $("gcWindow").textContent = `${result.features.pair.average_gc_percent}%`;

  const f = result.features.forward;
  const r = result.features.reverse;
  const rows = [
    ["Length", f.length, r.length],
    ["GC %", `${f.gc_percent}%`, `${r.gc_percent}%`],
    ["Tm", `${f.tm_celsius} C`, `${r.tm_celsius} C`],
    ["3-prime GC", `${f.three_prime_gc_percent}%`, `${r.three_prime_gc_percent}%`],
    ["Self complementarity", f.self_complementarity, r.self_complementarity],
    ["Hairpin proxy", f.hairpin_proxy, r.hairpin_proxy],
    ["Max homopolymer", f.max_homopolymer, r.max_homopolymer],
  ];

  $("featureRows").innerHTML = rows
    .map(([name, fv, rv]) => `<tr><td>${name}</td><td>${fv}</td><td>${rv}</td></tr>`)
    .join("");
}

function makeRecord() {
  if (!latestResult) throw new Error("Please run a primer prediction before saving a record.");
  const validationStatus = $("validationStatus");
  const validationNote = $("validationNote");
  return {
    id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}`,
    assay_id: $("assayId").value.trim() || "ASSAY-UNNAMED",
    created_at: new Date().toISOString(),
    validation_status: validationStatus ? validationStatus.value : "not_recorded",
    validation_note: validationNote ? validationNote.value.trim() : "",
    result: latestResult,
  };
}

function loadRecords() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
  } catch {
    return [];
  }
}

function saveRecords(records) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(records));
}

function renderRecords() {
  const recordsList = $("recordsList");
  if (!recordsList) return;

  const records = loadRecords();
  if (!records.length) {
    recordsList.textContent = "No records yet";
    return;
  }

  recordsList.innerHTML = records.map((record) => {
    const score = Math.round(record.result.prediction.probability_usable * 100);
    const created = new Date(record.created_at).toLocaleString("zh-TW");
    return `
      <article class="record-card">
        <div><span>Assay</span><strong>${record.assay_id}</strong></div>
        <div><span>Score</span><strong>${score}%</strong></div>
        <div><span>Prediction</span><strong>${record.result.prediction.label}</strong></div>
        <div><span>Validation</span><strong>${record.validation_status}</strong></div>
        <div><span>Note</span><strong>${record.validation_note || created}</strong></div>
      </article>
    `;
  }).join("");
}

function renderModelBenchmark() {
  const results = window.PRIMER_MODEL_RESULTS;
  const modelName = $("activeModelName");
  const summary = $("modelDatasetSummary");
  const bestCard = $("bestModelCard");
  const rows = $("modelResultRows");
  const importance = $("featureImportance");

  if (!results) {
    if (modelName) modelName.textContent = "Python demo";
    if (summary) summary.textContent = "Model benchmark data is not loaded.";
    return;
  }

  const best = results.best_model;
  const dataset = results.dataset;
  if (modelName) modelName.textContent = best.display_name;
  summary.textContent = `${dataset.source_file}, rows ${dataset.row_count}, train ${dataset.train_count}, test ${dataset.test_count}, success/fail = ${dataset.class_distribution.success}/${dataset.class_distribution.fail}`;
  bestCard.innerHTML = `
    <span>Best Model</span>
    <strong>${best.display_name}</strong>
    <p>${best.selection_rule}. Artifact: ${best.artifact}</p>
  `;
  rows.innerHTML = results.models.map((model) => {
    const metrics = model.metrics;
    const matrix = model.confusion_matrix;
    const selected = model.model_key === best.model_key ? "selected-model" : "";
    return `
      <tr class="${selected}">
        <td><strong>${model.display_name}</strong></td>
        <td>${formatMetric(metrics.accuracy)}</td>
        <td>${formatMetric(metrics.balanced_accuracy)}</td>
        <td>${formatMetric(metrics.precision_success)}</td>
        <td>${formatMetric(metrics.recall_success)}</td>
        <td>${formatMetric(metrics.f1_success)}</td>
        <td>${formatMetric(metrics.roc_auc)}</td>
        <td>TN ${matrix.tn_fail} / FP ${matrix.fp_fail_as_success} / FN ${matrix.fn_success_as_fail} / TP ${matrix.tp_success}</td>
      </tr>
    `;
  }).join("");
  importance.innerHTML = `
    <div class="section-head compact-head">
      <p>Top Features</p>
      <h2>Most influential model features</h2>
    </div>
    <div class="feature-chip-list">
      ${best.top_features.map((item) => `<span>${item.feature}<strong>${item.importance}</strong></span>`).join("")}
    </div>
  `;
}

function formatMetric(value) {
  return Number(value).toFixed(3);
}

$("demoButton").addEventListener("click", async () => {
  try {
    const demo = await getJson("/api/demo/");
    $("assayId").value = demo.assayId;
    $("ampliconLength").value = demo.ampliconLength;
    $("forwardPrimer").value = demo.forward;
    $("reversePrimer").value = demo.reverse;
    if ($("validationStatus")) $("validationStatus").value = demo.status;
    if ($("validationNote")) $("validationNote").value = demo.note;
  } catch (error) {
    alert(error.message);
  }
});

$("primerForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const forward = sanitizeSequence($("forwardPrimer").value);
    const reverse = sanitizeSequence($("reversePrimer").value);
    const ampliconLength = Number($("ampliconLength").value || 0);
    validateInputs(forward, reverse);
    latestResult = await postJson("/api/predict/", {
      forward_primer: forward,
      reverse_primer: reverse,
      amplicon_length_bp: ampliconLength,
    });
    renderResult(latestResult);
  } catch (error) {
    alert(error.message);
  }
});

if ($("saveRecordButton")) {
  $("saveRecordButton").addEventListener("click", () => {
    try {
      const records = loadRecords();
      records.unshift(makeRecord());
      saveRecords(records.slice(0, 20));
      renderRecords();
    } catch (error) {
      alert(error.message);
    }
  });
}

if ($("clearRecordsButton")) {
  $("clearRecordsButton").addEventListener("click", () => {
    saveRecords([]);
    renderRecords();
  });
}

renderRecords();
renderModelBenchmark();

async function getJson(url) {
  const response = await fetch(url);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `HTTP ${response.status}`);
  }
  return data;
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
