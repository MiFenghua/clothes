from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from app.schemas.domain import Scene, TaskStatus
from app.schemas.product import (
    FavoriteCreate,
    FavoriteType,
    FavoriteView,
    FeatureMetric,
    FeatureSummary,
    HomeRecommendation,
    HomeView,
    InspirationLook,
    InspirationPage,
    StyleProfileUpdate,
    StyleProfileView,
    TodaySuggestion,
)
from app.schemas.results import StyleTaskView


def default_profile(display_name: str = "Style User") -> StyleProfileView:
    return StyleProfileView(
        display_name=display_name,
        height_cm=168,
        weight_kg=58,
        body_shape="balanced",
        skin_tone="neutral",
        hair_tone="dark brown",
        style_keywords=["clean", "modern", "relaxed"],
    )


def profile_feature_metrics(profile: StyleProfileView) -> list[FeatureMetric]:
    return [
        FeatureMetric(label="Height", value=f"{profile.height_cm} cm" if profile.height_cm else "Not set"),
        FeatureMetric(label="Body shape", value=profile.body_shape or "Not set"),
        FeatureMetric(label="Skin tone", value=profile.skin_tone or "Not set"),
        FeatureMetric(label="Hair tone", value=profile.hair_tone or "Not set"),
    ]


SEEDED_INSPIRATIONS: list[InspirationLook] = [
    InspirationLook(
        inspiration_id="inspiration_commute_001",
        title="Soft Tailored Commute",
        scene=Scene.commute,
        palette="charcoal, ivory, slate blue",
        note="Structured layers with comfortable shoes for repeat weekday wear.",
        score=0.92,
        image_url="/static/inspirations/commute-soft-tailored.jpg",
    ),
    InspirationLook(
        inspiration_id="inspiration_date_001",
        title="Quiet Dinner Polish",
        scene=Scene.date,
        palette="black, pearl, wine",
        note="A simple column shape with one warmer accent.",
        score=0.9,
        image_url="/static/inspirations/date-quiet-dinner.jpg",
    ),
    InspirationLook(
        inspiration_id="inspiration_travel_001",
        title="Carry-On Weekend",
        scene=Scene.travel,
        palette="olive, white, denim",
        note="Light layers that can rotate across a short trip.",
        score=0.88,
        image_url="/static/inspirations/travel-weekend.jpg",
    ),
    InspirationLook(
        inspiration_id="inspiration_daily_001",
        title="Clean Daily Ease",
        scene=Scene.daily,
        palette="cream, navy, soft grey",
        note="Low-effort basics with enough contrast to feel intentional.",
        score=0.87,
        image_url="/static/inspirations/daily-clean-ease.jpg",
    ),
]


@dataclass
class ProfileRepository:
    profiles: dict[str | None, StyleProfileView] = field(default_factory=dict)

    def get(self, owner_id: str | None, display_name: str) -> StyleProfileView:
        if owner_id not in self.profiles:
            profile = default_profile(display_name)
            self.profiles[owner_id] = profile.model_copy(update={"feature_metrics": profile_feature_metrics(profile)})
        return self.profiles[owner_id]

    def update(self, owner_id: str | None, update: StyleProfileUpdate, display_name: str) -> StyleProfileView:
        current = self.get(owner_id, display_name)
        updated = self._apply_update(current, update, display_name)
        self.profiles[owner_id] = updated
        return updated

    def preview_update(self, owner_id: str | None, update: StyleProfileUpdate, display_name: str) -> StyleProfileView:
        current = self.get(owner_id, display_name)
        return self._apply_update(current, update, display_name)

    def _apply_update(
        self,
        current: StyleProfileView,
        update: StyleProfileUpdate,
        display_name: str,
    ) -> StyleProfileView:
        values = update.model_dump(exclude_unset=True)
        if "display_name" in values and values["display_name"] is None:
            values["display_name"] = display_name
        updated = current.model_copy(update=values)
        return updated.model_copy(update={"feature_metrics": profile_feature_metrics(updated)})


