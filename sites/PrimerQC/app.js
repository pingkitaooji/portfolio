const STORAGE_KEY = "primerqc_primer_records";

const demoPrimers = [
  {
    assayId: "PRIMER-DEMO-001",
    ampliconLength: 142,
    forward: "GCTGACCTGAAGTTCATCTGC",
    reverse: "CAGGTTGATGGTGATGGTGAA",
    status: "pass",
    note: "Demo: Ct stable, single peak"
  },
  {
    assayId: "PRIMER-DEMO-002",
    ampliconLength: 96,
    forward: "ATGCGCGCGCGTATATATAT",
    reverse: "ATATATACGCGCGCGCATAT",
    status: "fail",
    note: "Demo: high dimer risk"
  },
  {
    assayId: "PRIMER-DEMO-003",
    ampliconLength: 284,
    forward: "TACAGCTGATGACCTTGGCA",
    reverse: "ACCTTGACTGACCGTTAGCA",
    status: "untested",
    note: "Demo: pending validation"
  }
];

let latestResult = null;

const $ = (id) => document.getElementById(id);

function sanitizeSequence(value) {
  return value.toUpperCase().replace(/[^ACGT]/g, "");
}

function validateInputs(forward, reverse) {
  if (forward.length < 12 || reverse.length < 12) {
    throw new Error("Forward / reverse primer 至少需要 12 bp。");
  }
  if (forward.length > 35 || reverse.length > 35) {
    throw new Error("Demo 模型建議輸入 35 bp 以內的 primer。");
  }
}

function renderResult(result) {
  // The result object is returned by Django/Python; JS only formats it for review.
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
    ["Max homopolymer", f.max_homopolymer, r.max_homopolymer]
  ];

  $("featureRows").innerHTML = rows
    .map(([name, fv, rv]) => `<tr><td>${name}</td><td>${fv}</td><td>${rv}</td></tr>`)
    .join("");
  $("jsonOutput").textContent = JSON.stringify(result, null, 2);
}

function makeRecord() {
  // Browser storage keeps demo validation notes without requiring a backend database.
  if (!latestResult) throw new Error("請先完成一次模型預測。");
  return {
    id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}`,
    assay_id: $("assayId").value.trim() || "ASSAY-UNNAMED",
    created_at: new Date().toISOString(),
    validation_status: $("validationStatus").value,
    validation_note: $("validationNote").value.trim(),
    result: latestResult
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
  const records = loadRecords();
  if (!records.length) {
    $("recordsList").textContent = "尚無紀錄";
    return;
  }

  $("recordsList").innerHTML = records.map((record) => {
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
  // Benchmark metrics are static output from the model-building experiment.
  const results = window.PRIMER_MODEL_RESULTS;
  const modelName = $("activeModelName");
  const summary = $("modelDatasetSummary");
  const bestCard = $("bestModelCard");
  const rows = $("modelResultRows");
  const importance = $("featureImportance");

  if (!results) {
    if (modelName) modelName.textContent = "Python demo";
    if (summary) summary.textContent = "尚未找到模型結果檔。";
    return;
  }

  const best = results.best_model;
  const dataset = results.dataset;
  if (modelName) modelName.textContent = best.display_name;
  summary.textContent = `${dataset.source_file}，共 ${dataset.row_count} 筆；訓練 ${dataset.train_count} 筆、測試 ${dataset.test_count} 筆；success/fail = ${dataset.class_distribution.success}/${dataset.class_distribution.fail}`;
  bestCard.innerHTML = `
    <span>Best Model</span>
    <strong>${best.display_name}</strong>
    <p>${best.selection_rule}。目前保存 artifact：${best.artifact}。</p>
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
      <h2>最佳模型主要使用特徵</h2>
    </div>
    <div class="feature-chip-list">
      ${best.top_features.map((item) => `<span>${item.feature}<strong>${item.importance}</strong></span>`).join("")}
    </div>
  `;
}

function formatMetric(value) {
  return Number(value).toFixed(3);
}

$("demoButton").addEventListener("click", () => {
  const demo = demoPrimers[Math.floor(Math.random() * demoPrimers.length)];
  $("assayId").value = demo.assayId;
  $("ampliconLength").value = demo.ampliconLength;
  $("forwardPrimer").value = demo.forward;
  $("reversePrimer").value = demo.reverse;
  $("validationStatus").value = demo.status;
  $("validationNote").value = demo.note;
});

$("primerForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    // Primer feature extraction and scoring happen in the Django endpoint.
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

$("clearRecordsButton").addEventListener("click", () => {
  saveRecords([]);
  renderRecords();
});

renderRecords();
renderModelBenchmark();

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
