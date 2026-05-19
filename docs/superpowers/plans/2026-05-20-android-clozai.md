# Android clozAi Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the Android native Kotlin Compose client so all 14 approved clozAi design-draft pages exist, match the draft structure, and keep the existing backend style-task flow working.

**Architecture:** Keep `StyleViewModel` and `StyleApi` as the business/data layer. Split the current oversized `MainActivity.kt` UI into `ui/theme`, `ui/components`, `ui/screens`, and `ui/mock`, with `MainActivity.kt` acting only as the app entrypoint and route dispatcher.

**Tech Stack:** Kotlin, Jetpack Compose Material 3, Android Gradle Plugin 8.9.1, Kotlin 2.0.21, existing Java `HttpURLConnection` backend client.

---

## File Structure

- Modify: `android/app/src/main/kotlin/com/clothes/app/MainActivity.kt`
  - Keep `MainActivity`, `ClozAiApp`, snackbar host, scaffold routing, and utility functions that still belong at app shell level.
- Modify: `android/app/src/main/kotlin/com/clothes/app/StyleModels.kt`
  - Add the missing routes and local UI state for login, favorites tab, result subpage, and analysis progress.
- Modify: `android/app/src/main/kotlin/com/clothes/app/StyleViewModel.kt`
  - Add local-only navigation and form actions for login, feature analysis, favorites, detail pages, shopping list, and try-on.
- Create: `android/app/src/main/kotlin/com/clothes/app/ui/theme/ClozTheme.kt`
  - Own color tokens, gradients, theme wrapper, spacing constants, and shared shapes.
- Create: `android/app/src/main/kotlin/com/clothes/app/ui/components/ClozComponents.kt`
  - Own shared buttons, cards, chips, top bars, bottom bar, progress bars, status pill, and image loader.
- Create: `android/app/src/main/kotlin/com/clothes/app/ui/components/ClozPlaceholders.kt`
  - Own Compose-drawn model, garment, outfit, body-outline, empty-state, and sparkle placeholders.
- Create: `android/app/src/main/kotlin/com/clothes/app/ui/mock/ClozMockData.kt`
  - Own static demo looks, favorites, products, wardrobe item detail values, and feature analysis summaries.
- Create: `android/app/src/main/kotlin/com/clothes/app/ui/screens/OnboardingScreens.kt`
  - Own `SplashScreen`, `LoginScreen`, `StyleGoalScreen`, `UploadAnalysisScreen`, and `FeatureAnalysisScreen`.
- Create: `android/app/src/main/kotlin/com/clothes/app/ui/screens/TabScreens.kt`
  - Own `HomeScreen`, `InspirationScreen`, `WardrobeScreen`, `FavoritesScreen`, and `ProfileScreen`.
- Create: `android/app/src/main/kotlin/com/clothes/app/ui/screens/DetailScreens.kt`
  - Own `WardrobeItemDetailScreen`, `OutfitDetailScreen`, `ShoppingListScreen`, and `TryOnScreen`.
- Create: `android/app/src/main/kotlin/com/clothes/app/ui/screens/SystemScreens.kt`
  - Own `ProgressScreen` and `FailureScreen`.

## Task 1: Route And State Model

**Files:**
- Modify: `android/app/src/main/kotlin/com/clothes/app/StyleModels.kt`

- [ ] **Step 1: Add route and tab state types**

Add these declarations near `AppRoute` and the current option models:

```kotlin
enum class AppRoute {
    Splash,
    Login,
    StyleGoal,
    UploadAnalysis,
    FeatureAnalysis,
    Home,
    Inspiration,
    Wardrobe,
    WardrobeDetail,
    OutfitDetail,
    ShoppingList,
    TryOn,
    Favorites,
    Progress,
    Profile,
    Failure,
}

enum class ResultPanel {
    OutfitDetail,
    ShoppingList,
    TryOn,
}

enum class FavoriteTab(val label: String) {
    Outfits("穿搭"),
    Items("单品"),
    Inspiration("灵感"),
}
```

- [ ] **Step 2: Update bottom tabs**

Replace `BottomTabs` with:

