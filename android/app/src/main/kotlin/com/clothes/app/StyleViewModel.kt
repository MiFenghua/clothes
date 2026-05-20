package com.clothes.app

import android.app.Application
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

class StyleViewModel(application: Application) : AndroidViewModel(application) {
    private val authSessionStore = AuthSessionStore(application)
    private val api = StyleApi(application, application.getString(R.string.api_base_url), authSessionStore)
    private val _uiState = MutableStateFlow(UiState())
    val uiState: StateFlow<UiState> = _uiState
    private var pollingJob: Job? = null
    private var signInJob: Job? = null
    private var currentUserJob: Job? = null
    private var authGeneration = 0

    init {
        _uiState.update { it.copy(currentUser = authSessionStore.user()) }
        refreshCurrentUser()
        refreshBackendStatus()
    }

    fun startExperience() {
        _uiState.update { it.copy(route = AppRoute.Login, previousRoute = AppRoute.Splash) }
    }

    fun finishOnboarding() {
        _uiState.update { it.copy(route = AppRoute.Home, previousRoute = AppRoute.Home, notice = null) }
        refreshBackendStatus()
        loadWardrobe()
    }

    fun navigate(route: AppRoute) {
        pollingJob?.takeIf { route !in setOf(AppRoute.Progress, AppRoute.OutfitDetail, AppRoute.ShoppingList, AppRoute.TryOn) }?.cancel()
        _uiState.update {
            it.copy(
                route = route,
                previousRoute = if (route in BottomTabs.map { tab -> tab.route }) route else it.previousRoute,
                errorMessage = null,
                notice = null,
            )
        }
        if (route == AppRoute.Wardrobe) loadWardrobe()
        if (route == AppRoute.Profile || route == AppRoute.Home) refreshBackendStatus()
    }

    fun openStyleLab(item: WardrobeItem? = null) {
        _uiState.update {
            it.copy(
                route = AppRoute.UploadAnalysis,
                selectedWardrobeItem = item,
                form = it.form.copy(wardrobeItemIds = item?.itemId.orEmpty()),
                errorMessage = null,
                notice = null,
            )
        }
    }

    fun openWardrobeDetail(item: WardrobeItem) {
        _uiState.update { it.copy(route = AppRoute.WardrobeDetail, selectedWardrobeItem = item) }
    }

    fun backFromDetail() {
        _uiState.update { it.copy(route = it.previousRoute.takeIf { route -> route != AppRoute.Splash } ?: AppRoute.Home) }
    }

    fun selectPhoto(uri: Uri) {
        _uiState.update { it.copy(photoUri = uri, notice = null, errorMessage = null) }
    }

    fun selectSidePhoto(uri: Uri) {
        _uiState.update { it.copy(sidePhotoUri = uri, notice = null, errorMessage = null) }
    }

    fun updateForm(transform: (StyleForm) -> StyleForm) {
        _uiState.update { it.copy(form = transform(it.form)) }
    }

    fun toggleStyleGoal(goal: String) {
        _uiState.update { state ->
            val terms = state.form.likedStyle.split(",", "，").map { it.trim() }.filter { it.isNotBlank() }.toMutableList()
            if (terms.contains(goal)) terms.remove(goal) else terms.add(goal)
            state.copy(form = state.form.copy(likedStyle = terms.joinToString(",")))
        }
    }

    fun updateLoginPhone(value: String) {
        _uiState.update { it.copy(loginPhone = value, notice = null) }
    }

    fun updateLoginCode(value: String) {
        _uiState.update { it.copy(loginCode = value, notice = null) }
    }

    fun completeLocalLogin() {
        _uiState.update { it.copy(route = AppRoute.StyleGoal, previousRoute = AppRoute.Login, notice = null) }
    }

    fun signInWithGoogle(googleAuthClient: GoogleAuthClient) {
        signInJob?.cancel()
        authGeneration += 1
        val generationAtStart = authGeneration
        signInJob = viewModelScope.launch {
            _uiState.update { it.copy(isSigningIn = true, notice = null) }
            val googleResult = googleAuthClient.signIn()
            if (generationAtStart != authGeneration) return@launch
            when (googleResult) {
                GoogleSignInResult.Cancelled -> {
                    _uiState.update { it.copy(isSigningIn = false, notice = "已取消 Google 登录") }
                }
                is GoogleSignInResult.Failure -> {
                    _uiState.update { it.copy(isSigningIn = false, notice = googleResult.message) }
                }
                is GoogleSignInResult.Success -> {
                    try {
                        val auth = api.loginWithGoogle(googleResult.idToken)
                        if (generationAtStart != authGeneration) return@launch
                        authSessionStore.save(auth)
                        _uiState.update {
                            it.copy(
                                isSigningIn = false,
                                currentUser = auth.user,
                                route = AppRoute.StyleGoal,
                                previousRoute = AppRoute.Login,
                                notice = null,
                            )
                        }
                    } catch (error: CancellationException) {
                        throw error
                    } catch (error: Exception) {
                        _uiState.update {
                            it.copy(
                                isSigningIn = false,
                                notice = error.message ?: "Google 登录失败",
                            )
                        }
                    }
                }
            }
        }
    }

