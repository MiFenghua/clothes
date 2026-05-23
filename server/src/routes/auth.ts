import crypto from "node:crypto";
import type { Router } from "express";
import express from "express";
import { z } from "zod";
import { config } from "../config.js";
import { getCurrentUser } from "../auth/currentUser.js";
import type { AuthStore } from "../auth/authStore.js";
import { clearGoogleStateCookie, clearSessionCookie, readCookie, setGoogleStateCookie, setSessionCookie } from "../auth/cookies.js";
import type { GoogleUserProfile } from "../auth/types.js";
import { AppError, sendError } from "../utils/http.js";

const passwordAuthSchema = z.object({
  email: z.string().trim().email().max(254),
  password: z.string().min(8).max(128),
  name: z.string().trim().max(80).optional()
});

const googleCredentialSchema = z.object({
  credential: z.string().min(20)
});

const googleOAuthConfigured = () => Boolean(config.googleClientId && config.googleClientSecret);
const googleCredentialConfigured = () => Boolean(config.googleClientId);

const googleRedirectUri = () => config.googleOAuthRedirectUri || `${config.publicBaseUrl}/api/v1/auth/google/callback`;

const webAuthRedirect = (status: "google_success" | "google_failed" | "google_not_configured") => `/web/?auth=${status}`;

function parsePayload<T>(schema: z.ZodType<T>, payload: unknown) {
  const parsed = schema.safeParse(payload);
  if (!parsed.success) {
    throw new AppError(400, "INVALID_AUTH_PAYLOAD", "登录信息格式不正确");
  }
  return parsed.data;
}

async function readJson<T>(response: Response): Promise<T> {
  return (await response.json()) as T;
}

async function fetchGoogleUserInfo(accessToken: string): Promise<GoogleUserProfile> {
  const response = await fetch("https://www.googleapis.com/oauth2/v3/userinfo", {
    headers: {
      authorization: `Bearer ${accessToken}`
    }
  });
  const body = await readJson<{
    sub?: string;
    email?: string;
    email_verified?: boolean | string;
    name?: string;
    picture?: string;
  }>(response);

  if (!response.ok || !body.sub || !body.email) {
    throw new AppError(502, "GOOGLE_PROFILE_FAILED", "Google 登录信息获取失败");
  }

  return {
    sub: body.sub,
    email: body.email,
    emailVerified: body.email_verified === true || body.email_verified === "true",
    name: body.name ?? null,
    avatarUrl: body.picture ?? null
  };
}

async function exchangeGoogleCode(code: string): Promise<GoogleUserProfile> {
  if (!config.googleClientId || !config.googleClientSecret) {
    throw new AppError(503, "GOOGLE_AUTH_NOT_CONFIGURED", "Google 登录未配置");
  }

  const response = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: {
      "content-type": "application/x-www-form-urlencoded"
    },
    body: new URLSearchParams({
      client_id: config.googleClientId,
      client_secret: config.googleClientSecret,
      code,
      grant_type: "authorization_code",
      redirect_uri: googleRedirectUri()
    })
  });
  const body = await readJson<{ access_token?: string; error?: string }>(response);

  if (!response.ok || !body.access_token) {
    throw new AppError(502, "GOOGLE_TOKEN_EXCHANGE_FAILED", "Google 登录授权失败");
  }

  return fetchGoogleUserInfo(body.access_token);
}

async function verifyGoogleCredential(credential: string): Promise<GoogleUserProfile> {
  if (!config.googleClientId) {
    throw new AppError(503, "GOOGLE_AUTH_NOT_CONFIGURED", "Google 登录未配置");
  }

  const response = await fetch(`https://oauth2.googleapis.com/tokeninfo?id_token=${encodeURIComponent(credential)}`);
  const body = await readJson<{
    aud?: string;
    sub?: string;
    email?: string;
    email_verified?: boolean | string;
    name?: string;
    picture?: string;
  }>(response);

  if (!response.ok || body.aud !== config.googleClientId || !body.sub || !body.email) {
    throw new AppError(401, "GOOGLE_CREDENTIAL_INVALID", "Google 登录凭证无效");
  }

  return {
    sub: body.sub,
    email: body.email,
    emailVerified: body.email_verified === true || body.email_verified === "true",
    name: body.name ?? null,
    avatarUrl: body.picture ?? null
  };
}

