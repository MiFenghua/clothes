package com.clothes.app

import android.net.Uri

data class SceneOption(
    val value: String,
    val label: String,
)

val SceneOptions = listOf(
    SceneOption("daily", "日常"),
    SceneOption("commute", "通勤"),
    SceneOption("date", "约会"),
    SceneOption("travel", "旅行"),
    SceneOption("party", "聚会"),
)

data class CategoryOption(
    val value: String,
    val label: String,
)

val CategoryOptions = listOf(
    CategoryOption("top", "上衣"),
    CategoryOption("outerwear", "外套"),
    CategoryOption("bottom", "裤装"),
    CategoryOption("dress", "裙装"),
    CategoryOption("shoes", "鞋履"),
    CategoryOption("bag", "包袋"),
    CategoryOption("accessory", "配饰"),
)

data class TabOption(
    val route: AppRoute,
    val label: String,
)

val BottomTabs = listOf(
    TabOption(AppRoute.Home, "首页"),
    TabOption(AppRoute.Inspiration, "灵感"),
    TabOption(AppRoute.Wardrobe, "衣橱"),
    TabOption(AppRoute.Profile, "我的"),
)

val StyleGoalOptions = listOf("通勤", "约会", "旅行", "显高显瘦", "清新简约", "温柔质感")
val BodyShapeOptions = listOf("梨形", "沙漏形", "苹果形", "H 形", "倒三角")
val SkinToneOptions = listOf("暖白皮", "冷白皮", "自然肤", "小麦肤")

data class StyleForm(
    val scene: String = "daily",
    val budgetMin: String = "300",
    val budgetMax: String = "800",
    val likedStyle: String = "清新简约,显比例",
    val avoid: String = "",
    val ageYears: String = "",
    val heightCm: String = "",
    val weightKg: String = "",
    val usualSize: String = "",
    val bodyShape: String = "梨形",
    val skinTone: String = "暖白皮",
    val hairTone: String = "深棕色",
    val marketplaces: String = "taobao,tmall,amazon",
    val wardrobeItemIds: String = "",
)

data class WardrobeDraft(
    val photoUri: Uri? = null,
    val title: String = "",
    val category: String = "top",
    val colors: String = "",
    val styleTags: String = "",
    val fitTags: String = "",
    val notes: String = "",
)

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
    val currentUser: PublicUser? = null,
    val profileView: ProfileView? = null,
    val homeView: HomeView? = null,
    val inspirationPage: InspirationPage? = null,
    val favoriteItems: List<FavoriteView> = emptyList(),
    val backendOnline: Boolean? = null,
    val errorMessage: String? = null,
    val isSubmitting: Boolean = false,
    val isSigningIn: Boolean = false,
    val isSavingImage: Boolean = false,
    val isLoadingWardrobe: Boolean = false,
    val isSavingWardrobe: Boolean = false,
    val isLoadingProfile: Boolean = false,
    val isLoadingHome: Boolean = false,
    val isLoadingInspirations: Boolean = false,
    val isLoadingFavorites: Boolean = false,
    val isSavingFavorite: Boolean = false,
    val loginPhone: String = "",
    val loginCode: String = "",
    val favoritesTab: FavoriteTab = FavoriteTab.Outfits,
    val notice: String? = null,
)

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

val FavoriteTab.apiType: String
    get() = when (this) {
        FavoriteTab.Outfits -> "outfit"
        FavoriteTab.Items -> "item"
        FavoriteTab.Inspiration -> "inspiration"
    }

fun StyleForm.toStyleProfile(displayName: String = "Style User", current: StyleProfile? = null): StyleProfile {
    fun String.trimmedOrNull(): String? = trim().takeIf { it.isNotBlank() }

    return StyleProfile(
        displayName = displayName,
        heightCm = heightCm.trimmedOrNull()?.toIntOrNull() ?: current?.heightCm ?: 168,
        weightKg = weightKg.trimmedOrNull()?.toIntOrNull() ?: current?.weightKg ?: 50,
        bodyShape = bodyShape.trimmedOrNull(),
        skinTone = skinTone.trimmedOrNull(),
        hairTone = hairTone.trimmedOrNull(),
        styleKeywords = likedStyle.split(",").map { it.trim() }.filter { it.isNotBlank() },
        featureMetrics = current?.featureMetrics.orEmpty(),
    )
}

data class StyleTaskView(
    val taskId: String,
    val status: String,
    val progress: Int,
    val message: String,
    val result: StyleTaskResult? = null,
    val error: String? = null,
) {
    val isTerminal: Boolean
        get() = status == "succeeded" || status == "partial_succeeded" || status == "failed"
}

