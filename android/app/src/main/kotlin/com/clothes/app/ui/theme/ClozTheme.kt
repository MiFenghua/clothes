package com.clothes.app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

object ClozColors {
    val Page = Color(0xFFF7F7FB)
    val Paper = Color.White
    val Ink = Color(0xFF1F1F26)
    val Body = Color(0xFF4B4B57)
    val Muted = Color(0xFF8A8A99)
    val Placeholder = Color(0xFFB8B8C5)
    val Disabled = Color(0xFFD7D7E0)
    val Faint = Color(0xFFF8F8FA)
    val Line = Color(0xFFECECF2)
    val Border = Color(0xFFE6E3F2)
    val Lavender = Color(0xFF7B61FF)
    val LavenderLight = Color(0xFF9A86FF)
    val LavenderDark = Color(0xFF6550E8)
    val GradientEnd = Color(0xFF6E58F6)
    val LavenderBase = Color(0xFFEEEAFE)
    val LavenderSoft = Color(0xFFF5F2FF)
    val Lilac = Color(0xFFDCD4FF)
    val Blush = Color(0xFFFFF0F4)
    val Sage = Color(0xFFEAF4EF)
    val Gold = Color(0xFFC59B5F)
    val WeChat = Color(0xFF35C85A)
    val Like = Color(0xFFFF5C8A)
    val Success = Color(0xFF36C77B)
    val Warning = Color(0xFFF5A623)
    val BlackCta = Color(0xFF111217)
}

object ClozDimens {
    val ScreenPadding = 16.dp
    val CardRadius = 16.dp
    val SmallRadius = 12.dp
    val PillRadius = 24.dp
    val BottomBarHeight = 68.dp
}

val ClozPrimaryGradient = Brush.horizontalGradient(
    listOf(ClozColors.LavenderLight, ClozColors.GradientEnd),
)

val ClozSoftGradient = Brush.linearGradient(
    listOf(Color.White, ClozColors.LavenderSoft.copy(alpha = 0.62f), ClozColors.Page),
)

private val ClozTypography = Typography(
    headlineMedium = TextStyle(
        fontFamily = FontFamily.Default,
        fontWeight = FontWeight.SemiBold,
        fontSize = 28.sp,
        lineHeight = 34.sp,
    ),
    headlineSmall = TextStyle(
        fontFamily = FontFamily.Default,
        fontWeight = FontWeight.Medium,
        fontSize = 24.sp,
        lineHeight = 28.sp,
    ),
    titleLarge = TextStyle(
        fontFamily = FontFamily.Default,
        fontWeight = FontWeight.SemiBold,
        fontSize = 18.sp,
        lineHeight = 24.sp,
    ),
    titleMedium = TextStyle(
        fontFamily = FontFamily.Default,
        fontWeight = FontWeight.SemiBold,
        fontSize = 16.sp,
        lineHeight = 22.sp,
    ),
    bodyMedium = TextStyle(
        fontFamily = FontFamily.Default,
        fontWeight = FontWeight.Normal,
        fontSize = 14.sp,
        lineHeight = 20.sp,
    ),
    bodySmall = TextStyle(
        fontFamily = FontFamily.Default,
        fontWeight = FontWeight.Normal,
        fontSize = 12.sp,
        lineHeight = 18.sp,
    ),
    labelMedium = TextStyle(
        fontFamily = FontFamily.Default,
        fontWeight = FontWeight.Normal,
        fontSize = 11.sp,
        lineHeight = 16.sp,
    ),
    labelSmall = TextStyle(
        fontFamily = FontFamily.Default,
        fontWeight = FontWeight.Normal,
        fontSize = 10.sp,
        lineHeight = 14.sp,
    ),
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
        typography = ClozTypography,
        content = content,
    )
}
