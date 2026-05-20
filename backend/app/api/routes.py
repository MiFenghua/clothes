from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, HTTPException, UploadFile

from app.providers.google_auth import GoogleAuthNotConfiguredError, GoogleTokenVerificationError
from app.providers.product_content import build_home_view
from app.schemas.auth import AuthResponse, GoogleLoginRequest, PublicUser
from app.schemas.domain import Budget, Marketplace, ProductCategory, Scene, StylePreferences, StyleTaskRequest, WardrobeItem
from app.schemas.product import FavoriteType, HomeView, InspirationPage, ProfileView, StyleProfileUpdate, StyleProfileView
from app.schemas.results import StyleTaskResult, StyleTaskView
from app.services.container import AppContainer, get_container

router = APIRouter()


def container_dependency() -> AppContainer:
    return get_container()


def bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()


def current_user(
    container: Annotated[AppContainer, Depends(container_dependency)],
    authorization: Annotated[str | None, Header()] = None,
) -> PublicUser | None:
    return container.auth_store.get_user_by_token(bearer_token(authorization))


@router.get("/health")
async def health(container: Annotated[AppContainer, Depends(container_dependency)]) -> dict:
    return {
        "ok": True,
        "service": container.settings.app_name,
        "graph": container.graph.manifest().__dict__,
    }


@router.post("/api/v1/auth/google", response_model=AuthResponse)
async def login_with_google(
    payload: GoogleLoginRequest,
    container: Annotated[AppContainer, Depends(container_dependency)],
) -> AuthResponse:
    try:
        profile = container.google_id_token_verifier.verify(payload.id_token)
    except GoogleAuthNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail="Google login is not configured") from exc
    except GoogleTokenVerificationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    if not profile.email_verified:
        raise HTTPException(status_code=401, detail="Google email is not verified")

    try:
        user = container.auth_store.upsert_google_user(profile)
        session = container.auth_store.create_session(user.user_id)
    except ValueError as exc:
        detail = str(exc)
        if "verified" in detail.lower():
            raise HTTPException(status_code=401, detail="Google email is not verified") from exc
        raise HTTPException(status_code=409, detail=detail) from exc
    return AuthResponse(user=user, session=session)


@router.get("/api/v1/auth/me")
async def get_current_auth_user(user: Annotated[PublicUser | None, Depends(current_user)]) -> dict[str, PublicUser | None]:
    return {"user": user}


@router.post("/api/v1/auth/logout")
async def logout(
    container: Annotated[AppContainer, Depends(container_dependency)],
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, bool]:
    container.auth_store.destroy_session(bearer_token(authorization))
    return {"ok": True}


@router.get("/api/v1/profile", response_model=ProfileView)
async def get_profile(
    container: Annotated[AppContainer, Depends(container_dependency)],
    user: Annotated[PublicUser | None, Depends(current_user)],
) -> ProfileView:
    profile = container.profile_repository.get(_owner_id(user), _display_name(user))
    return ProfileView(user=user, style_profile=profile)


@router.put("/api/v1/profile/style", response_model=StyleProfileView)
async def update_style_profile(
    payload: StyleProfileUpdate,
    container: Annotated[AppContainer, Depends(container_dependency)],
    user: Annotated[PublicUser | None, Depends(current_user)],
) -> StyleProfileView:
    return container.profile_repository.update(_owner_id(user), payload, _display_name(user))


@router.get("/api/v1/home", response_model=HomeView)
async def get_home(
    container: Annotated[AppContainer, Depends(container_dependency)],
    user: Annotated[PublicUser | None, Depends(current_user)],
) -> HomeView:
    owner_id = _owner_id(user)
    profile = container.profile_repository.get(owner_id, _display_name(user))
    return build_home_view(
        profile=profile,
        tasks=container.task_service.recent_completed_tasks(),
        settings_status={
            "ok": True,
            "search_provider": container.settings.search_provider,
            "image_provider": container.settings.image_provider,
            "model_provider": container.settings.model_provider,
        },
    )


@router.get("/api/v1/inspirations", response_model=InspirationPage)
async def list_inspirations(
    container: Annotated[AppContainer, Depends(container_dependency)],
    user: Annotated[PublicUser | None, Depends(current_user)],
    scene: Scene | None = None,
) -> InspirationPage:
    favorites = container.favorite_repository.list_for_owner(_owner_id(user), FavoriteType.inspiration)
    favorite_ids_by_target = {favorite.target_id: favorite.favorite_id for favorite in favorites}
    return container.inspiration_repository.list(scene=scene, favorite_ids_by_target=favorite_ids_by_target)