@dataclass
class FavoriteRepository:
    favorites: dict[str | None, dict[str, FavoriteView]] = field(default_factory=dict)

    def list_for_owner(self, owner_id: str | None, favorite_type: FavoriteType | None = None) -> list[FavoriteView]:
        if owner_id is None:
            return []
        owner_favorites = list(self.favorites.get(owner_id, {}).values())
        if favorite_type is None:
            return owner_favorites
        return [favorite for favorite in owner_favorites if favorite.favorite_type == favorite_type]

    def save(self, owner_id: str | None, create: FavoriteCreate) -> FavoriteView:
        if owner_id is None:
            raise PermissionError("Authentication is required for favorites")
        owner_favorites = self.favorites.setdefault(owner_id, {})
        for favorite in owner_favorites.values():
            if favorite.favorite_type == create.favorite_type and favorite.target_id == create.target_id:
                updated = favorite.model_copy(update={"snapshot": create.snapshot})
                owner_favorites[favorite.favorite_id] = updated
                return updated
        favorite = FavoriteView(
            favorite_id=f"favorite_{uuid4().hex[:16]}",
            owner_id=owner_id,
            favorite_type=create.favorite_type,
            target_id=create.target_id,
            snapshot=create.snapshot,
        )
        owner_favorites[favorite.favorite_id] = favorite
        return favorite

    def delete(self, owner_id: str | None, favorite_id: str) -> None:
        if owner_id is None:
            if any(favorite_id in owner_favorites for owner_favorites in self.favorites.values()):
                raise PermissionError("Authentication is required for favorites")
            raise KeyError(f"Favorite not found: {favorite_id}")
        for stored_owner_id, owner_favorites in self.favorites.items():
            if favorite_id not in owner_favorites:
                continue
            if stored_owner_id != owner_id:
                raise PermissionError(f"Favorite belongs to another owner: {favorite_id}")
            owner_favorites.pop(favorite_id)
            return None
        raise KeyError(f"Favorite not found: {favorite_id}")


@dataclass
class InspirationRepository:
    inspirations: list[InspirationLook] = field(default_factory=lambda: list(SEEDED_INSPIRATIONS))

    def list(self, scene: Scene | None, favorite_ids_by_target: dict[str, str]) -> InspirationPage:
        items = [item for item in self.inspirations if scene is None or item.scene == scene]
        return InspirationPage(
            items=[
                item.model_copy(update={"favorite_id": favorite_ids_by_target.get(item.inspiration_id)})
                for item in items
            ],
            next_cursor=None,
        )


def build_home_view(
    profile: StyleProfileView,
    tasks: list[StyleTaskView],
    settings_status: dict[str, object],
) -> HomeView:
    completed_tasks = [
        task
        for task in tasks
        if task.result is not None and task.status in {TaskStatus.succeeded, TaskStatus.partial_succeeded}
    ]
    if completed_tasks:
        recommendations = [
            HomeRecommendation(
                recommendation_id=f"task_{task.task_id}",
                title=task.result.outfit.title if task.result.outfit else "Recent recommendation",
                scene=task.request.scene,
                score=task.result.outfit.score if task.result.outfit else 0.82,
                image_url=task.result.try_on_image_url,
                source_task_id=task.task_id,
            )
            for task in completed_tasks[:6]
        ]
    else:
        recommendations = [
            HomeRecommendation(
                recommendation_id=look.inspiration_id,
                title=look.title,
                scene=look.scene,
                score=look.score,
                image_url=look.image_url,
            )
            for look in SEEDED_INSPIRATIONS[:4]
        ]

    return HomeView(
        feature_summary=FeatureSummary(
            score=0.86,
            title=f"{profile.display_name}'s style profile",
            summary="Clean, modern outfit signals are ready for daily recommendations.",
        ),
        recommendations=recommendations,
        today_suggestion=TodaySuggestion(
            title="Start with one polished base",
            body="Use a clean neutral layer, then add one scene-specific accent.",
        ),
        backend_status=settings_status,
    )