data class StyleTaskResult(
    val taskId: String,
    val status: String,
    val outfit: OutfitCandidate?,
    val tryOnImageUrl: String?,
    val recommendationReport: RecommendationReport?,
    val imageQualityReport: ImageQualityReport?,
    val alternativesRejected: List<OutfitCandidate>,
    val userMessage: String?,
)

data class OutfitCandidate(
    val candidateId: String,
    val title: String,
    val items: List<OutfitItem>,
    val totalPrice: Double,
    val score: Double,
    val scoreBreakdown: Map<String, Double>,
    val whyThisWorks: List<String>,
    val whyNotOthers: List<String>,
    val riskFlags: List<String>,
)

data class OutfitItem(
    val productId: String,
    val marketplace: String,
    val category: String,
    val title: String,
    val price: Double,
    val priceText: String?,
    val imageUrl: String,
    val productUrl: String,
    val shopName: String?,
    val selectionReason: String,
    val matchReason: String,
)

data class RecommendationReport(
    val finalScore: Double,
    val fitScore: Double,
    val colorScore: Double,
    val occasionScore: Double,
    val budgetScore: Double,
    val wardrobeScore: Double,
    val gates: List<QualityGateReport>,
    val riskFlags: List<String>,
    val whyThisWorks: List<String>,
    val whyNotOthers: List<String>,
)

data class ImageQualityReport(
    val candidateId: String,
    val overallScore: Double,
    val identityScore: Double,
    val garmentScore: Double,
    val artifactScore: Double,
    val realismScore: Double,
    val gates: List<QualityGateReport>,
    val accepted: Boolean,
    val retryPromptHint: String?,
)

data class QualityGateReport(
    val gate: String,
    val status: String,
    val score: Double,
    val reasons: List<String>,
    val blocking: Boolean,
)

data class WardrobeItem(
    val itemId: String,
    val category: String,
    val imageUrl: String,
    val title: String,
    val colors: List<String>,
    val styleTags: List<String>,
    val fitTags: List<String>,
    val notes: String?,
)

data class InspirationLook(
    val title: String,
    val scene: String,
    val palette: String,
    val note: String,
    val score: Double,
    val inspirationId: String = "",
    val imageUrl: String? = null,
    val favoriteId: String? = null,
)

data class FeatureMetric(
    val label: String,
    val value: String,
)

data class StyleProfile(
    val displayName: String,
    val heightCm: Int?,
    val weightKg: Int?,
    val bodyShape: String?,
    val skinTone: String?,
    val hairTone: String?,
    val styleKeywords: List<String>,
    val featureMetrics: List<FeatureMetric>,
)

data class ProfileView(
    val user: PublicUser?,
    val styleProfile: StyleProfile,
)

data class FeatureSummary(
    val score: Double,
    val title: String,
    val summary: String,
)

data class HomeRecommendation(
    val recommendationId: String,
    val title: String,
    val scene: String,
    val score: Double,
    val imageUrl: String?,
    val sourceTaskId: String?,
)

fun HomeRecommendation.toInspirationLook(): InspirationLook {
    return InspirationLook(
        title = title,
        scene = scene,
        palette = "",
        note = "",
        score = score,
        inspirationId = recommendationId,
        imageUrl = imageUrl,
    )
}

data class TodaySuggestion(
    val title: String,
    val body: String,
)

data class HomeView(
    val featureSummary: FeatureSummary,
    val recommendations: List<HomeRecommendation>,
    val todaySuggestion: TodaySuggestion,
    val backendStatus: Map<String, String>,
)

data class InspirationPage(
    val items: List<InspirationLook>,
    val nextCursor: String?,
)

data class FavoriteView(
    val favoriteId: String,
    val ownerId: String?,
    val favoriteType: String,
    val targetId: String,
    val snapshotTitle: String?,
)

val InspirationLooks = listOf(
    InspirationLook("浅色西装与高腰牛仔裤", "通勤", "米白 / 浅蓝 / 象牙白", "利落但不生硬，适合办公室到咖啡约会的连续场景。", 0.92),
    InspirationLook("针织背心与缎面半裙", "约会", "奶油白 / 雾粉 / 银灰", "柔和材质叠加，突出轻盈感和女性化比例。", 0.89),
    InspirationLook("短风衣与直筒长裤", "旅行", "浅卡其 / 墨绿 / 暖灰", "方便行走，层次稳定，拍照时轮廓更完整。", 0.86),
    InspirationLook("黑色薄针织与阔腿白裤", "日常", "黑 / 白 / 香槟金", "极简配色提高质感，适合衣橱复用。", 0.91),
)