@router.post("/api/v1/style-tasks", response_model=StyleTaskView, status_code=201)
async def create_style_task(
    background_tasks: BackgroundTasks,
    photo: Annotated[UploadFile, File()],
    container: Annotated[AppContainer, Depends(container_dependency)],
    user: Annotated[PublicUser | None, Depends(current_user)],
    scene: Annotated[Scene, Form()] = Scene.daily,
    budget_min: Annotated[float | None, Form()] = 300,
    budget_max: Annotated[float | None, Form()] = 800,
    liked_style: Annotated[str | None, Form()] = None,
    avoid: Annotated[str | None, Form()] = None,
    age_years: Annotated[int | None, Form()] = None,
    height_cm: Annotated[int | None, Form()] = None,
    weight_kg: Annotated[int | None, Form()] = None,
    usual_size: Annotated[str | None, Form()] = None,
    wardrobe_item_ids: Annotated[str | None, Form()] = None,
    marketplaces: Annotated[str | None, Form()] = None,
) -> StyleTaskView:
    if not photo.content_type or not photo.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are supported")
    selected_wardrobe_item_ids = _visible_wardrobe_item_ids(
        container,
        user,
        _split_csv(wardrobe_item_ids),
    )
    object_key, photo_url = container.storage.save_file(photo.file, photo.filename or "photo.jpg", photo.content_type)
    request = StyleTaskRequest(
        photo_url=photo_url,
        photo_object_key=object_key,
        scene=scene,
        budget=Budget(min=budget_min, max=budget_max),
        preferences=StylePreferences(
            liked_style=liked_style,
            avoid=avoid,
            age_years=age_years,
            height_cm=height_cm,
            weight_kg=weight_kg,
            usual_size=usual_size,
        ),
        wardrobe_item_ids=selected_wardrobe_item_ids,
        marketplaces=_parse_marketplaces(marketplaces),
    )
    task = container.task_service.create_task(request)
    background_tasks.add_task(container.task_service.run_task, task.task_id)
    return task


@router.get("/api/v1/style-tasks/{task_id}", response_model=StyleTaskView)
async def get_style_task(task_id: str, container: Annotated[AppContainer, Depends(container_dependency)]) -> StyleTaskView:
    try:
        return container.task_service.get_task(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc


@router.get("/api/v1/style-tasks/{task_id}/result", response_model=StyleTaskResult)
async def get_style_task_result(
    task_id: str,
    container: Annotated[AppContainer, Depends(container_dependency)],
) -> StyleTaskResult:
    try:
        return container.task_service.get_result(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="Task result is not ready") from exc


@router.post("/api/v1/style-tasks/{task_id}/retry-image", response_model=StyleTaskView)
async def retry_style_task_image(
    task_id: str,
    background_tasks: BackgroundTasks,
    container: Annotated[AppContainer, Depends(container_dependency)],
) -> StyleTaskView:
    try:
        task = container.task_service.get_task(task_id)
        if task.result is None or task.result.outfit is None:
            raise HTTPException(status_code=409, detail="Task has no approved outfit to retry")
        background_tasks.add_task(container.task_service.retry_image, task_id)
        return container.task_service.get_task(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc


@router.get("/api/v1/style-tasks/{task_id}/trace")
async def get_style_task_trace(task_id: str, container: Annotated[AppContainer, Depends(container_dependency)]) -> dict:
    return {"task_id": task_id, "events": container.tracer.by_task(task_id)}


@router.get("/api/v1/wardrobe-items", response_model=list[WardrobeItem])
async def list_wardrobe_items(
    container: Annotated[AppContainer, Depends(container_dependency)],
    user: Annotated[PublicUser | None, Depends(current_user)],
) -> list[WardrobeItem]:
    return _visible_wardrobe_items(container, user)


@router.post("/api/v1/wardrobe-items", response_model=WardrobeItem, status_code=201)
async def create_wardrobe_item(
    photo: Annotated[UploadFile, File()],
    category: Annotated[ProductCategory, Form()],
    title: Annotated[str, Form()],
    container: Annotated[AppContainer, Depends(container_dependency)],
    user: Annotated[PublicUser | None, Depends(current_user)],
    colors: Annotated[str | None, Form()] = None,
    style_tags: Annotated[str | None, Form()] = None,
    fit_tags: Annotated[str | None, Form()] = None,
    notes: Annotated[str | None, Form()] = None,
) -> WardrobeItem:
    if not photo.content_type or not photo.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are supported")
    object_key, image_url = container.storage.save_file(photo.file, photo.filename or "wardrobe.jpg", photo.content_type)
    item = WardrobeItem(
        item_id=f"wardrobe_{uuid4().hex[:16]}",
        category=category,
        image_url=image_url,
        title=title,
        colors=_split_csv(colors),
        style_tags=_split_csv(style_tags),
        fit_tags=_split_csv(fit_tags),
        notes=notes or object_key,
        owner_id=user.user_id if user else None,
    )
    return container.task_service.save_wardrobe_item(item)


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.replace("，", ",").replace("、", ",").split(",") if part.strip()]


def _visible_wardrobe_items(container: AppContainer, user: PublicUser | None) -> list[WardrobeItem]:
    if user is not None:
        return container.task_service.list_wardrobe_items(user.user_id)
    return [item for item in container.task_service.list_wardrobe_items() if item.owner_id is None]


def _owner_id(user: PublicUser | None) -> str | None:
    return user.user_id if user else None


def _display_name(user: PublicUser | None) -> str:
    return user.name if user else "Style User"


def _visible_wardrobe_item_ids(container: AppContainer, user: PublicUser | None, item_ids: list[str]) -> list[str]:
    if not item_ids:
        return []
    allowed_item_ids = {item.item_id for item in _visible_wardrobe_items(container, user)}
    if any(item_id not in allowed_item_ids for item_id in item_ids):
        raise HTTPException(status_code=403, detail="Wardrobe item is not available")
    return item_ids


def _parse_marketplaces(value: str | None) -> list[Marketplace]:
    if not value:
        return [Marketplace.taobao, Marketplace.tmall, Marketplace.jd, Marketplace.pdd, Marketplace.amazon]
    parsed = []
    for part in _split_csv(value):
        parsed.append(Marketplace(part))
    return parsed
