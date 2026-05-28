package com.clothes.app

import android.content.Context
import androidx.credentials.CredentialManager
import androidx.credentials.GetCredentialRequest
import androidx.credentials.exceptions.GetCredentialCancellationException
import androidx.credentials.exceptions.GetCredentialException
import androidx.credentials.exceptions.NoCredentialException
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import kotlinx.coroutines.CancellationException

class GoogleAuthClient(private val context: Context) {
    private val credentialManager = CredentialManager.create(context)

    suspend fun signIn(): GoogleSignInResult {
        val clientId = context.getString(R.string.google_web_client_id)
        if (clientId.startsWith("replace-with-")) {
            return GoogleSignInResult.Failure("请先配置 Google Web Client ID")
        }
        val googleIdOption = GetGoogleIdOption.Builder()
            .setFilterByAuthorizedAccounts(false)
            .setServerClientId(clientId)
            .setAutoSelectEnabled(false)
            .build()
        val request = GetCredentialRequest.Builder()
            .addCredentialOption(googleIdOption)
            .build()
        return try {
            val result = credentialManager.getCredential(context, request)
            val credential = GoogleIdTokenCredential.createFrom(result.credential.data)
            GoogleSignInResult.Success(credential.idToken)
        } catch (_: GetCredentialCancellationException) {
            GoogleSignInResult.Cancelled
        } catch (error: CancellationException) {
            throw error
        } catch (error: GetCredentialException) {
            GoogleSignInResult.Failure(googleSignInFailureMessage(error))
        } catch (error: Exception) {
            GoogleSignInResult.Failure(googleSignInFailureMessage(error))
        }
    }
}

internal fun googleSignInFailureMessage(error: Throwable): String {
    val message = error.message.orEmpty()
    return if (
        error is NoCredentialException ||
        message.contains("No matching credentials", ignoreCase = true) ||
        message.contains("no credentials", ignoreCase = true)
    ) {
        "未能获取 Google 登录凭据。请确认当前手机资料已添加 Google 账号，并检查 Google Play 服务网络/VPN 是否可访问 Google。"
    } else {
        message.ifBlank { "Google 登录失败" }
    }
}
