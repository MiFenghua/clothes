package com.clothes.app.ui.screens

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.clothes.app.BodyShapeOptions
import com.clothes.app.GoogleAuthClient
import com.clothes.app.SceneOptions
import com.clothes.app.SkinToneOptions
import com.clothes.app.StyleGoalOptions
import com.clothes.app.StyleViewModel
import com.clothes.app.UiState
import com.clothes.app.ui.components.BodyOutlinePlaceholder
import com.clothes.app.ui.components.ClozCard
import com.clothes.app.ui.components.ClozChip
import com.clothes.app.ui.components.ClozLogo
import com.clothes.app.ui.components.ClozPrimaryButton
import com.clothes.app.ui.components.ClozProgressBar
import com.clothes.app.ui.components.ClozRemoteImage
import com.clothes.app.ui.components.ClozTopBar
import com.clothes.app.ui.components.ModelFigurePlaceholder
import com.clothes.app.ui.components.SideFigurePlaceholder
import com.clothes.app.ui.components.SparkleBackdrop
import com.clothes.app.ui.mock.DemoFeatureMetrics
import com.clothes.app.ui.mock.DemoStyleKeywords
import com.clothes.app.ui.theme.ClozColors
import com.clothes.app.ui.theme.ClozDimens
import com.clothes.app.ui.theme.ClozSoftGradient

@Composable
fun SplashScreen(state: UiState, viewModel: StyleViewModel, modifier: Modifier = Modifier) {
    Box(
        modifier
            .fillMaxSize()
            .background(ClozSoftGradient)
            .padding(horizontal = 28.dp, vertical = 22.dp),
    ) {
        SparkleBackdrop(Modifier.matchParentSize())
        Column(
            modifier = Modifier.align(Alignment.Center).fillMaxWidth(),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            ClozLogo()
            Text("AI 洞察你的独特特征\n生成最适合你的流行穿搭", color = ClozColors.Ink, textAlign = TextAlign.Center, style = MaterialTheme.typography.titleSmall)
        }
        Column(
            modifier = Modifier.align(Alignment.BottomCenter).fillMaxWidth(),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(11.dp),
        ) {
            ClozPrimaryButton("开始体验", dark = true, onClick = viewModel::startExperience)
            Text("我已阅读并同意《用户协议》与《隐私政策》", color = ClozColors.Muted, style = MaterialTheme.typography.labelSmall)
        }
    }
}

