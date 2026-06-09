const storeKey = "health-risk-report-demo";

const initialData = {
  loggedIn: false,
  operator: "",
  reports: [],
  snpRecords: [
    {
      serverId: "SNP-SRV-20260531-0001",
      machineId: "MC-8F2A-4410",
      receivedAt: "2026-05-31 09:12",
      status: "ready"
    },
    {
      serverId: "SNP-SRV-20260531-0002",
      machineId: "MC-8F2A-4411",
      receivedAt: "2026-05-31 10:48",
      status: "ready"
    }
  ]
};

let state = loadState();
let currentReport = state.reports.at(-1) || null;

const loginPanel = document.querySelector("#loginPanel");
const workspace = document.querySelector("#workspace");
const loginForm = document.querySelector("#loginForm");
const patientForm = document.querySelector("#patientForm");
const operatorName = document.querySelector("#operatorName");
const logoutBtn = document.querySelector("#logoutBtn");
const simulateUploadBtn = document.querySelector("#simulateUploadBtn");
const snpTable = document.querySelector("#snpTable");
const snpSelect = document.querySelector("#snpSelect");
const reportPreview = document.querySelector("#reportPreview");
const downloadPdfBtn = document.querySelector("#downloadPdfBtn");

loginForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const form = new FormData(loginForm);
  state.loggedIn = true;
  state.operator = String(form.get("account") || "clinic_admin");
  saveState();
  render();
});

logoutBtn.addEventListener("click", () => {
  state.loggedIn = false;
  state.operator = "";
  currentReport = null;
  saveState();
  render();
});

simulateUploadBtn.addEventListener("click", () => {
  const next = state.snpRecords.length + 1;
  const now = new Date();
  state.snpRecords.unshift({
    serverId: `SNP-SRV-${dateStamp(now)}-${String(next).padStart(4, "0")}`,
    machineId: `MC-${randomSegment()}-${String(4400 + next)}`,
    receivedAt: formatDateTime(now),
    status: "ready"
  });
  saveState();
  render();
});

patientForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const form = new FormData(patientForm);
  const selectedSnp = state.snpRecords.find((record) => record.serverId === form.get("snpId"));

  currentReport = {
    reportId: `RPT-${dateStamp(new Date())}-${String(state.reports.length + 1).padStart(4, "0")}`,
    createdAt: formatDateTime(new Date()),
    patientName: String(form.get("patientName")),
    gender: String(form.get("gender")),
    hospitalId: String(form.get("hospitalId")),
    snp: selectedSnp,
    risks: buildRiskProfile(selectedSnp?.serverId || "")
  };

  state.reports.push(currentReport);
  saveState();
  patientForm.reset();
  render();
  document.querySelector("#report").scrollIntoView({ behavior: "smooth", block: "start" });
});

