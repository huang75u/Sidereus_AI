/**
 * AI 智能简历分析系统 — 前端逻辑
 * 支持真实后端 API 和 Mock 演示模式
 */

// ─── State ────────────────────────────────────────────────────────────────────
const state = {
  currentStep: 1,
  resumeId: null,
  resumeData: null,
  file: null,
  apiBase: "",
};

// ─── Mock Data ────────────────────────────────────────────────────────────────
const MOCK_RESUME = {
  success: true,
  resume_id: "mock-" + Math.random().toString(36).slice(2, 10),
  message: "简历解析成功（演示模式）",
  data: {
    resume_id: "mock-demo",
    basic_info: { name: "张伟", phone: "13812345678", email: "zhangwei@example.com", address: "上海市浦东新区" },
    job_intent: { position: "Python 后端工程师", expected_salary: "25K-35K" },
    background: {
      years_of_experience: "4年",
      education: "本科 · 计算机科学与技术",
      projects: ["电商平台微服务重构", "实时数据处理流水线", "智能推荐系统"],
      skills: ["Python", "FastAPI", "Django", "MySQL", "Redis", "Docker", "Kubernetes", "Git"],
    },
    raw_text: "（演示模式，无实际文本）",
    created_at: new Date().toISOString(),
  },
};

const MOCK_MATCH = {
  resume_id: "mock-demo",
  job_description: "",
  skill_match: {
    matched: ["Python", "FastAPI", "MySQL", "Redis", "Docker"],
    missing: ["Kubernetes", "Kafka"],
    match_rate: 0.72,
  },
  experience_relevance: 0.85,
  overall_score: 81,
  ai_analysis:
    "候选人具备扎实的 Python 后端开发能力，FastAPI 和 MySQL 经验与岗位高度契合，Redis 缓存经验加分。缺少 Kafka 消息队列经验，但整体技术栈匹配良好，建议进行技术面试进一步考察。",
  recommendation: "推荐",
  created_at: new Date().toISOString(),
};

// ─── Init ─────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  setupDragDrop();
  loadSavedApiUrl();

  document.getElementById("file-input").addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) handleFileSelected(file);
  });
});

function loadSavedApiUrl() {
  const saved = localStorage.getItem("resume_api_base");
  if (saved) document.getElementById("api-base-url").value = saved;
}

// ─── Drag & Drop ──────────────────────────────────────────────────────────────
function setupDragDrop() {
  const area = document.getElementById("upload-area");

  area.addEventListener("dragover", (e) => {
    e.preventDefault();
    area.classList.add("drag-over");
  });

  area.addEventListener("dragleave", () => area.classList.remove("drag-over"));

  area.addEventListener("drop", (e) => {
    e.preventDefault();
    area.classList.remove("drag-over");
    const file = e.dataTransfer.files[0];
    if (file) handleFileSelected(file);
  });
}

// ─── File Handling ────────────────────────────────────────────────────────────
function handleFileSelected(file) {
  if (!file.name.toLowerCase().endsWith(".pdf") && file.type !== "application/pdf") {
    showAlert("upload-error", "❌ 请上传 PDF 格式文件");
    return;
  }

  if (file.size > 10 * 1024 * 1024) {
    showAlert("upload-error", "❌ 文件大小超过 10MB 限制");
    return;
  }

  state.file = file;
  hideAlert("upload-error");

  document.getElementById("upload-placeholder").style.display = "none";
  document.getElementById("upload-preview").style.display = "flex";
  document.getElementById("file-name").textContent = file.name;
  document.getElementById("file-size").textContent = formatBytes(file.size);
}

function resetUpload() {
  state.file = null;
  document.getElementById("file-input").value = "";
  document.getElementById("upload-placeholder").style.display = "";
  document.getElementById("upload-preview").style.display = "none";
  hideAlert("upload-error");
}

// ─── API Base ─────────────────────────────────────────────────────────────────
function getApiBase() {
  const val = document.getElementById("api-base-url").value.trim().replace(/\/$/, "");
  state.apiBase = val;
  if (val) localStorage.setItem("resume_api_base", val);
  return val;
}

