const state = {
  taskId: null,
  pollTimer: null,
  activeTab: "flow",
  user: null,
  authMode: "login",
  googleEnabled: false
};

const statusSteps = [
  ["analyzing_photo", "分析照片特征"],
  ["searching_products", "搜索外部电商商品"],
  ["building_outfit", "组合最佳穿搭"],
  ["generating_image", "生成试穿效果图"]
];

const statusOrder = [
  "created",
  "photo_uploaded",
  "validating_photo",
  "analyzing_photo",
  "profile_ready",
  "planning_outfit",
  "searching_products",
  "parsing_products",
  "building_outfit",
  "outfit_ready",
  "generating_image",
  "quality_checking",
  "succeeded"
];

const platformMap = {
  amazon: "Amazon",
  taobao: "淘宝",
  tmall: "天猫",
  jd: "京东",
  pdd: "拼多多",
  demo: "Demo"
};

const $ = (selector) => document.querySelector(selector);

async function requestJson(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    ...options,
    headers: {
      ...(options.headers || {})
    }
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error?.message || "请求失败");
  return body;
}

function setAuthMode(mode) {
  state.authMode = mode;
  const isRegister = mode === "register";
  $("#loginModeButton").classList.toggle("is-active", !isRegister);
  $("#registerModeButton").classList.toggle("is-active", isRegister);
  $("#nameField").hidden = !isRegister;
  $("#authSubmitButton").textContent = isRegister ? "注册并登录" : "登录";
  $("#authPassword").setAttribute("autocomplete", isRegister ? "new-password" : "current-password");
  $("#authMessage").textContent = "";
}

function renderAuthState() {
  const isSignedIn = Boolean(state.user);
  $("#authPanel").hidden = isSignedIn;
  $("#appContent").hidden = !isSignedIn;
  $("#authStatus").hidden = !isSignedIn;
  $("#googleLoginButton").hidden = !state.googleEnabled;

  if (state.user) {
    $("#authUserName").textContent = state.user.name || state.user.email;
  }
}

function showAuthMessage(message) {
  $("#authMessage").textContent = message;
}

async function loadCurrentUser() {
  const body = await requestJson("/api/v1/auth/me");
  state.user = body.user || null;
}

async function loadAuthConfig() {
  const body = await requestJson("/api/v1/auth/config");
  state.googleEnabled = Boolean(body.googleEnabled);
}

function showOAuthRedirectMessage() {
  const status = new URLSearchParams(window.location.search).get("auth");
  if (!status) return;

  const messages = {
    google_success: "Google 登录成功",
    google_failed: "Google 登录失败，请重试",
    google_not_configured: "Google 登录尚未配置 CLIENT_ID 和 CLIENT_SECRET"
  };
  showAuthMessage(messages[status] || "");
  window.history.replaceState({}, "", window.location.pathname);
}

function initAuth() {
  setAuthMode("login");

  $("#loginModeButton").addEventListener("click", () => setAuthMode("login"));
  $("#registerModeButton").addEventListener("click", () => setAuthMode("register"));
  $("#googleLoginButton").addEventListener("click", () => {
    window.location.assign("/api/v1/auth/google");
  });

  $("#logoutButton").addEventListener("click", async () => {
    await requestJson("/api/v1/auth/logout", { method: "POST" });
    state.user = null;
    state.taskId = null;
    clearTimeout(state.pollTimer);
    $("#progressPanel").hidden = true;
    $("#resultPanel").hidden = true;
    renderAuthState();
  });

  $("#authForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const payload = {
      email: String(formData.get("email") || ""),
      password: String(formData.get("password") || "")
    };
    if (state.authMode === "register") {
      payload.name = String(formData.get("name") || "");
    }

    $("#authSubmitButton").disabled = true;
    showAuthMessage(state.authMode === "register" ? "正在注册..." : "正在登录...");
    try {
      const endpoint = state.authMode === "register" ? "/api/v1/auth/register" : "/api/v1/auth/login";
      const body = await requestJson(endpoint, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload)
      });
      state.user = body.user;
      event.currentTarget.reset();
      renderAuthState();
    } catch (error) {
      showAuthMessage(error.message || "登录失败");
    } finally {
      $("#authSubmitButton").disabled = false;
    }
  });

  Promise.all([loadAuthConfig(), loadCurrentUser()])
    .catch((error) => {
      state.user = null;
      showAuthMessage(error.message || "登录状态读取失败");
    })
    .finally(() => {
      renderAuthState();
      showOAuthRedirectMessage();
    });
}

