from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


REMOVED_RUNTIME_PATHS = [
    "server",
    "miniprogram",
    "dist/server",
    "scripts/amazon-login.mjs",
    "scripts/taobao-login.mjs",
]


REMOVED_ENV_KEYS = [
    "PORT",
    "PUBLIC_BASE_URL",
    "SEARCH_PROVIDER",
    "AMAZON_BROWSER_ENABLED",
    "AMAZON_HEADLESS",
    "AMAZON_CHROME_PATH",
    "AMAZON_USER_DATA_DIR",
    "AMAZON_MARKETPLACE_BASE_URL",
    "AMAZON_SEARCH_URL_TEMPLATE",
    "AMAZON_SEARCH_TIMEOUT_MS",
    "TAOBAO_BROWSER_ENABLED",
    "TAOBAO_HEADLESS",
    "TAOBAO_CHROME_PATH",
    "TAOBAO_USER_DATA_DIR",
    "TAOBAO_SEARCH_TIMEOUT_MS",
    "ECOMMERCE_PLATFORMS",
    "ENABLE_DEMO_SEARCH",
    "AUTH_STORE_PATH",
    "AUTH_SESSION_COOKIE_NAME",
    "AUTH_SESSION_MAX_AGE_DAYS",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "GOOGLE_OAUTH_REDIRECT_URI",
    "IMAGE_PROVIDER",
    "ENABLE_OPENAI_IMAGE",
    "OPENAI_API_KEY",
    "OPENAI_IMAGE_MODEL",
    "ARK_API_KEY",
    "ARK_BASE_URL",
    "ARK_IMAGE_MODEL",
    "ARK_IMAGE_SIZE",
    "ARK_WATERMARK",
    "VISION_PROVIDER",
    "ARK_VISION_MODEL",
]


OLD_NODE_BACKEND_PACKAGE_MARKERS = [
    "dist/server/src/index.js",
    "dist/server/tests",
    "server/tests",
    "scripts/amazon-login.mjs",
    "scripts/taobao-login.mjs",
    "server/storage",
]


OLD_README_RUNTIME_MARKERS = [
    "Node.js/TypeScript Demo 后端",
    "Node Demo 后端启动",
    "server/src",
    "server/tests",
    "微信原生小程序",
    "小程序配置",
    "miniprogram/",
    "npm run amazon:login",
    "npm run taobao:login",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3000/web/",
]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def env_keys(relative_path: str) -> set[str]:
    keys = set()
    for line in read_text(relative_path).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _value = stripped.split("=", 1)
        keys.add(key.strip())
    return keys


def test_old_node_runtime_paths_are_removed() -> None:
    existing = [relative for relative in REMOVED_RUNTIME_PATHS if (ROOT / relative).exists()]
    assert existing == [], f"Remove old Node runtime paths: {existing}"


def test_root_package_json_no_longer_describes_node_backend() -> None:
    package_json = ROOT / "package.json"
    if not package_json.exists():
        return

    package_contents = package_json.read_text(encoding="utf-8")
    remaining = [
        marker for marker in OLD_NODE_BACKEND_PACKAGE_MARKERS if marker in package_contents
    ]
    assert remaining == [], f"Remove old Node backend package.json markers: {remaining}"


def test_python_static_debug_app_has_no_node_internal_routes() -> None:
    html = read_text("backend/app/static/index.html")
    javascript = read_text("backend/app/static/app.js")
    combined = f"{html}\n{javascript}"

    assert "/api/v1/style-tasks" in combined, "Static debug app must call Python API routes"
    assert "/static/app.js" in html, "Static debug app must load the Python-hosted app script"
    assert "/internal/" not in combined, "Remove old Node /internal routes from static debug app"
    assert "127.0.0.1:3000" not in combined, "Remove old Node port from static debug app"
    assert "localhost:3000" not in combined, "Remove old Node localhost URL from static debug app"


def test_env_example_is_python_backend_focused() -> None:
    env_example = read_text(".env.example")

    remaining = sorted(env_keys(".env.example") & set(REMOVED_ENV_KEYS))
    assert remaining == [], f"Remove unprefixed old Node env keys: {remaining}"

    assert "STYLE_BACKEND_MODEL_PROVIDER=ark" in env_example, "Document Python model provider env"
    assert "STYLE_BACKEND_ARK_VISION_MODEL=" in env_example, "Document Python Ark vision model env"
    assert "STYLE_BACKEND_ARK_IMAGE_MODEL=" in env_example, "Document Python Ark image model env"


def test_root_readme_documents_python_only_runtime() -> None:
    readme = read_text("README.md")

    assert "Python FastAPI" in readme, "README must document the Python backend"
    assert (
        "uvicorn app.main:app --reload --port 8000" in readme
    ), "README must document the Python backend startup command"

    remaining = [marker for marker in OLD_README_RUNTIME_MARKERS if marker in readme]
    assert remaining == [], f"Remove old runtime docs from README: {remaining}"