```kotlin
val BottomTabs = listOf(
    TabOption(AppRoute.Home, "首页"),
    TabOption(AppRoute.Inspiration, "灵感"),
    TabOption(AppRoute.Wardrobe, "衣橱"),
    TabOption(AppRoute.Profile, "我的"),
)
```

- [ ] **Step 3: Extend `UiState`**

Update `UiState` defaults so launch starts at the splash page and stores local design-only state:

```kotlin
data class UiState(
    val route: AppRoute = AppRoute.Splash,
    val previousRoute: AppRoute = AppRoute.Home,
    val photoUri: Uri? = null,
    val sidePhotoUri: Uri? = null,
    val form: StyleForm = StyleForm(),
    val task: StyleTaskView? = null,
    val result: StyleTaskResult? = null,
    val resultPanel: ResultPanel = ResultPanel.OutfitDetail,
    val wardrobeItems: List<WardrobeItem> = emptyList(),
    val wardrobeDraft: WardrobeDraft = WardrobeDraft(),
    val selectedWardrobeItem: WardrobeItem? = null,
    val backendOnline: Boolean? = null,
    val errorMessage: String? = null,
    val isSubmitting: Boolean = false,
    val isSavingImage: Boolean = false,
    val isLoadingWardrobe: Boolean = false,
    val isSavingWardrobe: Boolean = false,
    val loginPhone: String = "",
    val loginCode: String = "",
    val favoritesTab: FavoriteTab = FavoriteTab.Outfits,
    val notice: String? = null,
)
```

- [ ] **Step 4: Run Android compile**

Run: `cd android; ./gradlew.bat :app:compileDebugKotlin`

Expected: it may fail because the old UI still references removed route names. That confirms the model change is active.

## Task 2: Theme Tokens

**Files:**
- Create: `android/app/src/main/kotlin/com/clothes/app/ui/theme/ClozTheme.kt`
- Modify: `android/app/src/main/kotlin/com/clothes/app/MainActivity.kt`

- [ ] **Step 1: Create theme file**

Create the theme file with these exported tokens:

```kotlin
package com.clothes.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

object ClozColors {
    val Page = Color(0xFFFAFAFD)
    val Paper = Color.White
    val Ink = Color(0xFF16151D)
    val Muted = Color(0xFF777481)
    val Faint = Color(0xFFF5F3FA)
    val Line = Color(0xFFE9E6F0)
    val Lavender = Color(0xFF8B73FF)
    val LavenderDark = Color(0xFF6E58F2)
    val LavenderSoft = Color(0xFFEDE9FF)
    val Lilac = Color(0xFFDCD4FF)
    val Blush = Color(0xFFFFF0F4)
    val Sage = Color(0xFFEAF4EF)
    val Gold = Color(0xFFC59B5F)
    val WeChat = Color(0xFF35C85A)
}

object ClozDimens {
    val ScreenPadding = 18.dp
    val CardRadius = 18.dp
    val SmallRadius = 10.dp
    val PillRadius = 28.dp
    val BottomBarHeight = 68.dp
}

val ClozPrimaryGradient = Brush.horizontalGradient(
    listOf(ClozColors.Lavender, ClozColors.LavenderDark)
)

val ClozSoftGradient = Brush.linearGradient(
    listOf(Color.White, ClozColors.LavenderSoft.copy(alpha = 0.62f), ClozColors.Page)
)

@Composable
fun ClozAiTheme(content: @Composable () -> Unit) {
    val colors = lightColorScheme(
        primary = ClozColors.Lavender,
        secondary = ClozColors.Gold,
        background = ClozColors.Page,
        surface = ClozColors.Paper,
        onPrimary = Color.White,
        onBackground = ClozColors.Ink,
        onSurface = ClozColors.Ink,
    )
    MaterialTheme(colorScheme = colors, content = content)
}
```

- [ ] **Step 2: Update `MainActivity.kt` import**

Remove local color constants and local `ClozAiTheme`; import `com.clothes.app.ui.theme.ClozAiTheme`.

- [ ] **Step 3: Run compile**

Run: `cd android; ./gradlew.bat :app:compileDebugKotlin`

Expected: failures only from old UI functions that still reference removed local theme tokens.

## Task 3: Shared Components

**Files:**
- Create: `android/app/src/main/kotlin/com/clothes/app/ui/components/ClozComponents.kt`
- Create: `android/app/src/main/kotlin/com/clothes/app/ui/components/ClozPlaceholders.kt`

