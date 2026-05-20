package com.clothes.app

import org.junit.Assert.assertEquals
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
            weightKg = " ",
            likedStyle = "minimal, commute, ,soft",
            bodyShape = " pear ",
            skinTone = "",
            hairTone = " brown ",
        )

        val profile = form.toStyleProfile(displayName = "Ada", current = current)

        assertEquals("Ada", profile.displayName)
        assertEquals(168, profile.heightCm)
        assertNull(profile.weightKg)
        assertEquals("pear", profile.bodyShape)
        assertNull(profile.skinTone)
        assertEquals("brown", profile.hairTone)
        assertEquals(listOf("minimal", "commute", "soft"), profile.styleKeywords)
        assertEquals(current.featureMetrics, profile.featureMetrics)
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
}