    fun logout() {
        authGeneration += 1
        pollingJob?.cancel()
        pollingJob = null
        signInJob?.cancel()
        signInJob = null
        currentUserJob?.cancel()
        currentUserJob = null
        viewModelScope.launch {
            runCatching { api.logout() }
            authSessionStore.clear()
            _uiState.update {
                UiState(route = AppRoute.Login, previousRoute = AppRoute.Splash, backendOnline = it.backendOnline)
            }
        }
    }

    fun openFeatureAnalysis() {
        _uiState.update { it.copy(route = AppRoute.FeatureAnalysis, previousRoute = AppRoute.UploadAnalysis, notice = null) }
    }

    fun openOutfitDetail() {
        _uiState.update { it.copy(route = AppRoute.OutfitDetail, resultPanel = ResultPanel.OutfitDetail, notice = null) }
    }

    fun openShoppingList() {
        _uiState.update { it.copy(route = AppRoute.ShoppingList, resultPanel = ResultPanel.ShoppingList, notice = null) }
    }

    fun openTryOn() {
        _uiState.update { it.copy(route = AppRoute.TryOn, resultPanel = ResultPanel.TryOn, notice = null) }
    }

    fun openFavorites(tab: FavoriteTab = _uiState.value.favoritesTab) {
        _uiState.update { it.copy(route = AppRoute.Favorites, favoritesTab = tab, notice = null) }
    }

    fun selectFavoritesTab(tab: FavoriteTab) {
        _uiState.update { it.copy(favoritesTab = tab, notice = null) }
    }

    fun submit() {
        val state = _uiState.value
        val photo = state.photoUri ?: run {
            _uiState.update { it.copy(notice = "请先选择一张清晰全身照") }
            return
        }
        if (state.isSubmitting) return

        viewModelScope.launch {
            _uiState.update {
                it.copy(
                    isSubmitting = true,
                    route = AppRoute.Progress,
                    errorMessage = null,
                    result = null,
                    task = null,
                    notice = null,
                )
            }
            try {
                val task = api.createTask(photo, state.form)
                _uiState.update { it.copy(task = task, isSubmitting = false) }
                startPolling(task.taskId)
            } catch (error: Exception) {
                _uiState.update {
                    it.copy(
                        route = AppRoute.Failure,
                        isSubmitting = false,
                        errorMessage = error.message ?: "任务创建失败",
                    )
                }
            }
        }
    }

    fun retryImage() {
        val taskId = _uiState.value.task?.taskId ?: _uiState.value.result?.taskId ?: return
        viewModelScope.launch {
            _uiState.update { it.copy(route = AppRoute.Progress, result = null, errorMessage = null, notice = null) }
            try {
                val task = api.retryImage(taskId)
                _uiState.update { it.copy(task = task) }
                startPolling(taskId)
            } catch (error: Exception) {
                _uiState.update {
                    it.copy(
                        route = AppRoute.Failure,
                        errorMessage = error.message ?: "试穿图重试失败",
                    )
                }
            }
        }
    }

    fun saveTryOnImage() {
        val imageUrl = _uiState.value.result?.tryOnImageUrl ?: return
        if (_uiState.value.isSavingImage) return
        viewModelScope.launch {
            _uiState.update { it.copy(isSavingImage = true, notice = null) }
            val saved = runCatching { api.saveImageToGallery(imageUrl) }.getOrDefault(false)
            _uiState.update {
                it.copy(
                    isSavingImage = false,
                    notice = if (saved) "试穿图已保存到相册" else "当前图片暂时无法保存",
                )
            }
        }
    }

    fun resetForNewPhoto() {
        pollingJob?.cancel()
        _uiState.update {
            it.copy(
                route = AppRoute.UploadAnalysis,
                photoUri = null,
                sidePhotoUri = null,
                task = null,
                result = null,
                errorMessage = null,
                isSubmitting = false,
                isSavingImage = false,
                notice = null,
            )
        }
    }