- [ ] **Step 1: Create shared component API**

Create `ClozComponents.kt` with these composable names and signatures:

```kotlin
package com.clothes.app.ui.components

import android.content.Context
import android.graphics.BitmapFactory
import android.net.Uri
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.clothes.app.AppRoute
import com.clothes.app.BottomTabs
import com.clothes.app.ui.theme.ClozColors
import com.clothes.app.ui.theme.ClozDimens
import com.clothes.app.ui.theme.ClozPrimaryGradient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.net.URL

@Composable
fun ClozLogo(modifier: Modifier = Modifier) {
    Row(modifier, verticalAlignment = Alignment.Bottom) {
        Text("cloz", color = ClozColors.Ink, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Light)
        Text("Ai", color = ClozColors.Lavender, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
    }
}

@Composable
fun ClozCard(modifier: Modifier = Modifier, content: @Composable ColumnScope.() -> Unit) {
    Surface(modifier.fillMaxWidth(), shape = RoundedCornerShape(ClozDimens.CardRadius), color = ClozColors.Paper, shadowElevation = 2.dp) {
        Column(Modifier.padding(14.dp), content = content)
    }
}

@Composable
fun ClozPrimaryButton(text: String, modifier: Modifier = Modifier, enabled: Boolean = true, onClick: () -> Unit) {
    Button(onClick = onClick, enabled = enabled, modifier = modifier.fillMaxWidth().height(52.dp), shape = RoundedCornerShape(ClozDimens.PillRadius)) {
        Text(text, fontWeight = FontWeight.Bold)
    }
}

@Composable
fun ClozGhostButton(text: String, modifier: Modifier = Modifier, onClick: () -> Unit) {
    OutlinedButton(onClick = onClick, modifier = modifier.fillMaxWidth().height(48.dp), shape = RoundedCornerShape(ClozDimens.PillRadius)) {
        Text(text, fontWeight = FontWeight.Bold)
    }
}

@Composable
fun ClozChip(text: String, selected: Boolean, modifier: Modifier = Modifier, onClick: (() -> Unit)? = null) {
    Text(
        text = text,
        modifier = modifier
            .clip(RoundedCornerShape(ClozDimens.PillRadius))
            .background(if (selected) ClozColors.Lavender else ClozColors.Paper)
            .border(1.dp, if (selected) ClozColors.Lavender else ClozColors.Line, RoundedCornerShape(ClozDimens.PillRadius))
            .then(if (onClick != null) Modifier.clickable(onClick = onClick) else Modifier)
            .padding(horizontal = 13.dp, vertical = 8.dp),
        color = if (selected) Color.White else ClozColors.Muted,
        fontWeight = FontWeight.Bold,
    )
}

@Composable
fun ClozTopBar(title: String, modifier: Modifier = Modifier, onBack: (() -> Unit)? = null, actions: @Composable RowScope.() -> Unit = {}) {
    Row(modifier.fillMaxWidth().height(44.dp), verticalAlignment = Alignment.CenterVertically) {
        if (onBack != null) IconButton(onClick = onBack) { Icon(Icons.Filled.ArrowBack, contentDescription = "返回") } else Spacer(Modifier.width(8.dp))
        Text(title, modifier = Modifier.weight(1f), color = ClozColors.Ink, fontWeight = FontWeight.Bold)
        actions()
    }
}

@Composable
fun ClozBottomBar(current: AppRoute, onSelected: (AppRoute) -> Unit) {
    NavigationBar(containerColor = ClozColors.Paper, tonalElevation = 0.dp) {
        BottomTabs.forEach { tab ->
            NavigationBarItem(selected = current == tab.route, onClick = { onSelected(tab.route) }, icon = { Icon(tabIcon(tab.route), null) }, label = { Text(tab.label) })
        }
    }
}

@Composable
fun ClozProgressBar(progress: Float, modifier: Modifier = Modifier) {
    LinearProgressIndicator(progress = { progress.coerceIn(0f, 1f) }, modifier = modifier.fillMaxWidth().height(4.dp).clip(RoundedCornerShape(4.dp)), color = ClozColors.Lavender, trackColor = ClozColors.LavenderSoft)
}

@Composable
fun ClozRemoteImage(source: String, modifier: Modifier, contentScale: ContentScale = ContentScale.Crop) {
    val context = LocalContext.current
    var bitmap by remember(source) { mutableStateOf<ImageBitmap?>(null) }
    LaunchedEffect(source) {
        bitmap = if (source.isBlank() || source.startsWith("data:image/svg", true)) null else withContext(Dispatchers.IO) { loadImageBitmap(context, source) }
    }
    if (bitmap != null) Image(bitmap!!, null, modifier, contentScale = contentScale) else Box(modifier.background(ClozColors.LavenderSoft), contentAlignment = Alignment.Center) { Icon(Icons.Filled.AutoAwesome, null, tint = ClozColors.Lavender) }
}
```