async function testConnection() {
  const base = getApiBase();
  if (!base) return alert("请先输入后端 API 地址");

  try {
    const res = await fetch(`${base}/health`, { signal: AbortSignal.timeout(5000) });
    if (res.ok) {
      alert("✅ 连接成功！");
    } else {
      alert(`⚠️ 服务返回 ${res.status}`);
    }
  } catch {
    alert("❌ 无法连接，请检查地址或网络");
  }
}

// ─── Upload & Parse ───────────────────────────────────────────────────────────
async function uploadResume() {
  const apiBase = getApiBase();

  // Mock mode — no real file needed
  if (!apiBase) {
    setLoading("upload-btn", "upload-btn-text", "upload-spinner", true);
    await sleep(1400);
    setLoading("upload-btn", "upload-btn-text", "upload-spinner", false);
    const mockData = { ...MOCK_RESUME, resume_id: MOCK_RESUME.data.resume_id };
    handleUploadSuccess(mockData);
    return;
  }

  if (!state.file) {
    showAlert("upload-error", "❌ 请先选择 PDF 文件");
    return;
  }

  setLoading("upload-btn", "upload-btn-text", "upload-spinner", true);
  hideAlert("upload-error");

  try {
    const formData = new FormData();
    formData.append("file", state.file);

    const res = await fetch(`${apiBase}/api/resume/upload`, {
      method: "POST",
      body: formData,
    });

    const json = await res.json();

    if (!res.ok) {
      throw new Error(json.detail || json.message || `HTTP ${res.status}`);
    }

    handleUploadSuccess(json);
  } catch (err) {
    showAlert("upload-error", `❌ 上传失败：${err.message}`);
  } finally {
    setLoading("upload-btn", "upload-btn-text", "upload-spinner", false);
  }
}

function handleUploadSuccess(json) {
  state.resumeId = json.resume_id || json.data?.resume_id;
  state.resumeData = json.data;

  renderResumeResult(json.data);
  document.getElementById("resume-id-badge").textContent = `ID: ${state.resumeId}`;
  goToStep(2);
}

// ─── Render Resume ────────────────────────────────────────────────────────────
function renderResumeResult(data) {
  if (!data) return;
  const { basic_info = {}, job_intent = {}, background = {} } = data;

  renderInfoList("basic-info-list", [
    { key: "姓名", val: basic_info.name },
    { key: "电话", val: basic_info.phone },
    { key: "邮箱", val: basic_info.email },
    { key: "地址", val: basic_info.address },
  ]);

  renderInfoList("job-intent-list", [
    { key: "求职意向", val: job_intent.position },
    { key: "期望薪资", val: job_intent.expected_salary },
  ]);

  renderInfoList("background-list", [
    { key: "工作年限", val: background.years_of_experience },
    { key: "学历", val: background.education },
    { key: "项目经历", val: (background.projects || []).join("、") || null },
  ]);

  renderSkillTags("skills-tags", background.skills || [], "");
}

function renderInfoList(containerId, items) {
  const el = document.getElementById(containerId);
  el.innerHTML = items
    .map(
      ({ key, val }) => `
      <div class="info-item">
        <span class="info-key">${key}</span>
        <span class="info-val ${!val ? "null-val" : ""}">${val || "未获取"}</span>
      </div>`
    )
    .join("");
}

function renderSkillTags(containerId, tags, cls) {
  const el = document.getElementById(containerId);
  if (!tags || tags.length === 0) {
    el.innerHTML = `<span class="null-val" style="font-size:13px">暂无</span>`;
    return;
  }
  el.innerHTML = tags
    .map((t) => `<span class="skill-tag ${cls}">${t}</span>`)
    .join("");
}

