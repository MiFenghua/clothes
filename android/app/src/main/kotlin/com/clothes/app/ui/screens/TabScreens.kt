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
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForwardIos as ArrowForwardIosAuto
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.clothes.app.AppRoute
import com.clothes.app.FavoriteTab
import com.clothes.app.InspirationLook
import com.clothes.app.StyleViewModel
import com.clothes.app.UiState
import com.clothes.app.WardrobeItem
import com.clothes.app.asPercent
import com.clothes.app.categoryLabel
import com.clothes.app.ui.components.ClozCard
import com.clothes.app.ui.components.ClozChip
import com.clothes.app.ui.components.ClozLogo
import com.clothes.app.ui.components.ClozPrimaryButton
import com.clothes.app.ui.components.ClozProgressBar
import com.clothes.app.ui.components.EmptyWardrobeIllustration
import com.clothes.app.ui.components.GarmentPlaceholder
import com.clothes.app.ui.components.MetricColumn
import com.clothes.app.ui.components.ModelFigurePlaceholder
import com.clothes.app.ui.components.OutfitPlaceholder
import com.clothes.app.ui.components.SectionTitle
import com.clothes.app.ui.components.StatusPill
import com.clothes.app.ui.mock.DemoFavorites
import com.clothes.app.ui.mock.DemoLooks
import com.clothes.app.ui.mock.DemoWardrobeItem
import com.clothes.app.ui.theme.ClozColors
import com.clothes.app.ui.theme.ClozDimens

@Composable
fun HomeScreen(state: UiState, viewModel: StyleViewModel, modifier: Modifier = Modifier) {
    LazyColumn(
        modifier = modifier.fillMaxSize().background(ClozColors.Page).padding(horizontal = ClozDimens.ScreenPadding),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item {
            Row(Modifier.fillMaxWidth().padding(top = 12.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                ClozLogo()
                StatusPill(state.backendOnline, onRefresh = viewModel::refreshBackendStatus)
            }
        }
        item {
            Text("你好，今天想尝试\n什么风格的穿搭呢？", color = ClozColors.Ink, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
        }
        item {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                ClozPrimaryButton("上传照片", Modifier.weight(1f), onClick = { viewModel.openStyleLab() })
                ClozPrimaryButton("我的收藏", Modifier.weight(1f), dark = true, onClick = { viewModel.openFavorites() })
            }
        }
        item {
            ClozCard {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                    Text("我的特征分析", color = ClozColors.Ink, fontWeight = FontWeight.Bold)
                    Text("查看 〉", modifier = Modifier.clickable { viewModel.openFeatureAnalysis() }, color = ClozColors.Muted, style = MaterialTheme.typography.labelSmall)
                }
                MetricColumn("适配度", "92%", modifier = Modifier.fillMaxWidth())
                ClozProgressBar(0.92f)
            }
        }
        item { SectionTitle("今日推荐") }
        item {
            Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                DemoLooks.take(3).forEach { look ->
                    MiniLookCard(look, Modifier.width(128.dp)) { viewModel.openOutfitDetail() }
                }
            }
        }
        item {
            ClozCard(background = ClozColors.LavenderSoft.copy(alpha = 0.56f)) {
                Text("今日穿搭建议", color = ClozColors.Ink, fontWeight = FontWeight.SemiBold)
                Text("多云 18-24°C，适合薄外套，早晚注意保暖。", color = ClozColors.Muted, style = MaterialTheme.typography.bodySmall)
            }
        }
        item { Spacer(Modifier.height(16.dp)) }
    }
}

