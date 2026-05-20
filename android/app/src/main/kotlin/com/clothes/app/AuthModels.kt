package com.clothes.app

data class PublicUser(
    val userId: String,
    val email: String,
    val name: String,
    val avatarUrl: String?,
    val provider: String,
)

data class AuthSession(
    val token: String,
    val expiresAt: String,
)

data class AuthResponse(
    val user: PublicUser,
    val session: AuthSession,
)

sealed interface GoogleSignInResult {
    data class Success(val idToken: String) : GoogleSignInResult
    data object Cancelled : GoogleSignInResult
    data class Failure(val message: String) : GoogleSignInResult
}
