package com.clothes.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.CloudOff
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.clothes.app.AppRoute
import com.clothes.app.StyleViewModel
import com.clothes.app.UiState
import com.clothes.app.ui.components.ClozCard
import com.clothes.app.ui.components.ClozPrimaryButton
import com.clothes.app.ui.components.ClozProgressBar
import com.clothes.app.ui.theme.ClozColors
import com.clothes.app.ui.theme.ClozDimens

@Composable
fun ProgressScreen(state: UiState, modifier: Modifier = Modifier) {
    val task = state.task
    val progress = (task?.progress ?: 42) / 100f
    LazyColumn(
        modifier = modifier.fillMaxSize().background(ClozColors.Page).padding(horizontal = ClozDimens.ScreenPadding),
        verticalArrangement = Arrangement.spacedBy(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        item { Spacer(Modifier.height(44.dp)) }
        item {
            Icon(Icons.Filled.AutoAwesome, null, tint = ClozColors.Lavender, modifier = Modifier.size(46.dp))
            Text("AI 正在生成穿搭", color = ClozColors.Ink, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold, textAlign = TextAlign.Center)
            Text(task?.message ?: "正在分析身型、筛选单品并生成试穿图", color = ClozColors.Muted, textAlign = TextAlign.Center)
        }
        item {
            ClozCard {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("任务进度", color = ClozColors.Ink, fontWeight = FontWeight.Bold)
                    Text("${(progress * 100).toInt()}%", color = ClozColors.Lavender, fontWeight = FontWeight.Bold)
                }
                ClozProgressBar(progress)
                StatusStep("身型分析", activeStep(task?.status, 0))
                StatusStep("商品筛选", activeStep(task?.status, 1))
                StatusStep("搭配生成", activeStep(task?.status, 2))
                StatusStep("试穿质检", activeStep(task?.status, 3))
            }
        }
    }
}

@Composable
fun FailureScreen(state: UiState, viewModel: StyleViewModel, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier.fillMaxSize().background(ClozColors.Page).padding(ClozDimens.ScreenPadding),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Icon(Icons.Filled.CloudOff, null, tint = ClozColors.Lavender, modifier = Modifier.size(48.dp))
        Text("生成失败", color = ClozColors.Ink, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold, modifier = Modifier.padding(top = 14.dp))
        Text(
            state.errorMessage ?: state.task?.error ?: "当前服务暂时不可用，请稍后再试。",
            color = ClozColors.Muted,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 8.dp, bottom = 22.dp),
        )
        ClozPrimaryButton("重新上传", onClick = viewModel::resetForNewPhoto)
        Spacer(Modifier.height(10.dp))
        ClozPrimaryButton("回到首页", dark = true, onClick = { viewModel.navigate(AppRoute.Home) })
    }
}

@Composable
private fun StatusStep(title: String, state: StepState) {
    val color = when (state) {
        StepState.Done -> Color(0xFF48A577)
        StepState.Current -> ClozColors.Lavender
        StepState.Todo -> ClozColors.Line
    }
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(9.dp)) {
        Icon(
            if (state == StepState.Done) Icons.Filled.CheckCircle else Icons.Filled.AutoAwesome,
            null,
            tint = color,
            modifier = Modifier.size(20.dp).clip(CircleShape),
        )
        Text(title, color = ClozColors.Ink, fontWeight = FontWeight.Bold)
    }
}

private enum class StepState { Done, Current, Todo }

private fun activeStep(status: String?, step: Int): StepState {
    val current = when (status) {
        "created", "profiling_photo" -> 0
        "resolving_preferences", "scouting_products", "normalizing_products" -> 1
        "composing_outfits", "reviewing_outfits" -> 2
        else -> 3
    }
    return when {
        current > step -> StepState.Done
        current == step -> StepState.Current
        else -> StepState.Todo
    }
}
