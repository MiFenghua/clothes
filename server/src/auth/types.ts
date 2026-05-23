export type AuthProvider = "password" | "google" | "password_google";

export interface UserRecord {
  userId: string;
  email: string;
  name: string;
  avatarUrl: string | null;
  provider: AuthProvider;
  passwordHash?: string;
  passwordSalt?: string;
  googleSub?: string;
  createdAt: string;
  updatedAt: string;
}

export interface SessionRecord {
  sessionId: string;
  userId: string;
  tokenHash: string;
  createdAt: string;
  expiresAt: string;
}

export interface PublicUser {
  userId: string;
  email: string;
  name: string;
  avatarUrl: string | null;
  provider: AuthProvider;
}

export interface GoogleUserProfile {
  sub: string;
  email: string;
  emailVerified: boolean;
  name: string | null;
  avatarUrl: string | null;
}
