package com.clothes.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material.icons.filled.IosShare
import androidx.compose.material.icons.filled.MoreHoriz
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.clothes.app.OutfitCandidate
import com.clothes.app.OutfitItem
import com.clothes.app.StyleViewModel
import com.clothes.app.UiState
import com.clothes.app.WardrobeItem
import com.clothes.app.asPercent
import com.clothes.app.categoryLabel
import com.clothes.app.ui.components.ClozCard
import com.clothes.app.ui.components.ClozChip
import com.clothes.app.ui.components.ClozGhostButton
import com.clothes.app.ui.components.ClozPrimaryButton
import com.clothes.app.ui.components.ClozRemoteImage
import com.clothes.app.ui.components.ClozTopBar
import com.clothes.app.ui.components.GarmentPlaceholder
import com.clothes.app.ui.components.OutfitPlaceholder
import com.clothes.app.ui.components.ProductRow
import com.clothes.app.ui.components.RoundIconButton
import com.clothes.app.ui.components.ScoreText
import com.clothes.app.ui.components.copyToClipboard
import com.clothes.app.ui.components.openUrl
import com.clothes.app.ui.mock.DemoProducts
import com.clothes.app.ui.mock.DemoReasons
import com.clothes.app.ui.mock.DemoWardrobeItem
import com.clothes.app.ui.theme.ClozColors
import com.clothes.app.ui.theme.ClozDimens

@Composable
fun WardrobeItemDetailScreen(state: UiState, viewModel: StyleViewModel, modifier: Modifier = Modifier) {
    val item = state.selectedWardrobeItem ?: DemoWardrobeItem
    LazyColumn(
        modifier = modifier.fillMaxSize().background(ClozColors.Page).padding(horizontal = ClozDimens.ScreenPadding),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item {
            ClozTopBar("", onBack = viewModel::backFromDetail) {
                IconButton(onClick = {}) { Icon(Icons.Filled.IosShare, null) }
                IconButton(onClick = {}) { Icon(Icons.Filled.MoreHoriz, null) }
            }
        }
        item {
            GarmentPlaceholder(Modifier.fillMaxWidth().height(330.dp), item.title)
        }
        item {
            Text(item.title, color = ClozColors.Ink, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                (item.styleTags + listOf(categoryLabel(item.category))).take(4).forEach { ClozChip(it, selected = false) }
            }
        }
        item {
            ClozCard {
                DetailRow("颜色", item.colors.joinToString("、").ifBlank { "米色" })
                DetailRow("材质", "聚酯纤维")
                DetailRow("适合季节", item.fitTags.joinToString("、").ifBlank { "春 / 秋 / 冬" })
                DetailRow("购买时间", "2024.03")
            }
        }
        item { ClozPrimaryButton("生成搭配", onClick = { viewModel.openStyleLab(item) }) }
    }
}

@Composable
fun OutfitDetailScreen(state: UiState, viewModel: StyleViewModel, modifier: Modifier = Modifier) {
    val score = state.result?.recommendationReport?.finalScore ?: state.result?.outfit?.score ?: 0.92
    LazyColumn(
        modifier = modifier.fillMaxSize().background(ClozColors.Page).padding(horizontal = ClozDimens.ScreenPadding),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item {
            ClozTopBar("搭配详情", onBack = { viewModel.navigate(com.clothes.app.AppRoute.Home) }) {
                IconButton(onClick = viewModel::saveCurrentOutfitFavorite) { Icon(Icons.Filled.FavoriteBorder, null) }
                IconButton(onClick = {}) { Icon(Icons.Filled.IosShare, null) }
            }
        }
        item { ScoreText(score, "适配度") }
        item {
            Box(Modifier.fillMaxWidth().height(430.dp).clip(RoundedCornerShape(22.dp)).background(Color.White)) {
                val image = outfitDetailHeroImage(state)
                if (image == null) {
                    OutfitPlaceholder(Modifier.fillMaxSize())
                } else {
                    ClozRemoteImage(image, Modifier.fillMaxSize(), ContentScale.Crop)
                }
                Column(Modifier.align(Alignment.CenterEnd).padding(12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    RoundIconButton(Icons.Filled.Refresh, "换背景") {}
                    RoundIconButton(Icons.Filled.IosShare, "换姿势") {}
                    RoundIconButton(Icons.Filled.Download, "3D 预览") {}
                }
            }
        }
        item {
            ClozCard {
                Text("穿搭亮点", color = ClozColors.Ink, fontWeight = FontWeight.SemiBold)
                (state.result?.outfit?.whyThisWorks?.take(3) ?: DemoReasons).forEach { reason ->
                    Text("· $reason", color = ClozColors.Muted, style = MaterialTheme.typography.bodySmall)
                }
            }
        }
        item {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                ClozPrimaryButton("一键购买整套", Modifier.weight(1f), onClick = viewModel::openShoppingList)
                ClozPrimaryButton("AI 试穿", Modifier.weight(1f), onClick = viewModel::openTryOn)
            }
        }
    }
}

