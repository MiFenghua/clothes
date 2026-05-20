const state = {
  taskId: null,
  pollTimer: null,
  traceTimer: null,
  lastPhotoUrl: null
};

const statusLabels = {
  created: "任务已创建",
  profiling_photo: "照片画像",
  resolving_preferences: "偏好解析",
  scouting_products: "商品检索",
  normalizing_products: "商品清洗",
  composing_outfits: "候选搭配",
  reviewing_outfits: "穿搭质检",
  directing_fashion: "最终推荐",
  generating_candidates: "生成图像",
  checking_image_quality: "图像质检",
  retrying_image_generation: "图像重试",
  partial_succeeded: "部分完成",
  succeeded: "完成",
  failed: "失败"
};

const scoreLabels = {
  final_score: "总适配",
  fit_score: "版型",
  color_score: "配色",
  occasion_score: "场景",
  budget_score: "预算"
};

const $ = (selector) => document.querySelector(selector);

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || body.error || "请求失败");
  }
  return body;
}

function initTabs() {
  document.querySelectorAll(".tab").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((tab) => tab.classList.toggle("is-active", tab === button));
      document.querySelectorAll(".view").forEach((view) => view.classList.remove("is-active"));
      $(`#${button.dataset.view}View`).classList.add("is-active");
      if (button.dataset.view === "wardrobe") loadWardrobe();
      if (button.dataset.view === "trace" && state.taskId) loadTrace();
    });
  });
}

function initPhotoPreview() {
  const input = $("#photoInput");
  const preview = $("#photoPreview");
  const drop = document.querySelector(".photo-drop");
  input.addEventListener("change", () => {
    const file = input.files?.[0];
    if (!file) return;
    state.lastPhotoUrl = URL.createObjectURL(file);
    preview.src = state.lastPhotoUrl;
    drop.classList.add("has-image");
  });
}

function initStyleForm() {
  $("#styleForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    if (!formData.get("photo")) return;

    $("#submitButton").disabled = true;
    $("#submitButton").textContent = "创建任务中...";
    $("#resultPanel").hidden = true;
    $("#progressPanel").hidden = false;
    renderProgress({ status: "created", progress: 2, message: "任务已创建" });

    try {
      const task = await requestJson("/api/v1/style-tasks", {
        method: "POST",
        body: formData
      });
      state.taskId = task.task_id;
      $("#traceTaskId").textContent = task.task_id;
      pollTask();
      startTracePolling();
    } catch (error) {
      renderError(error.message || "创建任务失败");
      resetSubmit();
    }
  });
}

async function pollTask() {
  if (!state.taskId) return;
  clearTimeout(state.pollTimer);
  try {
    const task = await requestJson(`/api/v1/style-tasks/${state.taskId}`);
    renderProgress(task);
    if (["succeeded", "partial_succeeded", "failed"].includes(task.status)) {
      if (task.result) {
        renderResult(task.result);
      } else {
        renderError(task.error || task.message || "任务失败");
      }
      resetSubmit();
      return;
    }
    state.pollTimer = setTimeout(pollTask, 900);
  } catch (error) {
    renderError(error.message || "查询任务失败");
    resetSubmit();
  }
}

function renderProgress(task) {
  $("#taskMessage").textContent = task.message || statusLabels[task.status] || task.status;
  $("#taskStatus").textContent = statusLabels[task.status] || task.status;
  $("#taskProgress").textContent = `${task.progress || 0}%`;
  $("#meterFill").style.width = `${task.progress || 0}%`;
  const current = Object.keys(statusLabels).indexOf(task.status);
  $("#statusList").innerHTML = Object.entries(statusLabels)
    .filter(([status]) => !["created", "failed"].includes(status))
    .slice(0, 10)
    .map(([status, label]) => {
      const index = Object.keys(statusLabels).indexOf(status);
      const prefix = current > index ? "已完成" : current === index ? "进行中" : "等待中";
      return `<li>${prefix}：${escapeHtml(label)}</li>`;
    })
    .join("");
}

function renderResult(result) {
  const panel = $("#resultPanel");
  panel.hidden = false;
  if (result.status === "failed") {
    renderError(result.user_message || "推荐未通过质量闸门。");
    return;
  }
  const outfit = result.outfit;
  const report = result.recommendation_report;
  const imageReport = result.image_quality_report;
  const imageHtml = result.try_on_image_url
    ? `<img src="${escapeAttribute(result.try_on_image_url)}" alt="AI 试穿效果图" />`
    : `<div class="tryon-placeholder">推荐已通过，但试穿图没有通过本人真实感和生成瑕疵质检，因此暂不展示低质图。</div>`;

  panel.innerHTML = `
    <div class="result-grid">
      <div class="tryon-frame">${imageHtml}</div>
      <div class="result-copy">
        <h2>${escapeHtml(outfit.title)}</h2>
        <p>${escapeHtml(result.user_message || "搭配和试穿图均已完成质量审核。")}</p>
        <div class="score-grid">${renderScores(report)}</div>
        <div class="gate-list">${renderGates([...(report?.gates || []), ...(imageReport?.gates || [])])}</div>
      </div>
    </div>
    <h2 class="section-heading">为什么适合你</h2>
    <div class="gate-list">${(report?.why_this_works || outfit.why_this_works || []).map((item) => `<div class="gate passed"><span>${escapeHtml(item)}</span><strong>适配</strong></div>`).join("")}</div>
    <h2 class="section-heading">商品清单</h2>
    <div class="product-list">${outfit.items.map(renderProduct).join("")}</div>
  `;
}