@Composable
fun LoginScreen(
    state: UiState,
    viewModel: StyleViewModel,
    googleAuthClient: GoogleAuthClient,
    modifier: Modifier = Modifier,
) {
    LazyColumn(
        modifier = modifier.fillMaxSize().background(ClozColors.Page).padding(horizontal = ClozDimens.ScreenPadding),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        item { Spacer(Modifier.height(12.dp)) }
        item {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.Top) {
                Column(Modifier.weight(1f).padding(top = 10.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    ClozLogo()
                    Text("你好，欢迎使用\nclozAi", color = ClozColors.Ink, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
                    Text("AI 为你打造专属穿搭", color = ClozColors.Muted, style = MaterialTheme.typography.bodySmall)
                }
                ModelFigurePlaceholder(Modifier.width(142.dp).height(206.dp))
            }
        }
        item {
            ClozCard {
                Text("登录后保存你的身型档案、衣橱和推荐记录", color = ClozColors.Ink, fontWeight = FontWeight.SemiBold)
                ClozPrimaryButton(
                    text = if (state.isSigningIn) "正在连接 Google..." else "使用 Google 登录",
                    enabled = !state.isSigningIn,
                    onClick = { viewModel.signInWithGoogle(googleAuthClient) },
                )
                Text(
                    "继续即表示你同意《用户协议》与《隐私政策》",
                    modifier = Modifier.fillMaxWidth(),
                    color = ClozColors.Muted,
                    textAlign = TextAlign.Center,
                    style = MaterialTheme.typography.labelSmall,
                )
            }
        }
    }
}

@Composable
fun StyleGoalScreen(state: UiState, viewModel: StyleViewModel, modifier: Modifier = Modifier) {
    val selectedGoals = state.form.likedStyle.split(",", "，").map { it.trim() }.filter { it.isNotBlank() }
    LazyColumn(
        modifier = modifier.fillMaxSize().background(ClozColors.Page).padding(horizontal = ClozDimens.ScreenPadding),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        item { ClozTopBar("风格目标设置", onBack = { viewModel.navigate(com.clothes.app.AppRoute.Login) }) }
        item {
            Text("你的风格目标是？", color = ClozColors.Ink, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
            Text("选择想要的方向优化推荐", color = ClozColors.Muted, style = MaterialTheme.typography.bodySmall)
        }
        item {
            ChipScroller(StyleGoalOptions, selectedGoals, viewModel::toggleStyleGoal)
        }
        item {
            ClozCard {
                Text("你的基本信息", color = ClozColors.Ink, fontWeight = FontWeight.Bold)
                StepperRow("身高", state.form.heightCm.ifBlank { "168" }, "cm") { value -> viewModel.updateForm { it.copy(heightCm = value) } }
                StepperRow("体重（选填）", state.form.weightKg.ifBlank { "50" }, "kg") { value -> viewModel.updateForm { it.copy(weightKg = value) } }
                Text("体型", color = ClozColors.Ink, fontWeight = FontWeight.Bold)
                ChipScroller(BodyShapeOptions, listOf(state.form.bodyShape)) { value -> viewModel.updateForm { it.copy(bodyShape = value) } }
                Text("肤色", color = ClozColors.Ink, fontWeight = FontWeight.Bold)
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    listOf(Color(0xFFE7C7A8), Color(0xFFD7B08C), Color(0xFFC58B62), Color(0xFF9B6B4A), Color(0xFFF0D7BA), Color(0xFFB58B64)).forEachIndexed { index, color ->
                        Box(
                            Modifier
                                .size(26.dp)
                                .clip(CircleShape)
                                .background(color)
                                .border(2.dp, if (index == 0) ClozColors.Lavender else Color.White, CircleShape),
                        )
                    }
                }
                Text("发色", color = ClozColors.Ink, fontWeight = FontWeight.Bold)
                ChipScroller(SkinToneOptions, listOf(state.form.skinTone)) { value -> viewModel.updateForm { it.copy(skinTone = value) } }
            }
        }
        item { ClozPrimaryButton("下一步", onClick = viewModel::finishOnboarding) }
        item { Spacer(Modifier.height(24.dp)) }
    }
}

@Composable
fun UploadAnalysisScreen(state: UiState, viewModel: StyleViewModel, modifier: Modifier = Modifier) {
    val frontLauncher = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri -> if (uri != null) viewModel.selectPhoto(uri) }
    val sideLauncher = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri -> if (uri != null) viewModel.selectSidePhoto(uri) }
    LazyColumn(
        modifier = modifier.fillMaxSize().background(ClozColors.Page).padding(horizontal = ClozDimens.ScreenPadding),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item { ClozTopBar("上传照片与分析", onBack = { viewModel.navigate(com.clothes.app.AppRoute.Home) }) }
        item {
            Text("上传照片，AI 分析你的身型", color = ClozColors.Ink, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text("请尽量服装贴身，光线明亮", color = ClozColors.Muted, style = MaterialTheme.typography.bodySmall)
        }
        item {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                PhotoCard("正面照", state.photoUri?.toString(), Modifier.weight(1f), onClick = { frontLauncher.launch("image/*") })
                PhotoCard("侧面照", state.sidePhotoUri?.toString(), Modifier.weight(1f), onClick = { sideLauncher.launch("image/*") })
            }
        }
        item {
            ClozCard {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                    Text(if (state.photoUri == null) "AI 分析准备" else "AI 分析中...", color = ClozColors.Ink, fontWeight = FontWeight.SemiBold)
                    Text(if (state.photoUri == null) "待上传" else "65%", color = ClozColors.Lavender, fontWeight = FontWeight.SemiBold)
                }
                listOf("身型检测", "比例分析", "特征提取").forEach {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Icon(Icons.Filled.Check, null, tint = ClozColors.Lavender, modifier = Modifier.size(16.dp))
                        Text(it, color = ClozColors.Muted, style = MaterialTheme.typography.bodySmall)
                    }
                }
                ClozProgressBar(if (state.photoUri == null) 0.18f else 0.65f)
            }
        }
        item {
            Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                SceneOptions.forEach { scene ->
                    ClozChip(scene.label, selected = scene.value == state.form.scene) { viewModel.updateForm { it.copy(scene = scene.value) } }
                }
            }
        }
        item {
            ClozPrimaryButton(
                text = if (state.photoUri == null) "查看特征分析" else "生成今日搭配",
                enabled = !state.isSubmitting,
                onClick = { if (state.photoUri == null) viewModel.openFeatureAnalysis() else viewModel.submit() },
            )
        }
    }
}

