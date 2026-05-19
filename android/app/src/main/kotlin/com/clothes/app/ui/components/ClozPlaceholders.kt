package com.clothes.app.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Checkroom
import androidx.compose.material.icons.filled.Inventory2
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.CornerRadius
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
        drawArc(
            color = ClozColors.Lilac.copy(alpha = 0.62f),
            startAngle = 205f,
            sweepAngle = 250f,
            useCenter = false,
            topLeft = Offset(size.width * 0.16f, size.height * 0.05f),
            size = Size(size.width * 0.72f, size.height * 0.54f),
            style = Stroke(width = 1.dp.toPx(), cap = StrokeCap.Round),
        )
        listOf(
            Offset(size.width * 0.25f, size.height * 0.28f),
            Offset(size.width * 0.76f, size.height * 0.44f),
            Offset(size.width * 0.78f, size.height * 0.76f),
        ).forEach { center ->
            drawCircle(ClozColors.LavenderSoft, radius = 12.dp.toPx(), center = center)
            drawLine(ClozColors.Lavender.copy(alpha = 0.36f), center.copy(x = center.x - 12.dp.toPx()), center.copy(x = center.x + 12.dp.toPx()), 1.dp.toPx())
            drawLine(ClozColors.Lavender.copy(alpha = 0.36f), center.copy(y = center.y - 12.dp.toPx()), center.copy(y = center.y + 12.dp.toPx()), 1.dp.toPx())
        }
    }
}

@Composable
fun ModelFigurePlaceholder(modifier: Modifier = Modifier, darkTop: Boolean = false) {
    Box(
        modifier
            .clip(RoundedCornerShape(16.dp))
            .background(Color(0xFFF7F4F0))
            .padding(8.dp),
        contentAlignment = Alignment.Center,
    ) {
        Canvas(Modifier.fillMaxSize()) {
            val cx = size.width / 2f
            drawCircle(Color(0xFFFFE4D6), size.minDimension * 0.07f, Offset(cx, size.height * 0.13f))
            drawRoundRect(
                color = Color(0xFF3A302E).copy(alpha = 0.82f),
                topLeft = Offset(cx - size.width * 0.12f, size.height * 0.07f),
                size = Size(size.width * 0.24f, size.height * 0.16f),
                cornerRadius = CornerRadius(60f, 60f),
            )
            drawRoundRect(
                color = if (darkTop) Color(0xFF1E1F25) else Color(0xFFF5EFE8),
                topLeft = Offset(cx - size.width * 0.17f, size.height * 0.24f),
                size = Size(size.width * 0.34f, size.height * 0.24f),
                cornerRadius = CornerRadius(18f, 18f),
            )
            drawRoundRect(
                color = Color(0xFFE8DED4),
                topLeft = Offset(cx - size.width * 0.25f, size.height * 0.25f),
                size = Size(size.width * 0.16f, size.height * 0.36f),
                cornerRadius = CornerRadius(24f, 24f),
            )
            drawRoundRect(
                color = Color(0xFFE8DED4),
                topLeft = Offset(cx + size.width * 0.09f, size.height * 0.25f),
                size = Size(size.width * 0.16f, size.height * 0.36f),
                cornerRadius = CornerRadius(24f, 24f),
            )
            drawRoundRect(
                color = Color(0xFFD9E4EF),
                topLeft = Offset(cx - size.width * 0.18f, size.height * 0.48f),
                size = Size(size.width * 0.15f, size.height * 0.39f),
                cornerRadius = CornerRadius(20f, 20f),
            )
            drawRoundRect(
                color = Color(0xFFD9E4EF),
                topLeft = Offset(cx + size.width * 0.03f, size.height * 0.48f),
                size = Size(size.width * 0.15f, size.height * 0.39f),
                cornerRadius = CornerRadius(20f, 20f),
            )
            drawOval(Color(0xFFEEE7E0), topLeft = Offset(cx - size.width * 0.24f, size.height * 0.87f), size = Size(size.width * 0.18f, size.height * 0.04f))
            drawOval(Color(0xFFEEE7E0), topLeft = Offset(cx + size.width * 0.06f, size.height * 0.87f), size = Size(size.width * 0.18f, size.height * 0.04f))
        }
    }
}