Also add `tabIcon(route: AppRoute): ImageVector` and `loadImageBitmap(context: Context, source: String): ImageBitmap?` using the current logic from `MainActivity.kt`.

- [ ] **Step 2: Create placeholder API**

Create `ClozPlaceholders.kt` with these composable names:

```kotlin
package com.clothes.app.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Checkroom
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.clothes.app.ui.theme.ClozColors

@Composable
fun SparkleBackdrop(modifier: Modifier = Modifier) {
    Canvas(modifier.fillMaxSize()) {
        val stroke = Stroke(width = 1.dp.toPx(), cap = StrokeCap.Round)
        drawArc(ClozColors.Lilac.copy(alpha = 0.8f), 205f, 250f, false, topLeft = Offset(size.width * .18f, size.height * .08f), size = Size(size.width * .72f, size.height * .5f), style = stroke)
        listOf(Offset(size.width * .25f, size.height * .28f), Offset(size.width * .77f, size.height * .45f), Offset(size.width * .78f, size.height * .76f)).forEach {
            drawCircle(ClozColors.LavenderSoft, radius = 10.dp.toPx(), center = it)
        }
    }
}

@Composable
fun ModelFigurePlaceholder(modifier: Modifier = Modifier, darkTop: Boolean = false) {
    Column(modifier.clip(RoundedCornerShape(16.dp)).background(Color(0xFFF7F4F0)).padding(12.dp), horizontalAlignment = Alignment.CenterHorizontally) {
        Canvas(Modifier.fillMaxWidth().weight(1f, fill = true)) {
            drawCircle(Color(0xFFFFE4D6), size.minDimension * .08f, Offset(size.width / 2, size.height * .13f))
            drawRoundRect(if (darkTop) Color(0xFF202027) else Color(0xFFF5EFE8), topLeft = Offset(size.width * .36f, size.height * .23f), size = Size(size.width * .28f, size.height * .24f), cornerRadius = androidx.compose.ui.geometry.CornerRadius(18f, 18f))
            drawRoundRect(Color(0xFFD9E4EF), topLeft = Offset(size.width * .32f, size.height * .47f), size = Size(size.width * .14f, size.height * .42f), cornerRadius = androidx.compose.ui.geometry.CornerRadius(16f, 16f))
            drawRoundRect(Color(0xFFD9E4EF), topLeft = Offset(size.width * .54f, size.height * .47f), size = Size(size.width * .14f, size.height * .42f), cornerRadius = androidx.compose.ui.geometry.CornerRadius(16f, 16f))
        }
    }
}

@Composable fun SideFigurePlaceholder(modifier: Modifier = Modifier) = ModelFigurePlaceholder(modifier, darkTop = false)

@Composable
fun BodyOutlinePlaceholder(modifier: Modifier = Modifier) {
    Canvas(modifier.clip(RoundedCornerShape(16.dp)).background(Color.White).padding(18.dp)) {
        val path = Path().apply {
            moveTo(size.width * .5f, size.height * .12f)
            cubicTo(size.width * .36f, size.height * .18f, size.width * .34f, size.height * .42f, size.width * .42f, size.height * .56f)
            lineTo(size.width * .38f, size.height * .88f)
            moveTo(size.width * .5f, size.height * .12f)
            cubicTo(size.width * .64f, size.height * .18f, size.width * .66f, size.height * .42f, size.width * .58f, size.height * .56f)
            lineTo(size.width * .62f, size.height * .88f)
        }
        drawPath(path, ClozColors.Muted.copy(alpha = .7f), style = Stroke(width = 2.dp.toPx(), cap = StrokeCap.Round))
    }
}

@Composable
fun GarmentPlaceholder(modifier: Modifier = Modifier, label: String = "") {
    Box(modifier.clip(RoundedCornerShape(14.dp)).background(Color(0xFFF2EEE8)), contentAlignment = Alignment.Center) {
        Icon(Icons.Filled.Checkroom, null, tint = ClozColors.Lavender)
        if (label.isNotBlank()) Text(label, modifier = Modifier.align(Alignment.BottomCenter).padding(6.dp), color = ClozColors.Muted, fontWeight = FontWeight.Bold)
    }
}

@Composable fun OutfitPlaceholder(modifier: Modifier = Modifier) = ModelFigurePlaceholder(modifier, darkTop = false)

@Composable
fun EmptyWardrobeIllustration(modifier: Modifier = Modifier) {
    Column(modifier, horizontalAlignment = Alignment.CenterHorizontally) {
        Icon(Icons.Filled.Checkroom, null, tint = ClozColors.LavenderSoft, modifier = Modifier.size(64.dp))
        Text("你的衣橱还是空的", color = ClozColors.Muted, textAlign = TextAlign.Center)
    }
}
```

