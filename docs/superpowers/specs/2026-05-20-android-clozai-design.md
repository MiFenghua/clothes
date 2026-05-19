# Android clozAi Design Spec

Date: 2026-05-20

## Scope

Implement the full Android native Kotlin Compose client to match the provided 14-screen clozAi design draft. The target client is `android/`. The implementation must preserve the existing Python backend integration for upload, task polling, wardrobe upload, result loading, retry, and image saving.

The login screen is visual and local-state only. Phone, verification code, and WeChat login controls should be rendered according to the design, but they should not call a real authentication API in this pass.

Images should use local static demo data and Compose-drawn placeholders first. Real backend result data should replace demo content when available.

## Confirmed Pages

1. `SplashScreen`: launch page with white and pale lavender background, subtle sparkle path, centered `clozAi`, short product copy, and black primary start button.
2. `LoginScreen`: welcome/login page with logo, greeting copy, model placeholder, phone input, verification-code button, WeChat login button, and agreement copy.
3. `StyleGoalScreen`: style goal setup with capsule style choices, body basics, height and weight controls, body shape, skin tone, hair tone, and next button.
4. `UploadAnalysisScreen`: upload photos and AI analysis page with front and side photo cards, camera actions, analysis progress card, and checklist rows.
5. `FeatureAnalysisScreen`: personal feature analysis page with body-outline placeholder, height/body type/shoulder/waist-hip/color summary, style keyword chips, retest button, and save link.
6. `HomeScreen`: today recommendation home page with logo, greeting, feature match card, three outfit recommendation cards, suggestion card, and bottom navigation.
7. `InspirationScreen`: inspiration waterfall page with search/action icons, category chips, two-column outfit cards, like counts, and bottom navigation.
8. `WardrobeScreen`: wardrobe page with category tabs, search/add actions, empty state illustration, add item button, and bottom navigation. When wardrobe data exists, show design-consistent item cards.
9. `WardrobeItemDetailScreen`: item detail page with large garment image, tags, attribute rows, share/more actions, and generate-outfit button.
10. `OutfitDetailScreen`: outfit detail page with match score, main outfit figure placeholder, vertical action buttons, highlights, one-click buy button, and shopping bag action.
11. `ShoppingListScreen`: outfit shopping list with tabs, product rows, prices, buy buttons, and similar recommendation entry.
12. `TryOnScreen`: AI try-on page with full-height try-on image placeholder, selected outfit thumbnails, compare/share/refresh/download actions, save and share buttons.
13. `FavoritesScreen`: favorites page with outfit/item/inspiration tabs, filter chips, grid cards, weather suggestion card, and bottom navigation.
14. `ProfileScreen`: profile page with avatar, settings/notification actions, Pro membership card, menu rows, and bottom navigation.

## Architecture

Keep the existing `StyleViewModel`, `StyleApi`, route state, backend health check, task creation, polling, wardrobe save/list, retry, and gallery save behavior.

Split the Compose UI layer into focused packages:

- `ui/theme`: colors, typography helpers, spacing, rounded corners, shadows, and page background values from the design draft.
- `ui/components`: shared logo, buttons, cards, chips, progress bars, bottom navigation, top bars, empty states, product rows, outfit cards, and placeholder figure/garment components.
- `ui/screens`: one screen or tightly-related screen group per confirmed page.
- `ui/mock`: local demo data for home recommendations, inspiration, favorites, products, wardrobe detail, outfit detail, shopping list, and try-on thumbnails.

Refactor `MainActivity.kt` so it primarily wires theme, state collection, scaffold-level navigation, and screen dispatch. It should not continue to contain all UI implementation details.

## Navigation

Use the existing `AppRoute` model as the base, extending it where necessary so every design page has a direct route. Bottom navigation should cover `Home`, `Inspiration`, `Wardrobe`, and `Profile` as shown in the draft. Non-tab detail flows should preserve a back path without resetting the main tab state.

Suggested route additions or mappings:

- `Welcome` becomes `SplashScreen`.
- Add or map `Login`.
- `Onboarding` becomes `StyleGoalScreen`.
- `StyleLab` becomes `UploadAnalysisScreen`.
- Add `FeatureAnalysis`.
- `Result` can branch into `OutfitDetailScreen`, `ShoppingListScreen`, and `TryOnScreen`.
- Add `Favorites`.

## Data Flow

`StyleViewModel` remains the single source of UI state. Add local-only state for login form fields, selected analysis photos, selected style chips, current result subpage, current favorites tab, and demo selection where needed.

Backend-backed pages should prefer real data:

- Upload and task progress use existing API calls.
- Outfit detail, shopping list, and try-on use `StyleTaskResult` when present.
- Wardrobe uses backend wardrobe data when available.

If backend data is absent, empty, or image loading fails, screens should show local demo content or design-matched placeholders so the 14-page visual surface remains complete.

## Visual System

The app should match the design draft's white, soft gray, and lavender visual language:

- Background: near-white page surface with subtle lavender accents.
- Primary action: lavender gradient or solid lavender pill buttons depending on local component fit.
- Secondary action: white pill or outline button with thin gray border.
- Cards: white surfaces, 8 to 18 dp radius depending on the draft shape, very soft shadow, compact padding.
- Chips: pill-shaped, selected state lavender fill or lavender-tinted surface.
- Typography: compact mobile hierarchy, no oversized marketing sections after the splash screen.
- Imagery: local static/demo placeholders drawn to resemble model, garment, and outfit blocks until real assets are available.

## Error Handling

Keep errors lightweight and local:

- Backend offline: status pill or snackbar, without blocking visual exploration.
- Empty login input: local notice only; login still remains local-state in this pass.
- Missing upload photo: local notice asking for a clear full-body photo.
- Task failure: route to failure state or return to upload screen with message.
- Image load failure: design-matched lavender placeholder instead of broken image.

## Testing And Verification

Verification should include:

- Android compile or Gradle assemble for the Compose client.
- Manual or automated emulator navigation through all 14 pages.
- Screenshot checks for key pages against the design draft: splash, login, style goal, upload analysis, feature analysis, home, inspiration, wardrobe, item detail, outfit detail, shopping list, try-on, favorites, profile.
- Smoke test that the existing upload/task/result flow still reaches a result or failure state without UI crashes.

## Out Of Scope

- Real phone verification or WeChat login integration.
- Production image asset sourcing or AI-generated bitmap asset replacement.
- Backend API redesign.
- Full account system, subscription billing, or persistent favorites storage.