// ─── Match ────────────────────────────────────────────────────────────────────
async function matchResume() {
  const jd = document.getElementById("jd-input").value.trim();
  if (!jd) {
    showAlert("match-error", "❌ 请输入岗位需求描述");
    return;
  }

  const apiBase = getApiBase();
  setLoading("match-btn", "match-btn-text", "match-spinner", true);
  hideAlert("match-error");

  try {
    let matchData;

    if (!apiBase) {
      await sleep(1600);
      matchData = { ...MOCK_MATCH, job_description: jd };
    } else {
      const res = await fetch(`${apiBase}/api/match/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resume_id: state.resumeId, job_description: jd }),
      });

      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || json.message || `HTTP ${res.status}`);
      matchData = json;
    }

    renderMatchResult(matchData);
    document.getElementById("match-result-container").classList.remove("hidden");
  } catch (err) {
    showAlert("match-error", `❌ 匹配失败：${err.message}`);
  } finally {
    setLoading("match-btn", "match-btn-text", "match-spinner", false);
  }
}

function renderMatchResult(data) {
  const score = Math.round(data.overall_score || 0);
  const skillRate = data.skill_match?.match_rate || 0;
  const expRate = data.experience_relevance || 0;

  // Animated score ring
  const circumference = 2 * Math.PI * 50;
  const offset = circumference - (score / 100) * circumference;
  document.getElementById("score-value").textContent = score;
  setTimeout(() => {
    const ring = document.getElementById("ring-fill");
    ring.style.strokeDashoffset = offset;
    ring.style.stroke = scoreColor(score);
    document.getElementById("score-value").style.color = scoreColor(score);
  }, 50);

  // Recommendation badge
  const recEl = document.getElementById("recommendation-badge");
  const rec = data.recommendation || "待定";
  recEl.textContent = rec;
  if (rec === "推荐") { recEl.style.background = "#d1fae5"; recEl.style.color = "#065f46"; }
  else if (rec === "考虑") { recEl.style.background = "#fef3c7"; recEl.style.color = "#92400e"; }
  else { recEl.style.background = "#fee2e2"; recEl.style.color = "#991b1b"; }

  // Progress bars
  setTimeout(() => {
    document.getElementById("skill-progress").style.width = `${Math.round(skillRate * 100)}%`;
    document.getElementById("skill-progress").style.background = scoreColor(skillRate * 100);
    document.getElementById("exp-progress").style.width = `${Math.round(expRate * 100)}%`;
    document.getElementById("exp-progress").style.background = scoreColor(expRate * 100);
  }, 100);
  document.getElementById("skill-rate").textContent = `${Math.round(skillRate * 100)}%`;
  document.getElementById("exp-rate").textContent = `${Math.round(expRate * 100)}%`;

  // Skill tags
  renderSkillTags("matched-skills", data.skill_match?.matched || [], "ok");
  renderSkillTags("missing-skills", data.skill_match?.missing || [], "miss");

  // AI analysis
  document.getElementById("ai-analysis").textContent = data.ai_analysis || "暂无分析";

  // Store for export
  state.lastMatchData = data;
}

function scoreColor(score) {
  if (score >= 75) return "#10b981";
  if (score >= 50) return "#f59e0b";
  return "#ef4444";
}

// ─── Export ───────────────────────────────────────────────────────────────────
function exportResult() {
  const exportData = {
    resume: state.resumeData,
    match: state.lastMatchData,
    exported_at: new Date().toISOString(),
  };
  const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `resume_analysis_${state.resumeId || "result"}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

// ─── Step Navigation ──────────────────────────────────────────────────────────
function goToStep(step) {
  state.currentStep = step;

  document.getElementById("section-upload").classList.toggle("hidden", step !== 1);
  document.getElementById("section-result").classList.toggle("hidden", step !== 2);
  document.getElementById("section-match").classList.toggle("hidden", step !== 3);

  for (let i = 1; i <= 3; i++) {
    const el = document.getElementById(`step-nav-${i}`);
    el.classList.remove("active", "done");
    if (i < step) el.classList.add("done");
    else if (i === step) el.classList.add("active");
  }

  window.scrollTo({ top: 0, behavior: "smooth" });
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function showAlert(id, msg) {
  const el = document.getElementById(id);
  el.textContent = msg;
  el.classList.remove("hidden");
}

function hideAlert(id) {
  document.getElementById(id).classList.add("hidden");
}

function setLoading(btnId, textId, spinnerId, loading) {
  const btn = document.getElementById(btnId);
  btn.disabled = loading;
  document.getElementById(textId).style.opacity = loading ? "0.6" : "1";
  document.getElementById(spinnerId).classList.toggle("hidden", !loading);
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}
