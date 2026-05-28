package com.clothes.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class GoogleAuthClientTest {
    @Test
    fun noCredentialErrorsExplainProfileOrGoogleServiceNetwork() {
        val message = googleSignInFailureMessage(RuntimeException("No matching credentials."))

        assertTrue(message.contains("Google 登录凭据"))
        assertTrue(message.contains("当前手机资料"))
        assertTrue(message.contains("Google Play 服务网络"))
    }

    @Test
    fun unknownCredentialErrorsKeepProviderMessage() {
        assertEquals(
            "Provider unavailable",
            googleSignInFailureMessage(RuntimeException("Provider unavailable")),
        )
    }
}
