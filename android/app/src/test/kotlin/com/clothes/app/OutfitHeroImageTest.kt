package com.clothes.app

import com.clothes.app.ui.screens.outfitDetailHeroImage
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class OutfitHeroImageTest {
    @Test
    fun outfitDetailHeroUsesGeneratedTryOnImageWhenPresent() {
        val imageUrl = "data:image/png;base64,iVBORw0KGgo="
        val state = UiState(result = resultWithTryOnImage(imageUrl))

        assertEquals(imageUrl, outfitDetailHeroImage(state))
    }

    @Test
    fun outfitDetailHeroFallsBackWhenGeneratedImageIsMissing() {
        assertNull(outfitDetailHeroImage(UiState(result = resultWithTryOnImage(null))))
        assertNull(outfitDetailHeroImage(UiState()))
    }

    private fun resultWithTryOnImage(imageUrl: String?): StyleTaskResult {
        return StyleTaskResult(
            taskId = "task-1",
            status = "succeeded",
            outfit = null,
            tryOnImageUrl = imageUrl,
            recommendationReport = null,
            imageQualityReport = null,
            alternativesRejected = emptyList(),
            userMessage = null,
        )
    }
}
