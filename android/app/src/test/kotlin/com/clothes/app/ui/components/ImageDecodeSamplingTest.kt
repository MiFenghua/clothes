package com.clothes.app.ui.components

import org.junit.Assert.assertEquals
import org.junit.Test

class ImageDecodeSamplingTest {
    @Test
    fun largePhotoPreviewUsesDownsampling() {
        assertEquals(6, calculateBitmapSampleSize(width = 12_240, height = 12_240, maxDimension = 2_048))
    }

    @Test
    fun smallPhotoPreviewKeepsOriginalSize() {
        assertEquals(1, calculateBitmapSampleSize(width = 1_280, height = 960, maxDimension = 2_048))
    }
}