function signIn(res: express.Response, authStore: AuthStore, userId: string) {
  const session = authStore.createSession(userId);
  setSessionCookie(res, session.token, session.expiresAt);
}

export function createAuthRouter(authStore: AuthStore): Router {
  const router = express.Router();

  router.get("/config", (_req, res) => {
    res.json({
      googleEnabled: googleOAuthConfigured(),
      googleCredentialEnabled: googleCredentialConfigured(),
      googleClientId: config.googleClientId ?? null
    });
  });

  router.get("/me", (req, res) => {
    res.json({
      user: getCurrentUser(req)
    });
  });

  router.post("/register", (req, res) => {
    try {
      const payload = parsePayload(passwordAuthSchema, req.body);
      const user = authStore.registerWithPassword(payload);
      signIn(res, authStore, user.userId);
      res.status(201).json({ user });
    } catch (error) {
      sendError(res, error);
    }
  });

  router.post("/login", (req, res) => {
    try {
      const payload = parsePayload(passwordAuthSchema.omit({ name: true }), req.body);
      const user = authStore.loginWithPassword(payload.email, payload.password);
      signIn(res, authStore, user.userId);
      res.json({ user });
    } catch (error) {
      sendError(res, error);
    }
  });

  router.post("/logout", (req, res) => {
    const token = readCookie(req.headers.cookie, config.authSessionCookieName);
    authStore.destroySession(token);
    clearSessionCookie(res);
    res.json({ ok: true });
  });

  router.get("/google", (_req, res) => {
    if (!googleOAuthConfigured()) {
      res.redirect(webAuthRedirect("google_not_configured"));
      return;
    }

    const state = crypto.randomBytes(20).toString("base64url");
    setGoogleStateCookie(res, state);
    const url = new URL("https://accounts.google.com/o/oauth2/v2/auth");
    url.searchParams.set("client_id", config.googleClientId ?? "");
    url.searchParams.set("redirect_uri", googleRedirectUri());
    url.searchParams.set("response_type", "code");
    url.searchParams.set("scope", "openid email profile");
    url.searchParams.set("state", state);
    url.searchParams.set("prompt", "select_account");
    res.redirect(url.toString());
  });

  router.get("/google/start", (_req, res) => {
    res.redirect("/api/v1/auth/google");
  });

  router.get("/google/callback", async (req, res) => {
    try {
      const expectedState = readCookie(req.headers.cookie, config.googleOAuthStateCookieName);
      const receivedState = typeof req.query.state === "string" ? req.query.state : "";
      const code = typeof req.query.code === "string" ? req.query.code : "";
      if (!expectedState || expectedState !== receivedState || !code) {
        throw new AppError(401, "GOOGLE_STATE_INVALID", "Google 登录状态无效");
      }

      const profile = await exchangeGoogleCode(code);
      const user = authStore.loginWithGoogle(profile);
      signIn(res, authStore, user.userId);
      clearGoogleStateCookie(res);
      res.redirect(webAuthRedirect("google_success"));
    } catch (_error) {
      clearGoogleStateCookie(res);
      res.redirect(webAuthRedirect("google_failed"));
    }
  });

  router.post("/google/credential", async (req, res) => {
    try {
      const payload = parsePayload(googleCredentialSchema, req.body);
      const profile = await verifyGoogleCredential(payload.credential);
      const user = authStore.loginWithGoogle(profile);
      signIn(res, authStore, user.userId);
      res.json({ user });
    } catch (error) {
      sendError(res, error);
    }
  });

  return router;
}
