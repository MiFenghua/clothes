package com.clothes.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class GoogleAuthClientTest {
    @Test
    fun noCredentialErrorsExplainCurrentAndroidProfile() {
        val message = googleSignInFailureMessage(RuntimeException("No matching credentials."))

        assertTrue(message.contains("当前手机资料"))
        assertTrue(message.contains("Google 账号"))
    }

    @Test
    fun unknownCredentialErrorsKeepProviderMessage() {
        assertEquals(
            "Provider unavailable",
            googleSignInFailureMessage(RuntimeException("Provider unavailable")),
        )
    }
}
