package com.clothes.app.ui.mock

import com.clothes.app.InspirationLook
import com.clothes.app.OutfitItem
import com.clothes.app.WardrobeItem

data class FeatureMetric(val label: String, val value: String)

data class FavoriteLook(
    val title: String,
    val date: String,
    val liked: Boolean = true,
    val score: Double = 0.92,
)

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
    InspirationLook("短风衣与直筒裤", "旅行", "浅卡其 / 暖灰", "行动方便，拍照轮廓完整。", 0.86),
    InspirationLook("针织背心与半裙", "约会", "奶油白 / 雾粉", "柔和材质叠加，突出轻盈感。", 0.88),
)

val DemoFavorites = listOf(
    FavoriteLook("黑白通勤", "05-10 收藏", true, 0.94),
    FavoriteLook("浅蓝休闲", "05-08 收藏", true, 0.91),
    FavoriteLook("米色外套", "05-05 收藏", true, 0.89),
    FavoriteLook("奶白长裙", "04-30 收藏", false, 0.86),
)

val DemoWardrobeItem = WardrobeItem(
    itemId = "demo-outerwear",
    category = "outerwear",
    imageUrl = "",
    title = "米色西装外套",
    colors = listOf("米色"),
    styleTags = listOf("通勤", "质感", "百搭"),
    fitTags = listOf("直筒", "春 / 秋 / 冬"),
    notes = "剪裁利落，适合搭配高腰裤。",
)

val DemoProducts = listOf(
    OutfitItem(
        productId = "demo-jacket",
        marketplace = "taobao",
        category = "outerwear",
        title = "米白西装外套",
        price = 299.0,
        priceText = null,
        imageUrl = "",
        productUrl = "https://example.com/jacket",
        shopName = "UR 官方旗舰店",
        selectionReason = "利落但不厚重，能提升肩线。",
        matchReason = "浅色外套和牛仔蓝形成轻盈通勤感。",
    ),
    OutfitItem(
        productId = "demo-cami",
        marketplace = "taobao",
        category = "top",
        title = "白色针织背心",
        price = 159.0,
        priceText = null,
        imageUrl = "",
        productUrl = "https://example.com/top",
        shopName = "MANGO 官方旗舰店",
        selectionReason = "贴身内搭减少臃肿。",
        matchReason = "和外套同色系，保持上半身干净。",
    ),
    OutfitItem(
        productId = "demo-jeans",
        marketplace = "taobao",
        category = "bottom",
        title = "浅蓝色高腰牛仔裤",
        price = 299.0,
        priceText = null,
        imageUrl = "",
        productUrl = "https://example.com/jeans",
        shopName = "MO&Co.",
        selectionReason = "高腰线优化比例。",
        matchReason = "阔腿裤型平衡梨形身材。",
    ),
    OutfitItem(
        productId = "demo-shoes",
        marketplace = "taobao",
        category = "shoes",
        title = "白色粗跟小白鞋",
        price = 239.0,
        priceText = null,
        imageUrl = "",
        productUrl = "https://example.com/shoes",
        shopName = "自营鞋履",
        selectionReason = "低跟好走，适合通勤。",
        matchReason = "白色鞋面呼应上装，视觉更完整。",
    ),
)

val DemoReasons = listOf(
    "浅色西装削弱正式感，和牛仔裤组合更适合日常通勤。",
    "高腰阔腿裤拉长下半身比例，减少梨形身材的重心下沉。",
    "白色内搭和鞋子形成上下呼应，让整体更轻盈。",
)
