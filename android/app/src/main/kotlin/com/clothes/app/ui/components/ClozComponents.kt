package com.clothes.app.ui.components

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.BitmapFactory
import android.net.Uri
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.Checkroom
import androidx.compose.material.icons.filled.CloudOff
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.OpenInNew
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Style
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.clothes.app.AppRoute
import com.clothes.app.BottomTabs
import com.clothes.app.OutfitItem
import com.clothes.app.asPercent
import com.clothes.app.categoryLabel
import com.clothes.app.platformLabel
import com.clothes.app.ui.theme.ClozColors
import com.clothes.app.ui.theme.ClozDimens
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
fun ClozCard(
    modifier: Modifier = Modifier,
    background: Color = ClozColors.Paper,
    content: @Composable ColumnScope.() -> Unit,
) {
    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(ClozDimens.CardRadius),
        color = background,
        shadowElevation = 2.dp,
        tonalElevation = 0.dp,
    ) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp), content = content)
    }
}

@Composable
fun ClozPrimaryButton(
    text: String,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    dark: Boolean = false,
    onClick: () -> Unit,
) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier.fillMaxWidth().height(52.dp),
        shape = RoundedCornerShape(ClozDimens.PillRadius),
        colors = ButtonDefaults.buttonColors(
            containerColor = if (dark) ClozColors.Ink else ClozColors.Lavender,
            disabledContainerColor = ClozColors.Line,
        ),
    ) {
        Text(text, fontWeight = FontWeight.Bold)
    }
}

@Composable
fun ClozGhostButton(text: String, modifier: Modifier = Modifier, onClick: () -> Unit) {
    OutlinedButton(
        onClick = onClick,
        modifier = modifier.fillMaxWidth().height(48.dp),
        shape = RoundedCornerShape(ClozDimens.PillRadius),
    ) {
        Text(text, fontWeight = FontWeight.Bold, color = ClozColors.Ink)
    }
}

@Composable
fun ClozChip(
    text: String,
    selected: Boolean,
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null,
) {
    Text(
        text = text,
        modifier = modifier
            .clip(RoundedCornerShape(ClozDimens.PillRadius))
            .background(if (selected) ClozColors.Lavender else ClozColors.Paper)
            .border(1.dp, if (selected) ClozColors.Lavender else ClozColors.Line, RoundedCornerShape(ClozDimens.PillRadius))
            .then(if (onClick != null) Modifier.clickable(onClick = onClick) else Modifier)
            .padding(horizontal = 13.dp, vertical = 8.dp),
        color = if (selected) Color.White else ClozColors.Muted,
        style = MaterialTheme.typography.labelMedium,
        fontWeight = FontWeight.Bold,
        maxLines = 1,
    )
}

