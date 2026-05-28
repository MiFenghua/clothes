from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


REMOVED_RUNTIME_PATHS = [
    "server",
    "miniprogram",
    "scripts/amazon-login.mjs",
    "scripts/taobao-login.mjs",
]


REMOVED_ENV_KEYS = [
    "PORT",
    "PUBLIC_BASE_URL",
    "SEARCH_PROVIDER",
    "IMAGE_PROVIDER",
    "OPENAI_API_KEY",
    "OPENAI_IMAGE_MODEL",
    "ARK_API_KEY",
    "ARK_IMAGE_MODEL",
    "ARK_VISION_MODEL",
    "VISION_PROVIDER",
    "AMAZON_BROWSER_ENABLED",
    "TAOBAO_BROWSER_ENABLED",
]


OLD_NODE_BACKEND_PACKAGE_MARKERS = [
    "dist/server/src/index.js",
    "server/tests",
    "express",
    "multer",
    "cors",
    "openai",
    "playwright-core",
    "zod",
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

    assert "/api/v1/style-tasks" in combined
    assert "/static/app.js" in html
    assert "/internal/" not in combined
    assert "127.0.0.1:3000" not in combined
    assert "localhost:3000" not in combined


def test_env_example_is_python_backend_focused() -> None:
    env_example = read_text(".env.example")

    assert "STYLE_BACKEND_MODEL_PROVIDER=ark" in env_example
    assert "STYLE_BACKEND_ARK_VISION_MODEL=" in env_example
    assert "STYLE_BACKEND_ARK_IMAGE_MODEL=" in env_example

    remaining = sorted(env_keys(".env.example") & set(REMOVED_ENV_KEYS))
    assert remaining == [], f"Remove unprefixed old Node env keys: {remaining}"


def test_root_readme_documents_python_only_runtime() -> None:
    readme = read_text("README.md")

    assert "Python FastAPI" in readme
    assert "uvicorn app.main:app --reload --port 8000" in readme
    assert "server/src" not in readme
    assert "Node Demo" not in readme
    assert "miniprogram/" not in readme
    assert "127.0.0.1:3000" not in readme
