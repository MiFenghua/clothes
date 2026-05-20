package com.clothes.app

import android.content.Context
import org.json.JSONObject

class AuthSessionStore(context: Context) {
    private val preferences = context.getSharedPreferences("cloz_auth", Context.MODE_PRIVATE)

    fun save(auth: AuthResponse) {
        preferences.edit()
            .putString(KEY_TOKEN, auth.session.token)
            .putString(KEY_EXPIRES_AT, auth.session.expiresAt)
            .putString(KEY_USER, JSONObject().apply {
                put("user_id", auth.user.userId)
                put("email", auth.user.email)
                put("name", auth.user.name)
                put("avatar_url", auth.user.avatarUrl)
                put("provider", auth.user.provider)
            }.toString())
            .apply()
    }

    fun token(): String? = preferences.getString(KEY_TOKEN, null)?.takeIf { it.isNotBlank() }

    fun user(): PublicUser? {
        val raw = preferences.getString(KEY_USER, null) ?: return null
        return runCatching { parsePublicUser(JSONObject(raw)) }.getOrNull()
    }

    fun clear() {
        preferences.edit().clear().apply()
    }

    private companion object {
        const val KEY_TOKEN = "token"
        const val KEY_EXPIRES_AT = "expires_at"
        const val KEY_USER = "user"
    }
}
