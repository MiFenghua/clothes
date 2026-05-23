import type { NextFunction, Request, Response } from "express";
import { config } from "../config.js";
import { AppError } from "../utils/http.js";
import type { AuthStore } from "./authStore.js";
import { readCookie } from "./cookies.js";
import type { PublicUser } from "./types.js";

export interface RequestWithUser extends Request {
  currentUser?: PublicUser | null;
}

export function attachCurrentUser(authStore: AuthStore) {
  return (req: Request, _res: Response, next: NextFunction) => {
    const token = readCookie(req.headers.cookie, config.authSessionCookieName);
    (req as RequestWithUser).currentUser = authStore.getUserBySessionToken(token);
    next();
  };
}

export function getCurrentUser(req: Request) {
  return (req as RequestWithUser).currentUser ?? null;
}

export function requireCurrentUser(req: Request) {
  const user = getCurrentUser(req);
  if (!user) {
    throw new AppError(401, "AUTH_REQUIRED", "请先登录");
  }
  return user;
}