function initTabs() {
  document.querySelectorAll(".tab").forEach((button) => {
    button.addEventListener("click", () => {
      state.activeTab = button.dataset.tab;
      document.querySelectorAll(".tab").forEach((tab) => tab.classList.toggle("is-active", tab === button));
      $("#flowPanel").classList.toggle("is-active", state.activeTab === "flow");
      $("#searchPanel").classList.toggle("is-active", state.activeTab === "search");
    });
  });
}

function initUpload() {
  const input = $("#photoInput");
  const preview = $("#photoPreview");
  const submitButton = $("#submitButton");
  const dropzone = document.querySelector(".dropzone");

  input.addEventListener("change", () => {
    const file = input.files?.[0];
    submitButton.disabled = !file;
    if (!file) return;
    if (file.size > 8 * 1024 * 1024) {
      alert("图片需小于 8MB");
      input.value = "";
      submitButton.disabled = true;
      return;
    }
    preview.src = URL.createObjectURL(file);
    dropzone.classList.add("has-image");
  });
}

function initTaskForm() {
  $("#taskForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    const file = $("#photoInput").files?.[0];
    if (!file) return;
    if (!state.user) {
      renderAuthState();
      return;
    }

    $("#submitButton").disabled = true;
    $("#submitButton").textContent = "创建任务中...";
    $("#resultPanel").hidden = true;
    $("#progressPanel").hidden = false;
    renderProgress({ status: "created", progress: 2, message: "任务已创建" });

    try {
      const response = await fetch("/api/v1/style-tasks", {
        method: "POST",
        credentials: "same-origin",
        body: formData
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.error?.message || "创建任务失败");
      state.taskId = body.taskId;
      pollTask();
    } catch (error) {
      renderNotice(error.message || "创建任务失败");
      resetSubmitButton();
    }
  });
}

async function pollTask() {
  if (!state.taskId) return;
  clearTimeout(state.pollTimer);

  try {
    const response = await fetch(`/api/v1/style-tasks/${state.taskId}`);
    const task = await response.json();
    if (!response.ok) throw new Error(task.error?.message || "查询任务失败");
    renderProgress(task);

    if (task.status === "succeeded") {
      await loadResult();
      resetSubmitButton();
      return;
    }

    if (task.status === "failed") {
      renderNotice(task.userMessage || "生成失败");
      resetSubmitButton();
      return;
    }

    state.pollTimer = setTimeout(pollTask, 1500);
  } catch (error) {
    renderNotice(error.message || "查询任务失败");
    resetSubmitButton();
  }
}

function renderProgress(task) {
  $("#taskStatus").textContent = task.userMessage || task.message || task.status;
  $("#taskProgress").textContent = `${task.progress || 0}%`;
  $("#meterFill").style.width = `${task.progress || 0}%`;

  const currentIndex = statusOrder.indexOf(task.status);
  $("#steps").innerHTML = statusSteps
    .map(([status, label]) => {
      const index = statusOrder.indexOf(status);
      const className = currentIndex === index ? "active" : "";
      const prefix = currentIndex > index ? "已完成" : currentIndex === index ? "进行中" : "等待中";
      return `<li class="${className}">${prefix}：${label}</li>`;
    })
    .join("");
}