Use stable dimensions in calling screens so hover, loading, and text states cannot resize these placeholder regions.

- [ ] **Step 3: Compile shared components**

Run: `cd android; ./gradlew.bat :app:compileDebugKotlin`

Expected: any errors should be missing imports or unfinished bodies in the new component files; fix those before moving on.

## Task 4: Mock Data

**Files:**
- Create: `android/app/src/main/kotlin/com/clothes/app/ui/mock/ClozMockData.kt`

- [ ] **Step 1: Add demo models and values**

Create mock data using existing domain types:

```kotlin
package com.clothes.app.ui.mock

import com.clothes.app.InspirationLook
import com.clothes.app.OutfitItem
import com.clothes.app.WardrobeItem

data class FeatureMetric(val label: String, val value: String)
data class ProductSuggestion(val item: OutfitItem, val action: String = "去购买")
data class FavoriteLook(val title: String, val date: String, val liked: Boolean)

val DemoFeatureMetrics = listOf(
    FeatureMetric("身高", "168cm"),
    FeatureMetric("体型", "梨形"),
    FeatureMetric("肩宽", "适中"),
    FeatureMetric("腰臀比", "0.72"),
    FeatureMetric("发色", "深棕色"),
)

val DemoStyleKeywords = listOf("清新", "优雅", "简约", "通勤", "显高")

val DemoLooks = listOf(
    InspirationLook("春日通勤 轻盈简约", "通勤", "米白 / 浅蓝", "浅色外套和高腰牛仔裤强化比例。", 0.92),
    InspirationLook("温柔约会 桑蚕感", "约会", "象牙白 / 奶茶", "垂坠面料让整体更轻。", 0.89),
    InspirationLook("周末旅行 松弛感", "旅行", "白 / 蓝 / 灰", "层次清楚，行动方便。", 0.87),
    InspirationLook("极简黑白 显瘦", "日常", "黑 / 白", "上下比例明确，适合复用。", 0.91),
)

val DemoWardrobeItem = WardrobeItem(
    itemId = "demo-outerwear",
    category = "outerwear",
    imageUrl = "",
    title = "米色西装外套",
    colors = listOf("米色"),
    styleTags = listOf("通勤", "质感", "百搭"),
    fitTags = listOf("直筒", "春/秋/冬"),
    notes = "剪裁利落，适合搭配高腰裤。",
)
```

Also add four `OutfitItem` demo product rows for jacket, vest, jeans, and shoes.

- [ ] **Step 2: Compile mock data**

Run: `cd android; ./gradlew.bat :app:compileDebugKotlin`

Expected: unresolved constructor or package errors are fixed before screens use the data.

## Task 5: ViewModel Actions

**Files:**
- Modify: `android/app/src/main/kotlin/com/clothes/app/StyleViewModel.kt`

- [ ] **Step 1: Replace old route targets**

Update old methods:

