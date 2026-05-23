import type { CookieOptions, Response } from "express";
import { config } from "../config.js";

const isSecureCookie = () => config.publicBaseUrl.startsWith("https://");

const baseCookieOptions = (): CookieOptions => ({
  httpOnly: true,
  sameSite: "lax",
  secure: isSecureCookie(),
  path: "/"
});

export function readCookie(cookieHeader: string | undefined, name: string) {
  if (!cookieHeader) return null;

  const pairs = cookieHeader.split(";");
  for (const pair of pairs) {
    const separatorIndex = pair.indexOf("=");
    if (separatorIndex < 0) continue;
    const key = pair.slice(0, separatorIndex).trim();
    if (key !== name) continue;
    return decodeURIComponent(pair.slice(separatorIndex + 1).trim());
  }

  return null;
}

export function setSessionCookie(res: Response, token: string, expiresAt: string) {
  res.cookie(config.authSessionCookieName, token, {
    ...baseCookieOptions(),
    expires: new Date(expiresAt)
  });
}

export function clearSessionCookie(res: Response) {
  res.clearCookie(config.authSessionCookieName, baseCookieOptions());
}

export function setGoogleStateCookie(res: Response, state: string) {
  res.cookie(config.googleOAuthStateCookieName, state, {
    ...baseCookieOptions(),
    maxAge: 10 * 60 * 1000
  });
}

export function clearGoogleStateCookie(res: Response) {
  res.clearCookie(config.googleOAuthStateCookieName, baseCookieOptions());
}