downloadPdfBtn.addEventListener("click", () => {
  if (!currentReport) return;
  const pdfBlob = createSamplePdf(currentReport);
  const url = URL.createObjectURL(pdfBlob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${currentReport.reportId}.pdf`;
  anchor.click();
  URL.revokeObjectURL(url);
});

document.querySelectorAll("nav a").forEach((link) => {
  link.addEventListener("click", () => {
    document.querySelectorAll("nav a").forEach((item) => item.classList.remove("active"));
    link.classList.add("active");
  });
});

function render() {
  loginPanel.classList.toggle("hidden", state.loggedIn);
  workspace.classList.toggle("hidden", !state.loggedIn);
  operatorName.textContent = state.operator || "未登入";

  document.querySelector("#snpCount").textContent = state.snpRecords.length;
  document.querySelector("#readyCount").textContent = state.snpRecords.filter((item) => item.status === "ready").length;
  document.querySelector("#patientCount").textContent = state.reports.length;
  document.querySelector("#reportCount").textContent = state.reports.length;

  renderSnpTable();
  renderSnpOptions();
  renderReport();
}

function renderSnpTable() {
  snpTable.innerHTML = state.snpRecords.map((record) => `
    <tr>
      <td>${record.serverId}</td>
      <td>${record.machineId}</td>
      <td>${record.receivedAt}</td>
      <td><span class="ready">可產生報告</span></td>
    </tr>
  `).join("");
}

function renderSnpOptions() {
  if (!state.snpRecords.length) {
    snpSelect.innerHTML = "<option value=\"\">尚無可用 SNP 資料</option>";
    return;
  }

  snpSelect.innerHTML = [
    "<option value=\"\">請選擇伺服器流水號</option>",
    ...state.snpRecords.map((record) => `<option value="${record.serverId}">${record.serverId} / ${record.machineId}</option>`)
  ].join("");
}

function renderReport() {
  downloadPdfBtn.disabled = !currentReport;
  if (!currentReport) {
    reportPreview.className = "report-preview empty";
    reportPreview.innerHTML = "<p>尚未產生報告。請先選擇 SNP 資料並建立病人資訊。</p>";
    return;
  }

  reportPreview.className = "report-preview";
  reportPreview.innerHTML = `
    <article class="report-sheet">
      <div class="report-title">
        <h3>個人健康風險評估報告</h3>
        <p>報告編號：${currentReport.reportId}　產生時間：${currentReport.createdAt}</p>
      </div>
      <div class="report-meta">
        <div class="info-box"><span>病人名稱</span><strong>${escapeHtml(currentReport.patientName)}</strong></div>
        <div class="info-box"><span>性別</span><strong>${escapeHtml(currentReport.gender)}</strong></div>
        <div class="info-box"><span>醫院端流水號</span><strong>${escapeHtml(currentReport.hospitalId)}</strong></div>
      </div>
      <div class="report-meta">
        <div class="info-box"><span>SNP 伺服器流水號</span><strong>${currentReport.snp.serverId}</strong></div>
        <div class="info-box"><span>機台流水號</span><strong>${currentReport.snp.machineId}</strong></div>
        <div class="info-box"><span>資料狀態</span><strong>已彙整</strong></div>
      </div>
      <div class="risk-grid">
        ${currentReport.risks.map((risk) => `
          <div class="risk-item">
            <span>${risk.name}</span>
            <strong class="${risk.className}">${risk.level}</strong>
            <p>${risk.note}</p>
          </div>
        `).join("")}
      </div>
      <p>本頁為展示用範例報告，實際臨床判讀需由合格醫療專業人員依正式檢測資料完成。</p>
    </article>
  `;
}

function buildRiskProfile(seedText) {
  const seed = [...seedText].reduce((sum, char) => sum + char.charCodeAt(0), 0);
  const profiles = [
    ["心血管風險", ["低", "中", "高"], ["risk-low", "risk-mid", "risk-high"]],
    ["第二型糖尿病風險", ["中", "低", "高"], ["risk-mid", "risk-low", "risk-high"]],
    ["藥物代謝注意事項", ["一般", "需追蹤", "建議諮詢"], ["risk-low", "risk-mid", "risk-high"]]
  ];

  return profiles.map(([name, levels, classes], index) => {
    const pointer = (seed + index) % levels.length;
    return {
      name,
      level: levels[pointer],
      className: classes[pointer],
      note: pointer === 0 ? "目前未見明顯升高訊號。" : pointer === 1 ? "建議搭配病史與生活型態評估。" : "建議安排醫師進一步解讀。"
    };
  });
}

function createSamplePdf(report) {
  const lines = [
    "Personal Health Risk Assessment Report",
    `Report ID: ${report.reportId}`,
    `Patient: ${report.patientName}`,
    `Gender: ${report.gender}`,
    `Hospital ID: ${report.hospitalId}`,
    `SNP Server ID: ${report.snp.serverId}`,
    `Machine ID: ${report.snp.machineId}`,
    "Risk Summary:",
    ...report.risks.map((risk) => `${risk.name}: ${risk.level}`),
    "Demo file only. Not for clinical diagnosis."
  ];

  const content = [
    "BT",
    "/F1 14 Tf",
    "50 780 Td",
    ...lines.map((line, index) => `${index === 0 ? "" : "0 -26 Td"}(${pdfSafe(line)}) Tj`),
    "ET"
  ].join("\n");

  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    `<< /Length ${content.length} >>\nstream\n${content}\nendstream`
  ];

  let pdf = "%PDF-1.4\n";
  const offsets = [0];
  objects.forEach((object, index) => {
    offsets.push(pdf.length);
    pdf += `${index + 1} 0 obj\n${object}\nendobj\n`;
  });
  const xrefStart = pdf.length;
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  offsets.slice(1).forEach((offset) => {
    pdf += `${String(offset).padStart(10, "0")} 00000 n \n`;
  });
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefStart}\n%%EOF`;

  return new Blob([pdf], { type: "application/pdf" });
}

function loadState() {
  const saved = localStorage.getItem(storeKey);
  if (!saved) return structuredClone(initialData);

  try {
    return { ...structuredClone(initialData), ...JSON.parse(saved) };
  } catch {
    return structuredClone(initialData);
  }
}

function saveState() {
  localStorage.setItem(storeKey, JSON.stringify(state));
}

function dateStamp(date) {
  return `${date.getFullYear()}${String(date.getMonth() + 1).padStart(2, "0")}${String(date.getDate()).padStart(2, "0")}`;
}

function formatDateTime(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")} ${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
}

function randomSegment() {
  return Math.random().toString(16).slice(2, 6).toUpperCase();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll("\"", "&quot;")
    .replaceAll("'", "&#039;");
}

function pdfSafe(value) {
  return String(value)
    .normalize("NFKD")
    .replace(/[^\x20-\x7E]/g, "?")
    .replace(/[()\\]/g, "\\$&");
}

render();