function renderScores(report) {
  if (!report) return "";
  return Object.entries(scoreLabels)
    .map(([key, label]) => {
      const value = Number(report[key] || 0);
      return `<article class="score-card"><span class="score-label">${label}</span><strong class="score-value">${Math.round(value * 100)}</strong></article>`;
    })
    .join("");
}

function renderGates(gates) {
  if (!gates.length) return `<div class="empty">暂无质量闸门报告。</div>`;
  return gates
    .map((gate) => {
      const status = gate.status || "warning";
      const reasons = (gate.reasons || []).slice(0, 2).join("；");
      return `<article class="gate ${escapeAttribute(status)}"><span><strong>${escapeHtml(gate.gate)}</strong><br />${escapeHtml(reasons)}</span><strong>${Math.round((gate.score || 0) * 100)}</strong></article>`;
    })
    .join("");
}

function renderProduct(item) {
  return `
    <article class="product">
      <img src="${escapeAttribute(item.image_url)}" alt="${escapeAttribute(item.title)}" />
      <div>
        <h3>${escapeHtml(item.title)}</h3>
        <p>${escapeHtml(item.match_reason || item.selection_reason || "")}</p>
        <p>${escapeHtml(item.marketplace)} · ${item.price > 0 ? `¥${Math.round(item.price)}` : escapeHtml(item.price_text || "实时价格")}</p>
        <a href="${escapeAttribute(item.product_url)}" target="_blank" rel="noreferrer">打开商品</a>
      </div>
    </article>
  `;
}

function renderError(message) {
  const panel = $("#resultPanel");
  panel.hidden = false;
  panel.innerHTML = `<div class="gate failed"><span>${escapeHtml(message)}</span><strong>未通过</strong></div>`;
}

function resetSubmit() {
  $("#submitButton").disabled = false;
  $("#submitButton").textContent = "生成高可信穿搭";
}

function initWardrobeForm() {
  $("#wardrobeForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    try {
      await requestJson("/api/v1/wardrobe-items", {
        method: "POST",
        body: formData
      });
      event.currentTarget.reset();
      loadWardrobe();
    } catch (error) {
      $("#wardrobeList").innerHTML = `<div class="gate failed"><span>${escapeHtml(error.message)}</span><strong>失败</strong></div>`;
    }
  });
}

async function loadWardrobe() {
  const target = $("#wardrobeList");
  target.innerHTML = `<div class="empty">正在读取衣橱...</div>`;
  try {
    const items = await requestJson("/api/v1/wardrobe-items");
    if (!items.length) {
      target.innerHTML = `<div class="empty">还没有自有单品。上传常穿基础款后，后续推荐可以把它们纳入搭配约束。</div>`;
      return;
    }
    target.innerHTML = items.map((item) => `
      <article class="wardrobe-item">
        <img src="${escapeAttribute(item.image_url)}" alt="${escapeAttribute(item.title)}" />
        <div>
          <h3>${escapeHtml(item.title)}</h3>
          <p>${escapeHtml(item.category)} · ${(item.style_tags || []).map(escapeHtml).join(" / ") || "未标注风格"}</p>
        </div>
      </article>
    `).join("");
  } catch (error) {
    target.innerHTML = `<div class="gate failed"><span>${escapeHtml(error.message)}</span><strong>失败</strong></div>`;
  }
}

function startTracePolling() {
  clearInterval(state.traceTimer);
  loadTrace();
  state.traceTimer = setInterval(loadTrace, 1600);
}

async function loadTrace() {
  if (!state.taskId) return;
  try {
    const body = await requestJson(`/api/v1/style-tasks/${state.taskId}/trace`);
    const events = body.events || [];
    $("#traceTaskId").textContent = state.taskId;
    $("#traceList").innerHTML = events.length
      ? events.slice().reverse().map((event) => `
        <article class="trace-event">
          <strong>${escapeHtml(event.node)} · ${escapeHtml(event.event)}</strong>
          <code>${escapeHtml(JSON.stringify(event.payload, null, 2)).slice(0, 900)}</code>
        </article>
      `).join("")
      : `<div class="empty">等待 Agent trace...</div>`;
  } catch {
    // Trace is diagnostic only; keep the main flow quiet.
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function escapeAttribute(value) {
  return escapeHtml(value);
}

initTabs();
initPhotoPreview();
initStyleForm();
initWardrobeForm();
loadWardrobe();