@Composable
fun SideFigurePlaceholder(modifier: Modifier = Modifier) {
    Box(
        modifier
            .clip(RoundedCornerShape(16.dp))
            .background(Color(0xFFF7F4F0))
            .padding(8.dp),
    ) {
        Canvas(Modifier.fillMaxSize()) {
            val cx = size.width / 2f
            drawOval(Color(0xFFFFE4D6), topLeft = Offset(cx - size.width * 0.06f, size.height * 0.08f), size = Size(size.width * 0.12f, size.height * 0.09f))
            drawRoundRect(Color(0xFFE8DED4), topLeft = Offset(cx - size.width * 0.06f, size.height * 0.23f), size = Size(size.width * 0.18f, size.height * 0.29f), cornerRadius = CornerRadius(30f, 30f))
            drawRoundRect(Color(0xFFD9E4EF), topLeft = Offset(cx - size.width * 0.05f, size.height * 0.51f), size = Size(size.width * 0.12f, size.height * 0.37f), cornerRadius = CornerRadius(22f, 22f))
        }
    }
}

@Composable
fun BodyOutlinePlaceholder(modifier: Modifier = Modifier) {
    Canvas(
        modifier
            .clip(RoundedCornerShape(16.dp))
            .background(Color.White)
            .padding(18.dp),
    ) {
        val path = Path().apply {
            moveTo(size.width * 0.50f, size.height * 0.12f)
            cubicTo(size.width * 0.37f, size.height * 0.18f, size.width * 0.35f, size.height * 0.42f, size.width * 0.43f, size.height * 0.56f)
            lineTo(size.width * 0.38f, size.height * 0.88f)
            moveTo(size.width * 0.50f, size.height * 0.12f)
            cubicTo(size.width * 0.63f, size.height * 0.18f, size.width * 0.65f, size.height * 0.42f, size.width * 0.57f, size.height * 0.56f)
            lineTo(size.width * 0.62f, size.height * 0.88f)
        }
        drawPath(path, ClozColors.Muted.copy(alpha = 0.62f), style = Stroke(width = 2.dp.toPx(), cap = StrokeCap.Round))
        drawCircle(ClozColors.Muted.copy(alpha = 0.28f), radius = size.minDimension * 0.055f, center = Offset(size.width * 0.5f, size.height * 0.09f), style = Stroke(width = 2.dp.toPx()))
    }
}

@Composable
fun GarmentPlaceholder(modifier: Modifier = Modifier, label: String = "") {
    Box(
        modifier
            .clip(RoundedCornerShape(14.dp))
            .background(Color(0xFFF2EEE8)),
        contentAlignment = Alignment.Center,
    ) {
        Icon(Icons.Filled.Checkroom, contentDescription = null, tint = ClozColors.Lavender, modifier = Modifier.size(28.dp))
        if (label.isNotBlank()) {
            Text(
                label,
                modifier = Modifier.align(Alignment.BottomCenter).padding(5.dp),
                color = ClozColors.Muted,
                style = MaterialTheme.typography.labelSmall,
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center,
            )
        }
    }
}

@Composable
fun OutfitPlaceholder(modifier: Modifier = Modifier) {
    ModelFigurePlaceholder(modifier = modifier, darkTop = false)
}

@Composable
fun EmptyWardrobeIllustration(modifier: Modifier = Modifier) {
    Column(modifier, horizontalAlignment = Alignment.CenterHorizontally) {
        Box(
            Modifier
                .size(86.dp)
                .clip(RoundedCornerShape(24.dp))
                .background(ClozColors.LavenderSoft.copy(alpha = 0.52f)),
            contentAlignment = Alignment.Center,
        ) {
            Icon(Icons.Filled.Inventory2, contentDescription = null, tint = ClozColors.Lavender.copy(alpha = 0.46f), modifier = Modifier.size(48.dp))
        }
        Text("你的衣橱还是空的", color = ClozColors.Muted, fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 14.dp))
        Text("快去添加你的第一件单品吧", color = ClozColors.Muted.copy(alpha = 0.72f), style = MaterialTheme.typography.bodySmall)
    }
}