@Composable
fun ShoppingListScreen(state: UiState, viewModel: StyleViewModel, modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val items = currentItems(state)
    LazyColumn(
        modifier = modifier.fillMaxSize().background(ClozColors.Page).padding(horizontal = ClozDimens.ScreenPadding),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item { ClozTopBar("购物清单", onBack = viewModel::openOutfitDetail) }
        item {
            Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(20.dp)) {
                Text("单品 (${items.size})", color = ClozColors.Lavender, fontWeight = FontWeight.SemiBold)
                Text("套装信息", color = ClozColors.Muted, fontWeight = FontWeight.Bold)
            }
        }
        items(items) { item ->
            ClozCard {
                ProductRow(item) { openUrl(context, item.productUrl) }
            }
        }
        item {
            ClozCard(background = ClozColors.LavenderSoft.copy(alpha = 0.5f)) {
                Text("更多相似推荐", color = ClozColors.Ink, fontWeight = FontWeight.Bold)
                Text("根据你的特征和预算，发现更多适合你的单品。", color = ClozColors.Muted, style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
fun TryOnScreen(state: UiState, viewModel: StyleViewModel, modifier: Modifier = Modifier) {
    LazyColumn(
        modifier = modifier.fillMaxSize().background(ClozColors.Page).padding(horizontal = ClozDimens.ScreenPadding),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            ClozTopBar("AI 试穿", onBack = viewModel::openOutfitDetail) {
                IconButton(onClick = viewModel::retryImage) { Icon(Icons.Filled.Refresh, null) }
                IconButton(onClick = {}) { Icon(Icons.Filled.IosShare, null) }
            }
        }
        item {
            Box(Modifier.fillMaxWidth().height(540.dp).clip(RoundedCornerShape(22.dp)).background(Color.White)) {
                val image = state.result?.tryOnImageUrl
                if (image.isNullOrBlank()) OutfitPlaceholder(Modifier.fillMaxSize()) else ClozRemoteImage(image, Modifier.fillMaxSize(), ContentScale.Crop)
                ClozChip("对比", selected = false, modifier = Modifier.align(Alignment.TopEnd).padding(12.dp))
            }
        }
        item {
            Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                currentItems(state).take(3).forEach { item ->
                    GarmentPlaceholder(Modifier.size(58.dp), categoryLabel(item.category))
                }
                Box(Modifier.size(58.dp).clip(RoundedCornerShape(14.dp)).background(Color.White), contentAlignment = Alignment.Center) {
                    Text("+", color = ClozColors.Muted, style = MaterialTheme.typography.titleLarge)
                }
            }
        }
        item {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                ClozPrimaryButton("保存", Modifier.weight(1f), onClick = viewModel::saveTryOnImage)
                ClozGhostButton("分享", Modifier.weight(1f), onClick = {})
                ClozGhostButton("下载", Modifier.weight(1f), onClick = viewModel::saveTryOnImage)
            }
        }
    }
}

@Composable
private fun DetailRow(label: String, value: String) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
        Text(label, color = ClozColors.Muted)
        Text(value, color = ClozColors.Ink, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
    }
}

fun outfitDetailHeroImage(state: UiState): String? = state.result?.tryOnImageUrl?.takeIf { it.isNotBlank() }

private fun currentOutfit(state: UiState): OutfitCandidate? = state.result?.outfit

private fun currentItems(state: UiState): List<OutfitItem> = currentOutfit(state)?.items ?: DemoProducts