@Composable
fun FeatureAnalysisScreen(state: UiState, viewModel: StyleViewModel, modifier: Modifier = Modifier) {
    LazyColumn(
        modifier = modifier.fillMaxSize().background(ClozColors.Page).padding(horizontal = ClozDimens.ScreenPadding),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item { ClozTopBar("我的特征分析", onBack = { viewModel.navigate(com.clothes.app.AppRoute.UploadAnalysis) }) }
        item {
            ClozCard {
                Row(horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = Alignment.CenterVertically) {
                    BodyOutlinePlaceholder(Modifier.weight(1f).height(260.dp))
                    Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(13.dp)) {
                        DemoFeatureMetrics.forEach { metric ->
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                Box(Modifier.size(26.dp).clip(CircleShape).background(ClozColors.LavenderSoft), contentAlignment = Alignment.Center) {
                                    Text(metric.label.take(1), color = ClozColors.Lavender, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
                                }
                                Column {
                                    Text(metric.label, color = ClozColors.Muted, style = MaterialTheme.typography.labelSmall)
                                    Text(metric.value, color = ClozColors.Ink, fontWeight = FontWeight.Bold)
                                }
                            }
                        }
                    }
                }
            }
        }
        item {
            ClozCard {
                Text("风格关键词", color = ClozColors.Ink, fontWeight = FontWeight.Bold)
                ChipScroller(DemoStyleKeywords, DemoStyleKeywords.take(2)) {}
            }
        }
        item { ClozPrimaryButton("查看推荐穿搭", onClick = { viewModel.navigate(com.clothes.app.AppRoute.Home) }) }
        item {
            Text("保存报告 〉", modifier = Modifier.fillMaxWidth(), color = ClozColors.Lavender, textAlign = TextAlign.Center, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun ChipScroller(options: List<String>, selected: List<String>, onSelected: (String) -> Unit) {
    Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        options.forEach { option ->
            ClozChip(option, selected = selected.contains(option), onClick = { onSelected(option) })
        }
    }
}

@Composable
private fun StepperRow(label: String, value: String, unit: String, onChange: (String) -> Unit) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text(label, color = ClozColors.Muted, modifier = Modifier.weight(1f))
        Text("-", modifier = Modifier.clip(CircleShape).background(ClozColors.Faint).clickable { onChange((value.toIntOrNull()?.minus(1) ?: 0).toString()) }.padding(horizontal = 10.dp, vertical = 4.dp), color = ClozColors.Ink)
        Text("$value $unit", modifier = Modifier.width(82.dp), textAlign = TextAlign.Center, color = ClozColors.Ink, fontWeight = FontWeight.Bold)
        Text("+", modifier = Modifier.clip(CircleShape).background(ClozColors.Faint).clickable { onChange((value.toIntOrNull()?.plus(1) ?: 0).toString()) }.padding(horizontal = 10.dp, vertical = 4.dp), color = ClozColors.Ink)
    }
}

@Composable
private fun PhotoCard(title: String, source: String?, modifier: Modifier = Modifier, onClick: () -> Unit) {
    Column(
        modifier
            .clip(RoundedCornerShape(18.dp))
            .background(Color.White)
            .border(1.dp, ClozColors.Line, RoundedCornerShape(18.dp))
            .clickable(onClick = onClick)
            .padding(10.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Box(Modifier.fillMaxWidth().aspectRatio(0.72f).clip(RoundedCornerShape(14.dp)).background(ClozColors.Faint), contentAlignment = Alignment.Center) {
            if (source != null) {
                ClozRemoteImage(source, Modifier.fillMaxSize(), ContentScale.Crop)
            } else {
                if (title.contains("侧")) SideFigurePlaceholder(Modifier.fillMaxSize()) else ModelFigurePlaceholder(Modifier.fillMaxSize())
                Icon(Icons.Filled.CameraAlt, null, tint = ClozColors.Lavender, modifier = Modifier.align(Alignment.BottomEnd).padding(8.dp).size(24.dp))
            }
        }
        Text(title, color = ClozColors.Ink, fontWeight = FontWeight.Bold, textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth())
    }
}
