# Full Product Backend Integration Design Spec

Date: 2026-05-20

## Scope

Complete the Android-to-Python-backend product loop for the native clozAi app. The existing backend already supports Google auth, style task creation, task polling, result retrieval, try-on image retry, and wardrobe upload/list flows. This pass adds the missing backend-backed product surfaces that are still represented by Android local mock data:

- Home recommendations and today suggestion.
- Inspiration feed.
- Favorites for outfits, items, and inspiration looks.
- User profile and style profile summary.

The target client is `android/`. The target backend is `backend/`, because the Android app defaults to `http://10.0.2.2:8000` and already uses the Python FastAPI backend for the main agent flow. The Node.js demo backend remains out of scope for the Android product path.

## Confirmed Approach

Use the Python backend as the single Android product API. Add stable FastAPI contracts and local repository implementations first, so the whole app can run end-to-end without PostgreSQL or paid model providers. Keep repository boundaries small enough that the local storage can later be replaced by PostgreSQL without changing Android contracts.

Android should stop treating the main product pages as static mock-only views. The UI can retain design-matched fallback placeholders when a backend call fails, but normal successful paths must read from backend APIs.

## Backend API

Add these API groups under `/api/v1`.

### Profile

`GET /api/v1/profile`

Returns the current user's product profile. If there is no authenticated user, return an anonymous default profile rather than failing, because the app still supports local exploration.

Response:

```json
{
  "user": null,
  "style_profile": {
    "display_name": "Style User",
    "height_cm": 168,
    "weight_kg": 50,
    "body_shape": "pear",
    "skin_tone": "warm fair",
    "hair_tone": "dark brown",
    "style_keywords": ["clean", "commute", "proportion"],
    "feature_metrics": [
      { "label": "Height", "value": "168cm" }
    ]
  }
}
```

`PUT /api/v1/profile/style`

Updates the persisted style profile summary from Android onboarding inputs. This endpoint should accept only lightweight profile fields, not uploaded photos. Photo-derived analysis remains owned by style tasks.

### Home

`GET /api/v1/home`

Returns home screen content:

- `feature_summary`: match score and short body/style summary.
- `recommendations`: recent successful or partial style task outfits when available, otherwise seeded local recommendation cards.
- `today_suggestion`: short outfit/weather-style suggestion text.
- `backend_status`: useful provider flags for display or diagnostics.

### Inspirations

`GET /api/v1/inspirations?scene=<optional>&cursor=<optional>`

Returns a paged list of inspiration looks. The initial implementation can use seeded local looks shaped like production data. Each look should include title, scene, palette, note, score, image URL or null, and favorite state for the current user.

### Favorites

`GET /api/v1/favorites?type=outfit|item|inspiration`

Returns favorites scoped to the current user when authenticated, or anonymous favorites for local exploration.

`POST /api/v1/favorites`

Creates or refreshes a favorite.

Request:

```json
{
  "favorite_type": "outfit",
  "target_id": "task_123",
  "snapshot": {}
}
```

`DELETE /api/v1/favorites/{favorite_id}`

Removes a favorite. The endpoint must reject deletion of another user's favorite.

## Backend Storage

Add focused repositories instead of putting product-page state in `TaskService`.

- `ProfileRepository`: stores style profile records by owner id, plus an anonymous local profile.
- `InspirationRepository`: returns seeded inspiration data and optional favorite annotations.
- `FavoriteRepository`: stores favorite records by owner id and type.
- Existing `InMemoryWardrobeRepository`: remains the wardrobe source, but can be reused when building item favorites and home summaries.
- Existing `InMemoryTaskRepository`: remains task scoped. It should expose list helpers for recent completed tasks so home/favorites can show real outfit history.

Default implementation can be in memory for this pass. If a small JSON file is already used for auth, product repositories may use the same local-storage pattern only if it stays simple and testable. PostgreSQL-backed repositories are out of scope for this pass.

## Data Models

Add Pydantic schemas for the new product surfaces:

- `StyleProfileView`
- `FeatureMetric`
- `HomeView`
- `HomeRecommendation`
- `TodaySuggestion`
- `InspirationLook`
- `FavoriteType`
- `FavoriteCreate`
- `FavoriteView`

Use snake_case JSON names to match the existing backend and Android parser style. Avoid returning Android-only layout concepts. The backend should return product facts; Compose decides layout.

## Android Integration

Add StyleApi methods for:

- `getProfile()`
- `updateStyleProfile(...)`
- `getHome()`
- `getInspirations(scene)`
- `getFavorites(type)`
- `saveFavorite(type, targetId, snapshot)`
- `deleteFavorite(favoriteId)`

Extend `UiState` with backend-backed fields:

- `profile`
- `home`
- `inspirations`
- `favorites`
- loading flags for each product surface

Update screens as follows:

- `HomeScreen`: render backend `HomeView` recommendations and today suggestion. Use existing visual placeholders only when image URLs are missing.
- `InspirationScreen`: render backend inspiration looks instead of `DemoLooks`.
- `FavoritesScreen`: render backend favorites for the selected tab instead of `DemoFavorites`.
- `ProfileScreen`: render backend user/profile values instead of fixed local copy.
- `FeatureAnalysisScreen`: render `StyleProfileView.feature_metrics` and `style_keywords` instead of `DemoFeatureMetrics` and `DemoStyleKeywords`.
- `WardrobeScreen` and task/result screens keep their current backend behavior, with small parser/model updates only if shared models require them.

Android should keep local fallback data only as an error or empty-state fallback, not as the normal source after backend calls succeed.

## Data Flow

1. App starts and restores any auth session from `AuthSessionStore`.
2. `StyleViewModel` refreshes current user, backend health, profile, home data, and wardrobe.
3. Home and profile render backend data when available.
4. Inspiration and favorites are loaded when their tabs are opened.
5. Creating a style task remains unchanged. When a task completes, the result can be surfaced by home recommendations and can be favorited.
6. Saving a favorite stores a backend record with a compact snapshot so the favorites page can render even if the original source object is later unavailable.
7. Logging out clears local auth state and reloads anonymous profile/home/favorites.

## Auth And Scoping

All new endpoints should accept missing auth and return anonymous local data when that makes sense. Mutating endpoints should scope writes to:

- `owner_id = current user id` when authenticated.
- `owner_id = null` for anonymous local exploration.

Deletion and updates must verify that the current caller can see the target record. This should match the wardrobe scoping pattern already implemented for uploaded wardrobe items.

## Error Handling

Backend:

- Return 404 for missing records.
- Return 403 for records outside the caller's scope.
- Return 422 for invalid favorite types or malformed profile updates.
- Keep anonymous read endpoints successful where possible.

Android:

- Do not block the main task flow if product-page calls fail.
- Keep the previous loaded data when refresh fails.
- Show a short `notice` for product-page failures.
- Use existing visual placeholders for missing image URLs.

## Testing And Verification

Backend tests should cover:

- Profile default response for anonymous callers.
- Profile update and retrieval for authenticated users.
- Home response includes seeded recommendations when no tasks exist.
- Home response can include a completed style task result.
- Inspiration list returns stable data and respects scene filtering.
- Favorites create/list/delete behavior for anonymous callers.
- Favorites are scoped between two authenticated users.
- Deleting another user's favorite is rejected.

Android verification should include:

- Gradle compile or assemble.
- Parser tests or focused unit coverage where practical for new JSON shapes.
- Manual navigation through Home, Inspiration, Favorites, Profile, and Feature Analysis with backend running.
- Smoke test that style task creation, polling, result display, wardrobe upload/list, and retry image still work.

## Out Of Scope

- PostgreSQL implementation for the new product repositories.
- Production content management for inspirations.
- Real weather API integration.
- Billing, subscriptions, orders, checkout, shipping, address management, notifications, or settings pages.
- Replacing all Compose placeholders with production image assets.
- Node.js demo backend parity.
