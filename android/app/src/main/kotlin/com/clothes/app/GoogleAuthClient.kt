package com.clothes.app

import android.content.Context
import androidx.credentials.CredentialManager
import androidx.credentials.GetCredentialRequest
import androidx.credentials.exceptions.GetCredentialCancellationException
import androidx.credentials.exceptions.GetCredentialException
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential

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
        } catch (error: GetCredentialException) {
            GoogleSignInResult.Failure(error.message ?: "Google 登录失败")
        } catch (error: Exception) {
            GoogleSignInResult.Failure(error.message ?: "Google 登录失败")
        }
    }
}
