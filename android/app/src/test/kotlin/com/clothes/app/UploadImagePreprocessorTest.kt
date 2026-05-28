package com.clothes.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class UploadImagePreprocessorTest {
    @Test
    fun oversizedUploadUsesCeilSampling() {
        assertEquals(6, calculateUploadImageSampleSize(width = 12_240, height = 12_240, maxDimension = 2_048))
    }

    @Test
    fun smallJpegCanStreamOriginalBytes() {
        assertFalse(shouldReencodeUploadImage(width = 1_280, height = 960, mime = "image/jpeg"))
    }

    @Test
    fun oversizedJpegIsReencoded() {
        assertTrue(shouldReencodeUploadImage(width = 4_096, height = 1_024, mime = "image/jpeg"))
    }

    @Test
    fun nonJpegImagesAreReencodedForUpload() {
        assertTrue(shouldReencodeUploadImage(width = 1_280, height = 960, mime = "image/png"))
    }

    @Test
    fun compressedUploadNameUsesJpegExtension() {
        assertEquals("portrait.jpg", compressedUploadFileName("portrait.png"))
        assertEquals("photo.jpg", compressedUploadFileName(""))
    }
}