@Composable
fun ClozTopBar(
    title: String,
    modifier: Modifier = Modifier,
    onBack: (() -> Unit)? = null,
    actions: @Composable RowScope.() -> Unit = {},
) {
    Row(
        modifier = modifier.fillMaxWidth().height(44.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (onBack != null) {
            IconButton(onClick = onBack) { Icon(Icons.Filled.ArrowBack, contentDescription = "返回", tint = ClozColors.Ink) }
        } else {
            Spacer(Modifier.width(8.dp))
        }
        Text(title, modifier = Modifier.weight(1f), color = ClozColors.Ink, fontWeight = FontWeight.Bold)
        actions()
    }
}

@Composable
fun ClozBottomBar(current: AppRoute, onSelected: (AppRoute) -> Unit) {
    NavigationBar(containerColor = ClozColors.Paper, tonalElevation = 0.dp, modifier = Modifier.height(ClozDimens.BottomBarHeight)) {
        BottomTabs.forEach { tab ->
            NavigationBarItem(
                selected = current == tab.route,
                onClick = { onSelected(tab.route) },
                icon = { Icon(tabIcon(tab.route), contentDescription = null) },
                label = { Text(tab.label, maxLines = 1) },
            )
        }
    }
}

@Composable
fun ClozProgressBar(progress: Float, modifier: Modifier = Modifier) {
    LinearProgressIndicator(
        progress = { progress.coerceIn(0f, 1f) },
        modifier = modifier.fillMaxWidth().height(4.dp).clip(RoundedCornerShape(4.dp)),
        color = ClozColors.Lavender,
        trackColor = ClozColors.LavenderSoft,
    )
}

@Composable
fun ClozRemoteImage(source: String, modifier: Modifier, contentScale: ContentScale = ContentScale.Crop) {
    val context = LocalContext.current
    val svgPlaceholder = source.startsWith("data:image/svg", ignoreCase = true)
    var bitmap by remember(source) { mutableStateOf<ImageBitmap?>(null) }
    LaunchedEffect(source) {
        bitmap = if (source.isBlank() || svgPlaceholder) null else withContext(Dispatchers.IO) { loadImageBitmap(context, source) }
    }
    if (bitmap != null) {
        Image(bitmap = bitmap!!, contentDescription = null, modifier = modifier, contentScale = contentScale)
    } else {
        Box(modifier.background(ClozColors.LavenderSoft), contentAlignment = Alignment.Center) {
            Icon(Icons.Filled.AutoAwesome, contentDescription = null, tint = ClozColors.Lavender.copy(alpha = 0.72f))
        }
    }
}

@Composable
fun StatusPill(online: Boolean?, modifier: Modifier = Modifier, onRefresh: (() -> Unit)? = null) {
    val text = when (online) {
        true -> "AI 在线"
        false -> "离线"
        null -> "检测中"
    }
    Row(
        modifier = modifier
            .clip(RoundedCornerShape(18.dp))
            .background(if (online == false) ClozColors.Blush else ClozColors.LavenderSoft)
            .then(if (onRefresh != null) Modifier.clickable(onClick = onRefresh) else Modifier)
            .padding(horizontal = 10.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(5.dp),
    ) {
        Icon(if (online == false) Icons.Filled.CloudOff else Icons.Filled.AutoAwesome, null, modifier = Modifier.size(14.dp), tint = ClozColors.Lavender)
        Text(text, color = ClozColors.Lavender, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
    }
}

@Composable
fun SectionTitle(title: String, trailing: String? = null, modifier: Modifier = Modifier, onTrailing: (() -> Unit)? = null) {
    Row(modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
        Text(title, color = ClozColors.Ink, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.ExtraBold)
        if (trailing != null) {
            Text(
                trailing,
                modifier = if (onTrailing != null) Modifier.clickable(onClick = onTrailing) else Modifier,
                color = ClozColors.Muted,
                style = MaterialTheme.typography.labelMedium,
            )
        }
    }
}

@Composable
fun MetricColumn(label: String, value: String, modifier: Modifier = Modifier) {
    Column(modifier, verticalArrangement = Arrangement.spacedBy(4.dp), horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value, color = ClozColors.Lavender, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.ExtraBold)
        Text(label, color = ClozColors.Muted, style = MaterialTheme.typography.labelSmall)
    }
}

@Composable
fun ProductRow(item: OutfitItem, modifier: Modifier = Modifier, onBuy: () -> Unit = {}) {
    Row(modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
        if (item.imageUrl.isBlank()) {
            GarmentPlaceholder(Modifier.size(70.dp), label = categoryLabel(item.category))
        } else {
            ClozRemoteImage(item.imageUrl, Modifier.size(70.dp).clip(RoundedCornerShape(12.dp)))
        }
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
            Text(item.title, color = ClozColors.Ink, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text(platformLabel(item.marketplace), color = ClozColors.Muted, style = MaterialTheme.typography.labelSmall)
            Text(if (item.price > 0) "￥${item.price.toInt()}" else item.priceText ?: "实时价格", color = ClozColors.Ink, fontWeight = FontWeight.ExtraBold)
        }
        OutlinedButton(onClick = onBuy, shape = RoundedCornerShape(14.dp)) {
            Text("去购买", color = ClozColors.Lavender, style = MaterialTheme.typography.labelMedium)
        }
    }
}

@Composable
fun RoundIconButton(icon: ImageVector, contentDescription: String?, onClick: () -> Unit) {
    IconButton(onClick = onClick, modifier = Modifier.size(38.dp).clip(CircleShape).background(Color.White.copy(alpha = 0.9f))) {
        Icon(icon, contentDescription = contentDescription, tint = ClozColors.Ink, modifier = Modifier.size(18.dp))
    }
}

fun tabIcon(route: AppRoute): ImageVector = when (route) {
    AppRoute.Home -> Icons.Filled.Home
    AppRoute.Inspiration -> Icons.Filled.FavoriteBorder
    AppRoute.Wardrobe -> Icons.Filled.Checkroom
    AppRoute.Profile -> Icons.Filled.Person
    AppRoute.Favorites -> Icons.Filled.Favorite
    AppRoute.StyleGoal -> Icons.Filled.Style
    AppRoute.UploadAnalysis -> Icons.Filled.Add
    AppRoute.TryOn -> Icons.Filled.AutoAwesome
    AppRoute.ShoppingList -> Icons.Filled.CalendarMonth
    AppRoute.FeatureAnalysis -> Icons.Filled.Search
    else -> Icons.Filled.Settings
}

fun loadImageBitmap(context: Context, source: String): ImageBitmap? {
    return runCatching {
        if (source.startsWith("data:image/svg", ignoreCase = true)) return null
        val bytes = when {
            source.startsWith("content://", ignoreCase = true) -> context.contentResolver.openInputStream(Uri.parse(source))?.use { it.readBytes() }
            source.startsWith("data:", ignoreCase = true) -> {
                val encoded = source.substringAfter("base64,", "")
                if (encoded.isBlank()) null else android.util.Base64.decode(encoded, android.util.Base64.DEFAULT)
            }
            else -> URL(source).openStream().use { it.readBytes() }
        } ?: return null
        BitmapFactory.decodeByteArray(bytes, 0, bytes.size)?.asImageBitmap()
    }.getOrNull()
}

fun copyToClipboard(context: Context, text: String) {
    val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
    clipboard.setPrimaryClip(ClipData.newPlainText("clozAi", text))
}

fun openUrl(context: Context, url: String) {
    runCatching {
        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
    }
}

@Composable
fun ScoreText(score: Double, label: String, modifier: Modifier = Modifier) {
    Row(modifier, verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(5.dp)) {
        Text(score.asPercent(), color = ClozColors.Lavender, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.ExtraBold)
        Text(label, color = ClozColors.Muted, modifier = Modifier.padding(bottom = 4.dp), textAlign = TextAlign.Start)
    }
}