```kotlin
fun startExperience() {
    _uiState.update { it.copy(route = AppRoute.Login, previousRoute = AppRoute.Splash) }
}

fun finishOnboarding() {
    _uiState.update { it.copy(route = AppRoute.Home, previousRoute = AppRoute.Home, notice = null) }
    refreshBackendStatus()
    loadWardrobe()
}

fun openStyleLab(item: WardrobeItem? = null) {
    _uiState.update {
        it.copy(
            route = AppRoute.UploadAnalysis,
            selectedWardrobeItem = item,
            form = it.form.copy(wardrobeItemIds = item?.itemId.orEmpty()),
            errorMessage = null,
            notice = null,
        )
    }
}
```

- [ ] **Step 2: Add local-only UI actions**

Add these public methods:

```kotlin
fun updateLoginPhone(value: String) {
    _uiState.update { it.copy(loginPhone = value, notice = null) }
}

fun updateLoginCode(value: String) {
    _uiState.update { it.copy(loginCode = value, notice = null) }
}

fun completeLocalLogin() {
    _uiState.update { it.copy(route = AppRoute.StyleGoal, previousRoute = AppRoute.Login, notice = null) }
}

fun selectSidePhoto(uri: Uri) {
    _uiState.update { it.copy(sidePhotoUri = uri, notice = null, errorMessage = null) }
}

fun openFeatureAnalysis() {
    _uiState.update { it.copy(route = AppRoute.FeatureAnalysis, previousRoute = AppRoute.UploadAnalysis) }
}

fun openOutfitDetail() {
    _uiState.update { it.copy(route = AppRoute.OutfitDetail, resultPanel = ResultPanel.OutfitDetail) }
}

fun openShoppingList() {
    _uiState.update { it.copy(route = AppRoute.ShoppingList, resultPanel = ResultPanel.ShoppingList) }
}

fun openTryOn() {
    _uiState.update { it.copy(route = AppRoute.TryOn, resultPanel = ResultPanel.TryOn) }
}

fun openFavorites(tab: FavoriteTab = _uiState.value.favoritesTab) {
    _uiState.update { it.copy(route = AppRoute.Favorites, favoritesTab = tab) }
}

fun selectFavoritesTab(tab: FavoriteTab) {
    _uiState.update { it.copy(favoritesTab = tab) }
}
```

- [ ] **Step 3: Update task completion route**

In `finishTask`, replace `route = AppRoute.Result` with:

```kotlin
route = AppRoute.OutfitDetail
```

- [ ] **Step 4: Compile ViewModel changes**

Run: `cd android; ./gradlew.bat :app:compileDebugKotlin`

Expected: failures should now be limited to screen dispatch references not yet migrated.

## Task 6: Onboarding Screens

**Files:**
- Create: `android/app/src/main/kotlin/com/clothes/app/ui/screens/OnboardingScreens.kt`

- [ ] **Step 1: Create five screen composables**

Create composables with these signatures:

```kotlin
@Composable
fun SplashScreen(state: UiState, viewModel: StyleViewModel, modifier: Modifier = Modifier)

@Composable
fun LoginScreen(state: UiState, viewModel: StyleViewModel, modifier: Modifier = Modifier)

@Composable
fun StyleGoalScreen(state: UiState, viewModel: StyleViewModel, modifier: Modifier = Modifier)

@Composable
fun UploadAnalysisScreen(state: UiState, viewModel: StyleViewModel, modifier: Modifier = Modifier)

@Composable
fun FeatureAnalysisScreen(state: UiState, viewModel: StyleViewModel, modifier: Modifier = Modifier)
```

- [ ] **Step 2: Implement layout content**

Use the design mapping:

- `SplashScreen`: centered logo, `SparkleBackdrop`, black rounded button.
- `LoginScreen`: `ClozLogo`, model placeholder, phone/code fields, lavender verification button, WeChat ghost button.
- `StyleGoalScreen`: style chips, height/weight rows, body shape chips, skin tone swatches, hair color row.
- `UploadAnalysisScreen`: front and side photo cards, local image pickers, analysis progress card, CTA that calls `viewModel.openFeatureAnalysis()` when no real photo is selected and `viewModel.submit()` when photo exists.
- `FeatureAnalysisScreen`: body outline, `DemoFeatureMetrics`, keyword chips, retest button, save link.

