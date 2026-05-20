# clothes

AI 搭配师 Agent Demo：原生 Android App + Python 多 Agent 后端 + Node.js/TypeScript Demo 后端。

## 项目结构

```text
miniprogram/        微信原生小程序页面
web/                浏览器 Web 测试端
backend/            Python FastAPI、多 Agent 图、推荐和图像质量门禁
server/src/         Node.js/TypeScript Demo 后端
server/tests/       后端基础测试
android/            Kotlin Compose 原生 Android App
```

## Python Agent Backend

原生 Android App 默认对接 Python backend：

```bash
cd backend
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

真实 provider 配置：

```env
STYLE_BACKEND_SEARCH_PROVIDER=browser
STYLE_BACKEND_IMAGE_PROVIDER=ark
STYLE_BACKEND_MODEL_PROVIDER=ark
STYLE_BACKEND_ARK_API_KEY=...
STYLE_BACKEND_MAX_IMAGE_ATTEMPTS=2
STYLE_BACKEND_IMAGE_CANDIDATES_PER_ATTEMPT=3
```

未配置 Ark key 时会回退到 local provider，便于本地跑通 App 流程。

## Node Demo 后端启动

```bash
npm install
npm run build
npm start
```

开发时也可以直接：

```bash
npm run dev
```

默认服务地址：`http://127.0.0.1:3000`。
Web 测试端地址：`http://127.0.0.1:3000/web/`。
接口健康检查为 `http://127.0.0.1:3000/health`。

复制 `.env.example` 为 `.env` 后可配置：

- `OPENAI_API_KEY`：启用 GPT Image 2 试穿图生成。
- `OPENAI_IMAGE_MODEL`：默认 `gpt-image-2`。
- `ENABLE_OPENAI_IMAGE=true`：允许后端调用 OpenAI Images API。
- `SEARCH_PROVIDER=hybrid`：商品源模式，支持 `amazon-browser`、`taobao-browser`、`external`、`demo`、`hybrid`。
- `SEARCH_PROVIDER=amazon-browser`：用本机 Chrome 搜索 Amazon 商品页并解析真实商品卡片、ASIN、主图和详情链接。
- `AMAZON_HEADLESS=true`：后端搜索默认无头运行；登录、地区选择或人机验证请用 `npm run amazon:login` 打开可见浏览器。
- `AMAZON_MARKETPLACE_BASE_URL=https://www.amazon.com`：Amazon 站点，可换成其他 marketplace 域名。
- `AMAZON_SEARCH_URL_TEMPLATE=`：可选搜索模板，支持 `{query}`；例如指定店铺商品台时可配置成带 `me=SELLER_ID` 的 Amazon 搜索 URL。
- `AMAZON_USER_DATA_DIR=server/storage/amazon-browser-profile`：Amazon 登录态、地区和 cookie 保存目录。
- `SEARCH_PROVIDER=taobao-browser`：用本机 Chrome 模拟用户搜索淘宝并解析商品卡片。
- `TAOBAO_HEADLESS=true`：后端搜索默认无头运行；登录/验证请用 `npm run taobao:login` 打开可见浏览器。
- `TAOBAO_USER_DATA_DIR=server/storage/taobao-browser-profile`：淘宝登录态和 cookie 保存目录。
- `ECOMMERCE_PLATFORMS=amazon,taobao,jd,pdd`：外部电商搜索入口。
- `ENABLE_DEMO_SEARCH=true`：保留本地 Demo 商品候选，便于外部站点反爬时兜底。
- `AUTH_STORE_PATH=server/storage/auth-store.json`：本地注册用户和登录会话的文件存储位置。
- `AUTH_SESSION_COOKIE_NAME=clothes_session`、`AUTH_SESSION_MAX_AGE_DAYS=30`：登录 session cookie 名称和有效期。
- `GOOGLE_CLIENT_ID`、`GOOGLE_CLIENT_SECRET`：启用 Google OAuth 登录；需要在 Google Cloud Console 配置授权回调地址。
- `GOOGLE_OAUTH_REDIRECT_URI`：可选，默认是 `${PUBLIC_BASE_URL}/api/v1/auth/google/callback`，本机调试通常配置为 `http://127.0.0.1:3000/api/v1/auth/google/callback`。
- `IMAGE_PROVIDER=ark`：优先使用火山方舟/豆包图片生成。
- `ARK_API_KEY`：火山方舟 API Key。
- `ARK_IMAGE_MODEL=doubao-seedream-5-0-260128`：豆包图片模型。
- `ARK_IMAGE_SIZE=2K`、`ARK_WATERMARK=true`：豆包图片生成参数。
- `VISION_PROVIDER=ark`：使用豆包视觉模型做照片分析。
- `ARK_VISION_MODEL=doubao-seed-1-6-vision-250815`：豆包视觉模型。

