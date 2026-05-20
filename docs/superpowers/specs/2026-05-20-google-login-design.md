# Google Login Design Spec

Date: 2026-05-20

## Scope

Add real Google third-party login to the Android app and Python backend path. The Android app should replace the current local-only phone and WeChat login behavior with Google sign-in. The Python backend should verify Google ID tokens, create or update local users, issue app sessions, and expose the current authenticated user.

The target client is `android/`. The target backend is `backend/`, because the Android app currently defaults to `http://10.0.2.2:8000` and uses the Python FastAPI backend for the main product flow. The existing Node.js demo OAuth implementation is not part of the Android login path.

## Confirmed Approach

Use Android Credential Manager with Sign in with Google. Android obtains a Google ID token, sends it to the Python backend, and stores the backend-issued app session token for subsequent API calls.

The backend validates the ID token server-side before trusting the identity. Validation must check at least:

- Google token issuer.
- Token expiration.
- Audience equals the configured Google web client id.
- Subject is present.
- Email is present and verified.

This follows Google's recommended native-app pattern: the device obtains an ID token and the application backend verifies it before creating its own session.

References:

- https://developer.android.com/identity/sign-in/credential-manager-siwg-implementation
- https://developers.google.com/identity/sign-in/android/backend-auth

## Android UX

`LoginScreen` should become a real Google login screen. Keep the existing clozAi visual direction, welcome copy, logo, and model placeholder, but remove the phone-code and WeChat mock controls from the active login screen.

The primary action is "Use Google to continue". Tapping it launches Credential Manager. While login is in progress, disable the action and show a concise loading state. On success, navigate to `StyleGoal` for first-time profile setup or to `Home` if the backend later reports the user has already completed onboarding. In this pass, successful login should continue to `StyleGoal` to match the current app flow.

On failure, remain on `LoginScreen` and show a snackbar or local notice. User-cancelled sign-in should use a calm message such as "Google sign-in was cancelled" and should not be treated as a crash.

## Android Architecture

Add a small auth layer instead of mixing Google and backend logic directly into the Compose screen:

- `GoogleAuthClient`: wraps Credential Manager and returns a Google ID token or a typed cancellation/error.
- `AuthSessionStore`: persists the backend session token and public user profile in `SharedPreferences`.
- `StyleApi`: adds auth endpoints and attaches `Authorization: Bearer <session_token>` to backend requests when a session exists.
- `StyleViewModel`: owns login state, calls `GoogleAuthClient`, exchanges the ID token through `StyleApi`, stores the returned session, and updates navigation.

The existing `UiState` should gain focused fields such as `currentUser`, `isSigningIn`, and `authError` instead of overloading `notice` for all auth state.

## Backend API

Add these FastAPI endpoints under `/api/v1/auth`:

- `POST /api/v1/auth/google`
  - Request: `{ "id_token": string }`
  - Response: `{ "user": PublicUser, "session": { "token": string, "expires_at": string } }`
- `GET /api/v1/auth/me`
  - Uses `Authorization: Bearer <token>`.
  - Response: `{ "user": PublicUser | null }`
- `POST /api/v1/auth/logout`
  - Uses `Authorization: Bearer <token>`.
  - Destroys the current session if present.
  - Response: `{ "ok": true }`

`PublicUser` should include:

- `user_id`
- `email`
- `name`
- `avatar_url`
- `provider`

The backend should upsert users by Google subject first, then by normalized email. If a user exists by email, link the Google subject to that user. If not, create a new Google user.

## Backend Storage

Use a lightweight JSON auth store for this pass, consistent with the current local-demo backend shape. The file should live under backend storage and be excluded from git.

The store needs:

- Users with Google subject, email, display name, avatar URL, provider, created timestamp, and updated timestamp.
- Sessions with session id, user id, hashed token, created timestamp, and expiration timestamp.

Raw session tokens must not be stored. Store a SHA-256 hash of the token and return the raw token only once to the Android client.

## Backend Identity Flow

1. Android launches Google sign-in through Credential Manager.
2. Google returns an ID token to Android.
3. Android posts the ID token to `POST /api/v1/auth/google`.
4. Backend verifies the token against the configured Google client id.
5. Backend creates or updates the local user.
6. Backend creates a local app session and returns the session token plus public user.
7. Android persists the session token and user.
8. Future Android API calls include `Authorization: Bearer <session_token>`.
9. Backend dependencies can resolve the current user from the session token.

## Configuration

Add backend configuration:

- `STYLE_BACKEND_GOOGLE_CLIENT_ID`: Google OAuth web client id used to verify token audience.
- `STYLE_BACKEND_AUTH_STORE_PATH`: local user/session store path.
- `STYLE_BACKEND_AUTH_SESSION_MAX_AGE_DAYS`: default 30.

Add Android configuration:

- `google_web_client_id` string resource for the same web client id used by the backend.

The Android OAuth client and SHA fingerprints still need to be configured in Google Cloud Console for real devices or emulator builds. The backend audience check should use the web client id requested by Credential Manager.

## Error Handling

Backend errors should use stable codes and clear messages:

- Missing or malformed ID token: 400.
- Invalid Google token: 401.
- Unverified Google email: 401.
- Google verification service unavailable: 502.
- Missing backend Google client id: 503.

Android should map those failures to short user-facing messages and keep the user on the login screen.

## Testing And Verification

Backend tests should cover:

- Missing token returns a validation error.
- Invalid token returns 401.
- Unverified email is rejected.
- Valid token creates a user and session.
- Repeated login with the same Google subject reuses the same user.
- `GET /auth/me` returns the current user with a valid session token.
- Logout invalidates the current session.

Android verification should include:

- Gradle compile or assemble for the app.
- Login UI renders with the Google action.
- ViewModel login success stores session and navigates onward.
- Login cancellation or failure keeps the user on the login screen with a notice.

Manual end-to-end verification requires real Google Cloud OAuth credentials, so automated tests should mock the Google ID token verification boundary on the backend and the Credential Manager boundary on Android.

## Out Of Scope

- Node.js demo OAuth migration.
- Password, phone-code, or WeChat login.
- Production account settings, account deletion, or multi-provider linking UI.
- Server-side onboarding completion logic.
- Mandatory auth protection for every existing style task endpoint, beyond making the current user resolvable and attaching sessions from Android.
