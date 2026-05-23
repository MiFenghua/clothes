# clozAi Android App

这是面向女性用户的原生 Android App。客户端以设计稿的白色、浅紫、轻质感视觉为基础，用 Kotlin + Jetpack Compose 实现完整产品页面，并直接对接 Python agent backend。

## 本地运行

1. 启动 Python backend：

```bash
cd backend
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

2. 用 Android Studio 打开 `android/` 目录并运行 `app`。

模拟器默认访问：

```text
http://10.0.2.2:8000
```

配置项在 `app/src/main/res/values/strings.xml`：

```xml
<string name="api_base_url">http://10.0.2.2:8000</string>
```

真机调试时把它改成电脑局域网 IP 或已部署 HTTPS 域名。

## App 能力

- 完整页面：启动页、个人建档、首页推荐、灵感流、AI 试穿、衣橱、单品详情、进度、搭配详情和我的。
- 原生上传全身照，填写场景、预算、身高、尺码、身形、肤色、风格目标和避雷项。
- 打通 Python backend 的任务流程：创建任务、轮询多 Agent 状态、获取结果、重试试穿图。
- 打通衣橱流程：上传衣物照片、保存单品、拉取衣橱列表，并可围绕指定单品生成搭配。
- 结果页展示适配分、本人相似度、衣物还原分、搭配理由、试穿图和商品清单。
- 支持保存试穿图、复制或打开商品链接。

本地 backend 默认把图片 URL 生成为 `http://127.0.0.1:8000/objects/...`；Android 客户端会自动把本机 URL 映射成 `api_base_url`，因此模拟器使用 `10.0.2.2` 时也能加载上传图和生成图。

## 真实 Provider

生产效果依赖 backend 配置：

```env
STYLE_BACKEND_SEARCH_PROVIDER=taobao_union
STYLE_BACKEND_IMAGE_PROVIDER=ark
STYLE_BACKEND_MODEL_PROVIDER=ark
STYLE_BACKEND_ARK_API_KEY=...
STYLE_BACKEND_TAOBAO_UNION_APP_KEY=...
STYLE_BACKEND_TAOBAO_UNION_APP_SECRET=...
STYLE_BACKEND_TAOBAO_UNION_ADZONE_ID=...
STYLE_BACKEND_MAX_IMAGE_ATTEMPTS=2
STYLE_BACKEND_IMAGE_CANDIDATES_PER_ATTEMPT=3
```

没有 Ark key 时 backend 会回退到 local provider，App 仍可跑通主流程。