没有配置可用图片 provider，或没有拿到真实淘宝/天猫/Amazon 商品详情和商品图时，任务会按 PRD 返回失败提示，不展示 mock 试穿图。

## 小程序配置

用微信开发者工具导入 `miniprogram/` 目录。开发环境里请把 `miniprogram/utils/config.js` 的 `API_BASE_URL` 指向后端地址。

## Web 测试端

浏览器打开 `http://127.0.0.1:3000/web/`。Web 端保留两类测试：

- 完整流程：上传照片、创建任务、轮询进度、展示成功结果或失败提示。
- 商品搜索：直接访问外部电商搜索入口，验证 Amazon、淘宝、京东、拼多多链接。

## Android App

`android/` 是 Kotlin Compose 原生 App，默认连接 `http://10.0.2.2:8000`，也就是 Android 模拟器访问电脑本机 Python backend 的地址。客户端已覆盖启动建档、首页推荐、灵感、AI 试穿、衣橱、单品详情、搭配结果和我的页面，并打通任务创建/轮询/结果/重试与衣橱上传/列表接口。

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

然后用 Android Studio 打开 `android/` 目录运行 `app`。真机调试需要把 `android/app/src/main/res/values/strings.xml` 里的 `api_base_url` 改成电脑局域网 IP 或线上 HTTPS 地址。

## Amazon 搜索登录

后端会用 Playwright + 本机 Chrome 搜索 Amazon 商品结果，并从结果卡片里提取可用于试穿参考的商品主图和详情页链接。首次使用或触发人机验证时运行：

```bash
npm run amazon:login
```

在打开的 Chrome 窗口里完成 Amazon 登录、地区选择或验证码。会话会保存在 `server/storage/amazon-browser-profile`，后续后端会复用这套 cookie 搜索商品。

如果需要只搜某个 Amazon 店铺/卖家商品，可以在 `.env` 里配置 `AMAZON_SEARCH_URL_TEMPLATE`。模板中的 `{query}` 会替换为编码后的搜索词，例如：

```env
AMAZON_SEARCH_URL_TEMPLATE=https://www.amazon.com/s?me=SELLER_ID&marketplaceID=ATVPDKIKX0DER&k={query}
```

## 淘宝搜索登录

没有官方 API 时，后端会用 Playwright + 本机 Chrome 模拟用户搜索淘宝。首次使用前运行：

```bash
npm run taobao:login
```

在打开的 Chrome 窗口里登录淘宝并完成验证。登录态会保存在 `server/storage/taobao-browser-profile`，后续后端会复用这套 cookie 搜索商品。若淘宝再次要求验证，重新运行该命令。

登录完成后，回到运行 `npm run taobao:login` 的终端按 Enter，让脚本关闭 Chrome 并释放 profile。登录窗口一直开着时，后端无法复用同一个 `taobao-browser-profile`。

## 已实现范围

- 上传照片、场景/预算/年龄/身高体重/偏好表单。
- Web 端邮箱密码注册/登录、退出登录、Google OAuth 登录入口和 HttpOnly session cookie。
- 任务创建、状态轮询、结果/失败查询。
- 小程序前端与 Web 测试端并存。
- 后端状态机和 Agent 编排骨架。
- Ark/豆包视觉 provider，默认模型 `doubao-seed-1-6-vision-250815`，用于用户照片结构化分析，并直接输出 `recommendedOutfitStrategy` 商品搜索关键词。
- Amazon 浏览器搜索 provider：搜索 Amazon 商品结果，提取真实商品标题、ASIN、主图和详情链接。
- 淘宝浏览器搜索 provider：模拟用户打开淘宝搜索页，提取真实商品标题、价格、主图和详情链接。
- 商品搜索 provider 抽象、外部电商搜索入口与 Demo 兜底候选。
- 试穿图生成前强校验商品来源：必须是淘宝/天猫或 Amazon 实际商品详情页，并带商品图；搜索入口、平台 logo 和 Demo 兜底图不会用于生成试穿图。
- Ark/豆包图片 provider，默认模型 `doubao-seedream-5-0-260128`。
- Ark/豆包图片请求会传入参考图：用户上传照 + 入选电商商品图；本地用户照会自动转为 base64 data URL。
- GPT Image 2 图片 provider，按官方 Images API 的 `images.edit` 方式接入。
- 复制外部电商商品/搜索链接埋点。

## 验证

```bash
npm test
npm run typecheck
```