    fun selectWardrobePhoto(uri: Uri) {
        _uiState.update { it.copy(wardrobeDraft = it.wardrobeDraft.copy(photoUri = uri), notice = null) }
    }

    fun updateWardrobeDraft(transform: (WardrobeDraft) -> WardrobeDraft) {
        _uiState.update { it.copy(wardrobeDraft = transform(it.wardrobeDraft)) }
    }

    fun loadWardrobe() {
        if (_uiState.value.isLoadingWardrobe) return
        viewModelScope.launch {
            _uiState.update { it.copy(isLoadingWardrobe = true) }
            val result = runCatching { api.listWardrobeItems() }
            _uiState.update {
                it.copy(
                    isLoadingWardrobe = false,
                    wardrobeItems = result.getOrElse { _ -> it.wardrobeItems },
                    notice = result.exceptionOrNull()?.message,
                )
            }
        }
    }

    fun saveWardrobeItem() {
        val draft = _uiState.value.wardrobeDraft
        if (draft.photoUri == null) {
            _uiState.update { it.copy(notice = "请先选择衣物照片") }
            return
        }
        if (draft.title.isBlank()) {
            _uiState.update { it.copy(notice = "请填写衣物名称") }
            return
        }
        if (_uiState.value.isSavingWardrobe) return

        viewModelScope.launch {
            _uiState.update { it.copy(isSavingWardrobe = true, notice = null) }
            try {
                val saved = api.createWardrobeItem(draft)
                _uiState.update {
                    it.copy(
                        isSavingWardrobe = false,
                        wardrobeDraft = WardrobeDraft(category = draft.category),
                        wardrobeItems = listOf(saved) + it.wardrobeItems.filterNot { item -> item.itemId == saved.itemId },
                        notice = "已加入衣橱",
                    )
                }
            } catch (error: Exception) {
                _uiState.update {
                    it.copy(
                        isSavingWardrobe = false,
                        notice = error.message ?: "衣物保存失败",
                    )
                }
            }
        }
    }

    fun refreshBackendStatus() {
        viewModelScope.launch {
            val online = api.health()
            _uiState.update { it.copy(backendOnline = online) }
        }
    }

    private fun refreshCurrentUser() {
        val tokenAtStart = authSessionStore.token() ?: return
        currentUserJob?.cancel()
        currentUserJob = viewModelScope.launch {
            try {
                val user = api.currentUser()
                if (authSessionStore.token() != tokenAtStart) return@launch
                if (user == null) {
                    authSessionStore.clear()
                }
                _uiState.update { it.copy(currentUser = user) }
            } catch (error: CancellationException) {
                throw error
            } catch (_: Exception) {
                if (authSessionStore.token() != tokenAtStart) return@launch
                _uiState.update { state ->
                    state.copy(currentUser = authSessionStore.user() ?: state.currentUser)
                }
            }
        }
    }

    fun dismissNotice() {
        _uiState.update { it.copy(notice = null) }
    }

    private fun startPolling(taskId: String) {
        pollingJob?.cancel()
        pollingJob = viewModelScope.launch {
            while (true) {
                try {
                    val task = api.getTask(taskId)
                    _uiState.update { it.copy(task = task, route = AppRoute.Progress) }
                    if (task.isTerminal) {
                        finishTask(task)
                        return@launch
                    }
                    delay(1200)
                } catch (error: CancellationException) {
                    throw error
                } catch (error: Exception) {
                    _uiState.update {
                        it.copy(
                            route = AppRoute.Failure,
                            errorMessage = error.message ?: "查询任务失败",
                        )
                    }
                    return@launch
                }
            }
        }
    }

    private suspend fun finishTask(task: StyleTaskView) {
        if (task.status == "failed") {
            _uiState.update {
                it.copy(
                    route = AppRoute.Failure,
                    task = task,
                    errorMessage = task.error ?: task.message.ifBlank { "任务失败" },
                )
            }
            return
        }

        val result = task.result ?: api.getResult(task.taskId)
        _uiState.update {
            it.copy(
                route = AppRoute.OutfitDetail,
                resultPanel = ResultPanel.OutfitDetail,
                task = task,
                result = result,
                errorMessage = null,
            )
        }
    }

    override fun onCleared() {
        pollingJob?.cancel()
        signInJob?.cancel()
        currentUserJob?.cancel()
        super.onCleared()
    }
}
