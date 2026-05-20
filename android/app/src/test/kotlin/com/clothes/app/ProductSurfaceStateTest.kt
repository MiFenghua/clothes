package com.clothes.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.assertNull
import org.junit.Test

class ProductSurfaceStateTest {
    @Test
    fun favoriteTabApiTypeMapsBackendTypes() {
        assertEquals("outfit", FavoriteTab.Outfits.apiType)
        assertEquals("item", FavoriteTab.Items.apiType)
        assertEquals("inspiration", FavoriteTab.Inspiration.apiType)
    }

    @Test
    fun styleFormToStyleProfileParsesNullableMeasurementsAndKeywords() {
        val current = StyleProfile(
            displayName = "Current",
            heightCm = 160,
            weightKg = 48,
            bodyShape = "old",
            skinTone = "old",
            hairTone = "old",
            styleKeywords = listOf("old"),
            featureMetrics = listOf(FeatureMetric("shoulder", "balanced")),
        )
        val form = StyleForm(
            heightCm = "168",
            weightKg = "52",
            likedStyle = "minimal, commute, ,soft",
            bodyShape = " pear ",
            skinTone = "",
            hairTone = " brown ",
        )

        val profile = form.toStyleProfile(displayName = "Ada", current = current)

        assertEquals("Ada", profile.displayName)
        assertEquals(168, profile.heightCm)
        assertEquals(52, profile.weightKg)
        assertEquals("pear", profile.bodyShape)
        assertNull(profile.skinTone)
        assertEquals("brown", profile.hairTone)
        assertEquals(listOf("minimal", "commute", "soft"), profile.styleKeywords)
        assertEquals(current.featureMetrics, profile.featureMetrics)
    }

    @Test
    fun styleFormToStyleProfileUsesUiDefaultsForBlankMeasurements() {
        val profile = StyleForm(heightCm = " ", weightKg = "").toStyleProfile(displayName = "Ada")

        assertEquals(168, profile.heightCm)
        assertEquals(50, profile.weightKg)
    }

    @Test
    fun styleFormToStyleProfileUsesUiDefaultsForBlankMeasurementsEvenWithCurrentProfile() {
        val current = StyleProfile(
            displayName = "Current",
            heightCm = 170,
            weightKg = 60,
            bodyShape = null,
            skinTone = null,
            hairTone = null,
            styleKeywords = emptyList(),
            featureMetrics = emptyList(),
        )

        val profile = StyleForm(heightCm = "", weightKg = "").toStyleProfile(displayName = "Ada", current = current)

        assertEquals(168, profile.heightCm)
        assertEquals(50, profile.weightKg)
    }

    @Test
    fun visibleBackendFavoritesOnlyReturnsItemsForSelectedTabType() {
        val favorite = favoriteView(type = "outfit")
        val state = UiState(
            favoritesTab = FavoriteTab.Inspiration,
            favoriteItemsType = "outfit",
            favoriteItems = listOf(favorite),
        )

        assertTrue(state.visibleBackendFavorites.isEmpty())
        assertEquals(
            listOf(favorite),
            state.copy(favoritesTab = FavoriteTab.Outfits).visibleBackendFavorites,
        )
    }

    @Test
    fun favoritesSurfaceResolvedTracksCurrentTabEvenWhenEmpty() {
        assertTrue(
            UiState(
                favoritesTab = FavoriteTab.Inspiration,
                favoriteItemsType = "inspiration",
                favoriteItems = emptyList(),
            ).hasResolvedFavoritesForCurrentTab,
        )
        assertTrue(
            !UiState(
                favoritesTab = FavoriteTab.Inspiration,
                favoriteItemsType = "outfit",
                favoriteItems = listOf(favoriteView(type = "outfit")),
            ).hasResolvedFavoritesForCurrentTab,
        )
    }

    @Test
    fun unauthorizedApiErrorsAreDetectedFromStatusCode() {
        assertTrue(StyleApiException(401, "Authentication is required").isUnauthorizedApiError())
        assertTrue(!StyleApiException(500, "Server error").isUnauthorizedApiError())
    }

    @Test
    fun localProfilePreviewSkipsAnonymousProfileRefresh() {
        assertTrue(UiState().shouldRefreshProfileFromBackend(hasAuthToken = false))
        assertTrue(UiState(hasLocalStyleProfilePreview = true).shouldRefreshProfileFromBackend(hasAuthToken = true))
        assertTrue(!UiState(hasLocalStyleProfilePreview = true).shouldRefreshProfileFromBackend(hasAuthToken = false))
    }

    @Test
    fun homeRecommendationToInspirationLookPreservesCardFields() {
        val recommendation = HomeRecommendation(
            recommendationId = "rec-1",
            title = "Blue blazer",
            scene = "commute",
            score = 0.93,
            imageUrl = "https://example.com/rec.png",
            sourceTaskId = "task-1",
        )

        val look = recommendation.toInspirationLook()

        assertEquals("rec-1", look.inspirationId)
        assertEquals("Blue blazer", look.title)
        assertEquals("commute", look.scene)
        assertEquals(0.93, look.score, 0.0001)
        assertEquals("https://example.com/rec.png", look.imageUrl)
    }

    private fun favoriteView(type: String): FavoriteView {
        return FavoriteView(
            favoriteId = "fav-1",
            ownerId = "user-1",
            favoriteType = type,
            targetId = "target-1",
            snapshotTitle = "Saved",
        )
    }
}