- [ ] **Step 3: Compile onboarding screens**

Run: `cd android; ./gradlew.bat :app:compileDebugKotlin`

Expected: no unresolved screen/component names from this file.

## Task 7: Tab Screens

**Files:**
- Create: `android/app/src/main/kotlin/com/clothes/app/ui/screens/TabScreens.kt`

- [ ] **Step 1: Create five tab screen composables**

Create:

```kotlin
@Composable fun HomeScreen(state: UiState, viewModel: StyleViewModel, modifier: Modifier = Modifier)
@Composable fun InspirationScreen(state: UiState, viewModel: StyleViewModel, modifier: Modifier = Modifier)
@Composable fun WardrobeScreen(state: UiState, viewModel: StyleViewModel, modifier: Modifier = Modifier)
@Composable fun FavoritesScreen(state: UiState, viewModel: StyleViewModel, modifier: Modifier = Modifier)
@Composable fun ProfileScreen(state: UiState, viewModel: StyleViewModel, modifier: Modifier = Modifier)
```

- [ ] **Step 2: Implement tab layouts**

Use `ClozCard`, `ClozChip`, `OutfitPlaceholder`, `GarmentPlaceholder`, and mock data:

- Home: logo, greeting, 92% feature card, three daily recommendation cards, weather/suggestion card.
- Inspiration: title, search icon, category chips, two-column grid from `DemoLooks`.
- Wardrobe: category tabs, empty-state illustration if `state.wardrobeItems` is empty, otherwise item cards, add button.
- Favorites: tabs from `FavoriteTab.entries`, filters, two-column favorites grid, weather card.
- Profile: avatar placeholder, Pro card, menu rows, bottom nav route highlighted.

- [ ] **Step 3: Compile tab screens**

Run: `cd android; ./gradlew.bat :app:compileDebugKotlin`

Expected: no unresolved tab screen names.

## Task 8: Detail And Result Screens

**Files:**
- Create: `android/app/src/main/kotlin/com/clothes/app/ui/screens/DetailScreens.kt`

- [ ] **Step 1: Create detail screen composables**

Create:

```kotlin
@Composable fun WardrobeItemDetailScreen(state: UiState, viewModel: StyleViewModel, modifier: Modifier = Modifier)
@Composable fun OutfitDetailScreen(state: UiState, viewModel: StyleViewModel, modifier: Modifier = Modifier)
@Composable fun ShoppingListScreen(state: UiState, viewModel: StyleViewModel, modifier: Modifier = Modifier)
@Composable fun TryOnScreen(state: UiState, viewModel: StyleViewModel, modifier: Modifier = Modifier)
```

- [ ] **Step 2: Implement data fallback helpers**

Inside the file, add helpers:

```kotlin
private fun currentOutfit(state: UiState): OutfitCandidate? = state.result?.outfit
private fun currentItems(state: UiState): List<OutfitItem> = state.result?.outfit?.items ?: DemoProducts
private fun scoreText(state: UiState): String = (state.result?.recommendationReport?.finalScore ?: state.result?.outfit?.score ?: 0.92).asPercent()
```

- [ ] **Step 3: Implement result layouts**

- Item detail: use `state.selectedWardrobeItem ?: DemoWardrobeItem`.
- Outfit detail: large outfit placeholder, score, rationale lines from real result or demo text, buttons for shopping list and try-on.
- Shopping list: product rows from real result or demo products, each with price and “去购买”.
- Try-on: full-page outfit placeholder or remote try-on image, thumbnail strip, save/share actions.

- [ ] **Step 4: Compile detail screens**

Run: `cd android; ./gradlew.bat :app:compileDebugKotlin`

Expected: no unresolved detail screen names.

## Task 9: System Screens And Shell Routing

**Files:**
- Create: `android/app/src/main/kotlin/com/clothes/app/ui/screens/SystemScreens.kt`
- Modify: `android/app/src/main/kotlin/com/clothes/app/MainActivity.kt`

- [ ] **Step 1: Move progress and failure screens**

Create:

```kotlin
@Composable fun ProgressScreen(state: UiState, modifier: Modifier = Modifier)
@Composable fun FailureScreen(state: UiState, viewModel: StyleViewModel, modifier: Modifier = Modifier)
```

