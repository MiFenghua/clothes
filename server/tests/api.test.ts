import { after, describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { createServer, type Server } from "node:http";
import path from "node:path";

process.env.SEARCH_PROVIDER = "external";
process.env.VISION_PROVIDER = "local";
process.env.IMAGE_PROVIDER = "unavailable";
process.env.GOOGLE_CLIENT_ID = "";
process.env.GOOGLE_CLIENT_SECRET = "";
const authStorePath = path.resolve("server/storage/test-auth-store.json");
process.env.AUTH_STORE_PATH = authStorePath;
fs.rmSync(authStorePath, { force: true });

const { createApp } = await import("../src/app.js");
const app = createApp();
const server: Server = createServer(app);

const baseUrl = await new Promise<string>((resolve) => {
  server.listen(0, "127.0.0.1", () => {
    const address = server.address();
    if (!address || typeof address === "string") {
      throw new Error("Unexpected test server address");
    }
    resolve(`http://127.0.0.1:${address.port}`);
  });
});

after(() => {
  server.close();
  fs.rmSync(authStorePath, { force: true });
});

function sessionCookieFrom(response: Response) {
  const setCookie = response.headers.get("set-cookie");
  assert.ok(setCookie, "Expected auth response to set a session cookie");
  return setCookie.split(";")[0];
}

async function requestJson<T = Record<string, unknown>>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(init?.headers ?? {})
    }
  });
  const body = (await response.json()) as T;
  assert.ok(response.ok, JSON.stringify(body));
  return body;
}

async function waitForTerminalTask(taskId: string) {
  for (let index = 0; index < 60; index += 1) {
    const body = await requestJson<{ status: string; errorCode?: string }>(`/api/v1/style-tasks/${taskId}`);
    if (["succeeded", "failed"].includes(body.status)) {
      return body;
    }
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  throw new Error("Task did not reach terminal status");
}

describe("clothes api", () => {
  it("returns health status", async () => {
    const body = await requestJson("/health");
    assert.deepEqual(body, {
      ok: true,
      service: "clothes-api"
    });
  });

  it("serves the web test client", async () => {
    const response = await fetch(`${baseUrl}/web/`);
    const html = await response.text();
    assert.equal(response.status, 200);
    assert.match(html, /AI 搭配师 Web 测试端/);
  });

  it("supports email registration, session lookup, logout and login", async () => {
    const email = "style-user@example.com";
    const password = "strong-password-123";

    const registerResponse = await fetch(`${baseUrl}/api/v1/auth/register`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ email, password, name: "Style User" })
    });
    const registered = (await registerResponse.json()) as { user: { email: string; name: string } };
    assert.equal(registerResponse.status, 201, JSON.stringify(registered));
    assert.equal(registered.user.email, email);
    assert.equal(registered.user.name, "Style User");

    const cookie = sessionCookieFrom(registerResponse);
    const me = await requestJson<{ user: { email: string } }>("/api/v1/auth/me", {
      headers: { cookie }
    });
    assert.equal(me.user.email, email);

    const logoutResponse = await fetch(`${baseUrl}/api/v1/auth/logout`, {
      method: "POST",
      headers: { cookie }
    });
    assert.equal(logoutResponse.status, 200);

    const loggedOut = await requestJson<{ user: null }>("/api/v1/auth/me", {
      headers: { cookie }
    });
    assert.equal(loggedOut.user, null);

    const loginResponse = await fetch(`${baseUrl}/api/v1/auth/login`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    const loggedIn = (await loginResponse.json()) as { user: { email: string } };
    assert.equal(loginResponse.status, 200, JSON.stringify(loggedIn));
    assert.equal(loggedIn.user.email, email);
    sessionCookieFrom(loginResponse);
  });

  it("reports google login as disabled when OAuth credentials are missing", async () => {
    const body = await requestJson<{ googleEnabled: boolean; googleClientId: string | null }>("/api/v1/auth/config");

    assert.equal(body.googleEnabled, false);
    assert.equal(body.googleClientId, null);
  });

  it("returns demo product candidates", async () => {
    const body = await requestJson<{ products: Array<{ title: string; productUrl: string }> }>("/internal/search-products", {
      method: "POST",
      body: JSON.stringify({
        queries: ["短款针织上衣 女 春夏", "高腰直筒牛仔裤 女"],
        budget: { min: 300, max: 800 },
        limitPerQuery: 20
      })
    });

    assert.ok(body.products.length >= 4);
    assert.equal(typeof body.products[0].title, "string");
    assert.equal(typeof body.products[0].productUrl, "string");
  });

  it("does not generate try-on images from search landing links", async () => {
    const formData = new FormData();
    formData.append("scene", "daily");
    formData.append("budgetMin", "300");
    formData.append("budgetMax", "800");
    formData.append("ageYears", "");
    formData.append("heightCm", "");
    formData.append("weightKg", "");
    formData.append("photo", new Blob(["fake-image-bytes"], { type: "image/jpeg" }), "full-body.jpg");

    const createResponse = await fetch(`${baseUrl}/api/v1/style-tasks`, {
      method: "POST",
      body: formData
    });
    const created = (await createResponse.json()) as { taskId: string };
    assert.equal(createResponse.status, 201, JSON.stringify(created));

    const terminal = await waitForTerminalTask(created.taskId);
    assert.equal(terminal.status, "failed");
    assert.equal(terminal.errorCode, "OUTFIT_BUILD_FAILED");

    const result = await requestJson<{ status: string }>(`/api/v1/style-tasks/${created.taskId}/result`);
    assert.equal(result.status, "failed");
    assert.equal(Object.hasOwn(result, "tryOnImageUrl"), false);
  });
});