async function loadResult() {
  const response = await fetch(`/api/v1/style-tasks/${state.taskId}/result`);
  const result = await response.json();
  if (!response.ok) throw new Error(result.error?.message || "结果加载失败");
  if (result.status === "failed") {
    renderNotice(result.userMessage || "生成失败");
    return;
  }
  renderResult(result);
}

function renderResult(result) {
  const panel = $("#resultPanel");
  panel.hidden = false;
  panel.innerHTML = `
    <img class="try-on" src="${escapeAttribute(result.tryOnImageUrl)}" alt="AI 试穿效果图" />
    <section class="outfit-summary">
      <h2>${escapeHtml(result.outfit.title)}</h2>
      <p>${escapeHtml(result.outfit.reason)}</p>
      <p>${result.outfit.totalPrice > 0 ? `预计合计 ¥${result.outfit.totalPrice}` : "价格以外部电商页面为准"}</p>
    </section>
    <section class="products"></section>
  `;
  renderProducts(panel.querySelector(".products"), result.outfit.items);
}

function renderNotice(message) {
  const panel = $("#resultPanel");
  panel.hidden = false;
  const hint = String(message).includes("商品详情页")
    ? "当前外部电商搜索只能拿到搜索入口链接，试穿图生成需要淘宝/天猫或 Amazon 真实商品详情页和商品主图。"
    : "";
  panel.innerHTML = `<div class="notice">${escapeHtml(message)}${hint ? `<br />${escapeHtml(hint)}` : ""}</div>`;
}

function resetSubmitButton() {
  const button = $("#submitButton");
  button.disabled = !$("#photoInput").files?.[0];
  button.textContent = "生成我的穿搭";
}

function initSearchForm() {
  $("#searchForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const queries = $("#queries").value
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
    const target = $("#searchResults");
    target.innerHTML = `<div class="notice">正在访问外部电商搜索入口...</div>`;

    try {
      const response = await fetch("/internal/search-products", {
        method: "POST",
        credentials: "same-origin",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          queries,
          budget: { min: 300, max: 800 },
          limitPerQuery: 18
        })
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.error?.message || "搜索失败");
      renderProducts(target, body.products);
      if (body.searchIssue) {
        target.insertAdjacentHTML("afterbegin", `<div class="notice">${escapeHtml(body.searchIssue.message)}</div>`);
      }
      if (!body.products?.length && body.searchIssue) {
        target.innerHTML = `<div class="notice">${escapeHtml(body.searchIssue.message)}</div>`;
      }
    } catch (error) {
      target.innerHTML = `<div class="notice">${escapeHtml(error.message || "搜索失败")}</div>`;
    }
  });
}

function renderProducts(container, products) {
  container.innerHTML = "";
  const template = $("#productTemplate");
  products.forEach((product) => {
    const node = template.content.cloneNode(true);
    const img = node.querySelector(".product-image");
    const title = node.querySelector("h3");
    const badge = node.querySelector(".badge");
    const price = node.querySelector(".price");
    const reason = node.querySelector(".reason");
    const copy = node.querySelector(".copy");
    const link = node.querySelector("a");

    img.src = product.imageUrl;
    img.alt = product.title;
    badge.textContent = platformMap[product.platform] || product.platform;
    title.textContent = product.title;
    price.textContent = product.price > 0 ? `¥${product.price}` : product.priceText || "进入电商查看实时价格";
    reason.textContent = product.matchReason || product.reason || "外部电商链接";
    link.href = product.productUrl;
    copy.addEventListener("click", async () => {
      await navigator.clipboard.writeText(product.productUrl);
      copy.textContent = "已复制";
      setTimeout(() => {
        copy.textContent = "复制链接";
      }, 1200);
      if (state.taskId && product.productId) {
        fetch("/api/v1/events/copy-product-link", {
          method: "POST",
          credentials: "same-origin",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ taskId: state.taskId, productId: product.productId })
        }).catch(() => {});
      }
    });
    container.appendChild(node);
  });
}

function escapeHtml(value) {
  return String(value)
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
initUpload();
initTaskForm();
initSearchForm();
initAuth();