@Composable
fun InspirationScreen(state: UiState, viewModel: StyleViewModel, modifier: Modifier = Modifier) {
    LazyColumn(
        modifier = modifier.fillMaxSize().background(ClozColors.Page).padding(horizontal = ClozDimens.ScreenPadding),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item {
            Row(Modifier.fillMaxWidth().padding(top = 12.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Text("灵感", color = ClozColors.Ink, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
                IconButton(onClick = {}) { Icon(Icons.Filled.Search, null, tint = ClozColors.Ink) }
            }
        }
        item {
            Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("推荐", "通勤", "约会", "旅行", "轻熟").forEachIndexed { index, label -> ClozChip(label, selected = index == 0) }
            }
        }
        items(DemoLooks.chunked(2)) { row ->
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                row.forEach { look -> InspirationTile(look, Modifier.weight(1f)) { viewModel.openOutfitDetail() } }
                if (row.size == 1) Spacer(Modifier.weight(1f))
            }
        }
    }
}

@Composable
fun WardrobeScreen(state: UiState, viewModel: StyleViewModel, modifier: Modifier = Modifier) {
    LazyColumn(
        modifier = modifier.fillMaxSize().background(ClozColors.Page).padding(horizontal = ClozDimens.ScreenPadding),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item {
            Row(Modifier.fillMaxWidth().padding(top = 12.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Text("衣橱", color = ClozColors.Ink, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                Row {
                    IconButton(onClick = {}) { Icon(Icons.Filled.Search, null) }
                    IconButton(onClick = { viewModel.openWardrobeDetail(DemoWardrobeItem) }) { Icon(Icons.Filled.Add, null) }
                }
            }
        }
        item {
            Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(18.dp)) {
                listOf("上衣", "外套", "裤装", "裙装", "鞋包").forEachIndexed { index, label ->
                    Text(label, color = if (index == 0) ClozColors.Lavender else ClozColors.Muted, fontWeight = FontWeight.Bold)
                }
            }
        }
        if (state.wardrobeItems.isEmpty()) {
            item {
                ClozCard {
                    Box(Modifier.fillMaxWidth().height(320.dp), contentAlignment = Alignment.Center) {
                        EmptyWardrobeIllustration()
                    }
                    ClozPrimaryButton("+ 添加单品", onClick = { viewModel.openWardrobeDetail(DemoWardrobeItem) })
                }
            }
        } else {
            items(state.wardrobeItems) { item ->
                WardrobeListItem(item, viewModel)
            }
        }
    }
}

@Composable
fun FavoritesScreen(state: UiState, viewModel: StyleViewModel, modifier: Modifier = Modifier) {
    LazyColumn(
        modifier = modifier.fillMaxSize().background(ClozColors.Page).padding(horizontal = ClozDimens.ScreenPadding),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item { Text("收藏", modifier = Modifier.padding(top = 12.dp), color = ClozColors.Ink, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold) }
        item {
            Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(18.dp)) {
                FavoriteTab.entries.forEach { tab ->
                    Text(
                        tab.label,
                        modifier = Modifier.clickable { viewModel.selectFavoritesTab(tab) },
                        color = if (state.favoritesTab == tab) ClozColors.Lavender else ClozColors.Muted,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }
        }
        item {
            Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("全部", "通勤", "约会", "旅行").forEachIndexed { index, label -> ClozChip(label, selected = index == 0) }
            }
        }
        items(DemoFavorites.chunked(2)) { row ->
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                row.forEach { favorite ->
                    ClozCard(Modifier.weight(1f)) {
                        Box(Modifier.fillMaxWidth().aspectRatio(0.78f)) {
                            OutfitPlaceholder(Modifier.fillMaxSize())
                            Icon(if (favorite.liked) Icons.Filled.Favorite else Icons.Filled.FavoriteBorder, null, tint = ClozColors.Lavender, modifier = Modifier.align(Alignment.TopEnd).padding(8.dp))
                        }
                        Text(favorite.date, color = ClozColors.Muted, style = MaterialTheme.typography.labelSmall)
                    }
                }
                if (row.size == 1) Spacer(Modifier.weight(1f))
            }
        }
        item {
            ClozCard(background = ClozColors.LavenderSoft.copy(alpha = 0.54f)) {
                Text("今日穿搭建议", color = ClozColors.Ink, fontWeight = FontWeight.Bold)
                Text("多云 18-24°C，适合薄外套，早晚注意保暖。", color = ClozColors.Muted, style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
fun ProfileScreen(state: UiState, viewModel: StyleViewModel, modifier: Modifier = Modifier) {
    LazyColumn(
        modifier = modifier.fillMaxSize().background(ClozColors.Page).padding(horizontal = ClozDimens.ScreenPadding),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item {
            Row(Modifier.fillMaxWidth().padding(top = 14.dp), verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.size(58.dp).clip(CircleShape).background(ClozColors.LavenderSoft), contentAlignment = Alignment.Center) {
                    Text("晴", color = ClozColors.Lavender, fontWeight = FontWeight.Bold)
                }
                Column(Modifier.weight(1f).padding(start = 12.dp)) {
                    Text("小晴", color = ClozColors.Ink, fontWeight = FontWeight.SemiBold)
                    Text("编辑个人资料 〉", color = ClozColors.Muted, style = MaterialTheme.typography.labelSmall)
                }
                IconButton(onClick = {}) { Icon(Icons.Filled.Settings, null) }
                IconButton(onClick = {}) { Icon(Icons.Filled.Notifications, null) }
            }
        }
        item {
            ClozCard(background = ClozColors.Lavender) {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                    Column {
                        Text("clozAi 会员", color = Color.White, fontWeight = FontWeight.SemiBold)
                        Text("已解锁 AI 试穿", color = Color.White.copy(alpha = 0.78f), style = MaterialTheme.typography.labelSmall)
                    }
                    ClozChip("去续费", selected = false)
                }
            }
        }
        items(listOf("我的特征分析", "订单记录", "我的尺码", "地址管理", "隐私设置", "帮助与反馈", "关于 clozAi")) { title ->
            ProfileRow(title)
        }
    }
}

@Composable
private fun MiniLookCard(look: InspirationLook, modifier: Modifier = Modifier, onClick: () -> Unit) {
    Column(modifier.clip(RoundedCornerShape(14.dp)).background(Color.White).clickable(onClick = onClick).padding(8.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
        OutfitPlaceholder(Modifier.fillMaxWidth().aspectRatio(0.62f))
        Text(look.scene, color = ClozColors.Muted, style = MaterialTheme.typography.labelSmall, maxLines = 1)
    }
}

@Composable
private fun InspirationTile(look: InspirationLook, modifier: Modifier = Modifier, onClick: () -> Unit) {
    Column(modifier.clip(RoundedCornerShape(14.dp)).background(Color.White).clickable(onClick = onClick).padding(8.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
        OutfitPlaceholder(Modifier.fillMaxWidth().aspectRatio(0.78f),)
        Text(look.title, color = ClozColors.Ink, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            Icon(Icons.Filled.Favorite, null, tint = ClozColors.Like, modifier = Modifier.size(13.dp))
            Text((look.score * 1000).toInt().toString(), color = ClozColors.Muted, style = MaterialTheme.typography.labelSmall)
        }
    }
}

@Composable
private fun WardrobeListItem(item: WardrobeItem, viewModel: StyleViewModel) {
    ClozCard(Modifier.clickable { viewModel.openWardrobeDetail(item) }) {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            GarmentPlaceholder(Modifier.size(76.dp), categoryLabel(item.category))
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(item.title, color = ClozColors.Ink, fontWeight = FontWeight.Bold)
                Text((item.colors + item.styleTags).take(3).joinToString(" / "), color = ClozColors.Muted, style = MaterialTheme.typography.bodySmall)
            }
            Text("搭配", color = ClozColors.Lavender, fontWeight = FontWeight.Bold, modifier = Modifier.clickable { viewModel.openStyleLab(item) })
        }
    }
}

@Composable
private fun ProfileRow(title: String) {
    Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).background(Color.White).padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
        Text(title, modifier = Modifier.weight(1f), color = ClozColors.Ink, fontWeight = FontWeight.Bold)
        Icon(Icons.AutoMirrored.Filled.ArrowForwardIosAuto, null, tint = ClozColors.Line, modifier = Modifier.size(14.dp))
    }
}