Progress keeps the existing task status mapping and design-style card. Failure shows the existing message and buttons to retry or return to upload.

- [ ] **Step 2: Replace `MainActivity.kt` body**

Reduce `MainActivity.kt` to app entry and route dispatch:

```kotlin
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            ClozAiTheme {
                val viewModel: StyleViewModel = viewModel()
                ClozAiApp(viewModel)
            }
        }
    }
}

@Composable
fun ClozAiApp(viewModel: StyleViewModel) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    LaunchedEffect(state.notice) {
        val message = state.notice ?: return@LaunchedEffect
        snackbar.showSnackbar(message)
        viewModel.dismissNotice()
    }
    val bottomRoutes = BottomTabs.map { it.route }.toSet()
    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        containerColor = ClozColors.Page,
        bottomBar = {
            if (state.route in bottomRoutes || state.route == AppRoute.Favorites) {
                ClozBottomBar(current = state.route, onSelected = viewModel::navigate)
            }
        },
    ) { padding ->
        val modifier = Modifier.padding(padding)
        when (state.route) {
            AppRoute.Splash -> SplashScreen(state, viewModel, modifier)
            AppRoute.Login -> LoginScreen(state, viewModel, modifier)
            AppRoute.StyleGoal -> StyleGoalScreen(state, viewModel, modifier)
            AppRoute.UploadAnalysis -> UploadAnalysisScreen(state, viewModel, modifier)
            AppRoute.FeatureAnalysis -> FeatureAnalysisScreen(state, viewModel, modifier)
            AppRoute.Home -> HomeScreen(state, viewModel, modifier)
            AppRoute.Inspiration -> InspirationScreen(state, viewModel, modifier)
            AppRoute.Wardrobe -> WardrobeScreen(state, viewModel, modifier)
            AppRoute.WardrobeDetail -> WardrobeItemDetailScreen(state, viewModel, modifier)
            AppRoute.OutfitDetail -> OutfitDetailScreen(state, viewModel, modifier)
            AppRoute.ShoppingList -> ShoppingListScreen(state, viewModel, modifier)
            AppRoute.TryOn -> TryOnScreen(state, viewModel, modifier)
            AppRoute.Favorites -> FavoritesScreen(state, viewModel, modifier)
            AppRoute.Progress -> ProgressScreen(state, modifier)
            AppRoute.Profile -> ProfileScreen(state, viewModel, modifier)
            AppRoute.Failure -> FailureScreen(state, viewModel, modifier)
        }
    }
}
```

- [ ] **Step 3: Compile full UI**

Run: `cd android; ./gradlew.bat :app:compileDebugKotlin`

Expected: PASS.

## Task 10: Build And Visual Verification

**Files:**
- Modify as needed based on compile and emulator findings.

- [ ] **Step 1: Assemble APK**

Run: `cd android; ./gradlew.bat :app:assembleDebug`

Expected: `BUILD SUCCESSFUL`.

- [ ] **Step 2: Launch emulator smoke test**

Run the existing Android app on an available emulator or device. Navigate through:

`Splash -> Login -> StyleGoal -> UploadAnalysis -> FeatureAnalysis -> Home -> Inspiration -> Wardrobe -> WardrobeDetail -> OutfitDetail -> ShoppingList -> TryOn -> Favorites -> Profile`

Expected: no crashes, no unreadable text clipping on a standard phone viewport, bottom navigation highlights the current tab pages.

- [ ] **Step 3: Capture screenshots**

Capture screenshots for at least:

- Splash
- Login
- StyleGoal
- UploadAnalysis
- FeatureAnalysis
- Home
- Inspiration
- Wardrobe
- WardrobeDetail
- OutfitDetail
- ShoppingList
- TryOn
- Favorites
- Profile

Expected: each page structurally matches the corresponding design draft page.

- [ ] **Step 4: Commit implementation**

Run:

```bash
git add android/app/src/main/kotlin/com/clothes/app docs/superpowers/plans/2026-05-20-android-clozai.md
git commit -m "Implement Android clozAi design screens"
```

Expected: commit succeeds and includes only Android UI implementation files plus this plan.
