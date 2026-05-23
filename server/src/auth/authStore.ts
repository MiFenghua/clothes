import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { nanoid } from "nanoid";
import { config } from "../config.js";
import { AppError } from "../utils/http.js";
import type { GoogleUserProfile, PublicUser, SessionRecord, UserRecord } from "./types.js";

interface AuthStoreData {
  users: UserRecord[];
  sessions: SessionRecord[];
}

const emptyData = (): AuthStoreData => ({
  users: [],
  sessions: []
});

const normalizeEmail = (email: string) => email.trim().toLowerCase();

const nowIso = () => new Date().toISOString();

function hashToken(token: string) {
  return crypto.createHash("sha256").update(token).digest("base64url");
}

function publicUser(user: UserRecord): PublicUser {
  return {
    userId: user.userId,
    email: user.email,
    name: user.name,
    avatarUrl: user.avatarUrl,
    provider: user.provider
  };
}

export class AuthStore {
  private data: AuthStoreData;

  constructor(private readonly storePath = config.authStorePath) {
    this.data = this.load();
    this.pruneExpiredSessions();
  }

  registerWithPassword(input: { email: string; password: string; name?: string | null }) {
    const email = normalizeEmail(input.email);
    if (this.findUserByEmail(email)) {
      throw new AppError(409, "EMAIL_ALREADY_REGISTERED", "该邮箱已注册");
    }

    const { salt, hash } = this.hashPassword(input.password);
    const timestamp = nowIso();
    const user: UserRecord = {
      userId: `user_${nanoid(12)}`,
      email,
      name: input.name?.trim() || email.split("@")[0] || "用户",
      avatarUrl: null,
      provider: "password",
      passwordHash: hash,
      passwordSalt: salt,
      createdAt: timestamp,
      updatedAt: timestamp
    };

    this.data.users.push(user);
    this.save();
    return publicUser(user);
  }

  loginWithPassword(emailInput: string, password: string) {
    const email = normalizeEmail(emailInput);
    const user = this.findUserByEmail(email);
    if (!user || !user.passwordHash || !user.passwordSalt || !this.verifyPassword(user, password)) {
      throw new AppError(401, "INVALID_CREDENTIALS", "邮箱或密码不正确");
    }

    return publicUser(user);
  }

  loginWithGoogle(profile: GoogleUserProfile) {
    if (!profile.emailVerified) {
      throw new AppError(401, "GOOGLE_EMAIL_UNVERIFIED", "Google 邮箱尚未验证");
    }

    const email = normalizeEmail(profile.email);
    const existingByGoogle = this.data.users.find((user) => user.googleSub === profile.sub);
    const existingByEmail = this.findUserByEmail(email);
    const user = existingByGoogle ?? existingByEmail;

    if (user) {
      user.googleSub = profile.sub;
      user.provider = user.passwordHash ? "password_google" : "google";
      user.name = profile.name || user.name;
      user.avatarUrl = profile.avatarUrl || user.avatarUrl;
      user.updatedAt = nowIso();
      this.save();
      return publicUser(user);
    }

    const timestamp = nowIso();
    const created: UserRecord = {
      userId: `user_${nanoid(12)}`,
      email,
      name: profile.name || email.split("@")[0] || "Google 用户",
      avatarUrl: profile.avatarUrl,
      provider: "google",
      googleSub: profile.sub,
      createdAt: timestamp,
      updatedAt: timestamp
    };

    this.data.users.push(created);
    this.save();
    return publicUser(created);
  }

  createSession(userId: string) {
    this.pruneExpiredSessions();
    const token = crypto.randomBytes(32).toString("base64url");
    const createdAt = new Date();
    const expiresAt = new Date(createdAt.getTime() + config.authSessionMaxAgeDays * 24 * 60 * 60 * 1000);
    const session: SessionRecord = {
      sessionId: `session_${nanoid(12)}`,
      userId,
      tokenHash: hashToken(token),
      createdAt: createdAt.toISOString(),
      expiresAt: expiresAt.toISOString()
    };

    this.data.sessions.push(session);
    this.save();
    return {
      token,
      expiresAt: session.expiresAt
    };
  }

  getUserBySessionToken(token: string | null) {
    if (!token) return null;
    this.pruneExpiredSessions();
    const tokenHash = hashToken(token);
    const session = this.data.sessions.find((candidate) => candidate.tokenHash === tokenHash);
    if (!session) return null;

    const user = this.data.users.find((candidate) => candidate.userId === session.userId);
    return user ? publicUser(user) : null;
  }

  destroySession(token: string | null) {
    if (!token) return;
    const tokenHash = hashToken(token);
    const nextSessions = this.data.sessions.filter((session) => session.tokenHash !== tokenHash);
    if (nextSessions.length === this.data.sessions.length) return;
    this.data.sessions = nextSessions;
    this.save();
  }

  private findUserByEmail(email: string) {
    return this.data.users.find((user) => user.email === email);
  }

  private hashPassword(password: string) {
    const salt = crypto.randomBytes(16).toString("base64url");
    const hash = crypto.scryptSync(password, salt, 64).toString("base64url");
    return { salt, hash };
  }

  private verifyPassword(user: UserRecord, password: string) {
    if (!user.passwordHash || !user.passwordSalt) return false;
    const expected = Buffer.from(user.passwordHash, "base64url");
    const actual = crypto.scryptSync(password, user.passwordSalt, expected.length);
    return expected.length === actual.length && crypto.timingSafeEqual(expected, actual);
  }

  private pruneExpiredSessions() {
    const now = Date.now();
    const nextSessions = this.data.sessions.filter((session) => new Date(session.expiresAt).getTime() > now);
    if (nextSessions.length === this.data.sessions.length) return;
    this.data.sessions = nextSessions;
    this.save();
  }

  private load(): AuthStoreData {
    const resolved = path.resolve(this.storePath);
    if (!fs.existsSync(resolved)) {
      return emptyData();
    }

    const parsed = JSON.parse(fs.readFileSync(resolved, "utf8")) as Partial<AuthStoreData>;
    return {
      users: Array.isArray(parsed.users) ? parsed.users : [],
      sessions: Array.isArray(parsed.sessions) ? parsed.sessions : []
    };
  }

  private save() {
    const resolved = path.resolve(this.storePath);
    fs.mkdirSync(path.dirname(resolved), { recursive: true });
    fs.writeFileSync(resolved, `${JSON.stringify(this.data, null, 2)}\n`, "utf8");
  }
}
