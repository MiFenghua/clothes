package com.clothes.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.clothes.app.ui.components.ClozBottomBar
import com.clothes.app.ui.screens.FailureScreen
import com.clothes.app.ui.screens.FavoritesScreen
import com.clothes.app.ui.screens.FeatureAnalysisScreen
import com.clothes.app.ui.screens.HomeScreen
import com.clothes.app.ui.screens.InspirationScreen
import com.clothes.app.ui.screens.LoginScreen
import com.clothes.app.ui.screens.OutfitDetailScreen
import com.clothes.app.ui.screens.ProgressScreen
import com.clothes.app.ui.screens.ProfileScreen
import com.clothes.app.ui.screens.ShoppingListScreen
import com.clothes.app.ui.screens.SplashScreen
import com.clothes.app.ui.screens.StyleGoalScreen
import com.clothes.app.ui.screens.TryOnScreen
import com.clothes.app.ui.screens.UploadAnalysisScreen
import com.clothes.app.ui.screens.WardrobeItemDetailScreen
import com.clothes.app.ui.screens.WardrobeScreen
import com.clothes.app.ui.theme.ClozAiTheme
import com.clothes.app.ui.theme.ClozColors

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            ClozAiTheme {
                val viewModel: StyleViewModel = viewModel()
                val googleAuthClient = remember { GoogleAuthClient(this@MainActivity) }
                ClozAiApp(viewModel, googleAuthClient)
            }
        }
    }
}

@Composable
fun ClozAiApp(viewModel: StyleViewModel, googleAuthClient: GoogleAuthClient) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    LaunchedEffect(state.notice) {
        val message = state.notice ?: return@LaunchedEffect
        snackbar.showSnackbar(message)
        viewModel.dismissNotice()
    }

    val bottomRoutes = BottomTabs.map { it.route }.toSet() + AppRoute.Favorites
    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        containerColor = ClozColors.Page,
        bottomBar = {
            if (state.route in bottomRoutes) {
                ClozBottomBar(current = state.route, onSelected = viewModel::navigate)
            }
        },
    ) { padding ->
        val modifier = Modifier.padding(padding)
        when (state.route) {
            AppRoute.Splash -> SplashScreen(state, viewModel, modifier)
            AppRoute.Login -> LoginScreen(state, viewModel, modifier)
            AppRoute.StyleGoal -> StyleGoalScreen(state, viewModel, modifier)
            AppRoute.UploadAnalysis -> UploadAnalysisScreen(state, viewModel, modifier)
            AppRoute.FeatureAnalysis -> FeatureAnalysisScreen(state, viewModel, modifier)
            AppRoute.Home -> HomeScreen(state, viewModel, modifier)
            AppRoute.Inspiration -> InspirationScreen(state, viewModel, modifier)
            AppRoute.Wardrobe -> WardrobeScreen(state, viewModel, modifier)
            AppRoute.WardrobeDetail -> WardrobeItemDetailScreen(state, viewModel, modifier)
            AppRoute.OutfitDetail -> OutfitDetailScreen(state, viewModel, modifier)
            AppRoute.ShoppingList -> ShoppingListScreen(state, viewModel, modifier)
            AppRoute.TryOn -> TryOnScreen(state, viewModel, modifier)
            AppRoute.Favorites -> FavoritesScreen(state, viewModel, modifier)
            AppRoute.Progress -> ProgressScreen(state, modifier)
            AppRoute.Profile -> ProfileScreen(state, viewModel, modifier)
            AppRoute.Failure -> FailureScreen(state, viewModel, modifier)
        }
    }
}
