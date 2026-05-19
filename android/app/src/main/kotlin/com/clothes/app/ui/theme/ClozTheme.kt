package com.clothes.app.ui.theme

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
    val Faint = Color(0xFFF6F4FA)
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
    listOf(ClozColors.Lavender, ClozColors.LavenderDark),
)

val ClozSoftGradient = Brush.linearGradient(
    listOf(Color.White, ClozColors.LavenderSoft.copy(alpha = 0.62f), ClozColors.Page),
)

@Composable
fun ClozAiTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = lightColorScheme(
            primary = ClozColors.Lavender,
            secondary = ClozColors.Gold,
            surface = ClozColors.Paper,
            background = ClozColors.Page,
            onPrimary = Color.White,
            onSurface = ClozColors.Ink,
            onBackground = ClozColors.Ink,
        ),
        content = content,
    )
}
