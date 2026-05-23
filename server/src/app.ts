import path from "node:path";
import cors from "cors";
import express from "express";
import { config } from "./config.js";
import { attachCurrentUser } from "./auth/currentUser.js";
import { createAuthRouter } from "./routes/auth.js";
import { createEventsRouter } from "./routes/events.js";
import { createInternalRouter } from "./routes/internal.js";
import { createStyleTaskRouter } from "./routes/styleTasks.js";
import { services } from "./container.js";

export function createApp() {
  const app = express();

  app.use(cors());
  app.use(express.json({ limit: "2mb" }));
  app.use(attachCurrentUser(services.authStore));
  app.use("/uploads", express.static(path.resolve(config.uploadDir)));
  app.use("/generated", express.static(path.resolve(config.generatedDir)));
  app.get(/^\/web$/, (_req, res) => {
    res.redirect("/web/");
  });
  app.use("/web", express.static(path.resolve("web")));

  app.get("/", (_req, res) => {
    res.type("html").send(`
      <!doctype html>
      <html lang="zh-CN">
        <head>
          <meta charset="utf-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1" />
          <title>clothes-api</title>
          <style>
            body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f6f3ef; color: #23201d; }
            main { max-width: 720px; margin: 0 auto; padding: 56px 24px; }
            h1 { margin: 0 0 12px; font-size: 32px; }
            p { line-height: 1.7; color: #5d554d; }
            code { background: #fffdf9; border: 1px solid #eadfd3; border-radius: 6px; padding: 2px 6px; }
            a { color: #1f1d1b; font-weight: 600; }
          </style>
        </head>
        <body>
          <main>
            <h1>clothes-api 正在运行</h1>
            <p>这是 AI 搭配师 Demo 的后端服务，不是小程序页面。</p>
            <p>Web 测试端：<a href="/web/">/web</a></p>
            <p>健康检查：<a href="/health">/health</a></p>
            <p>小程序请用微信开发者工具导入 <code>miniprogram/</code> 目录，并确认 <code>miniprogram/utils/config.js</code> 指向当前后端地址。</p>
          </main>
        </body>
      </html>
    `);
  });

  app.get("/health", (_req, res) => {
    res.json({
      ok: true,
      service: "clothes-api"
    });
  });

  app.use("/api/v1/auth", createAuthRouter(services.authStore));
  app.use("/api/v1/style-tasks", createStyleTaskRouter(services.taskStore, services.orchestrator));
  app.use("/api/v1/events", createEventsRouter());
  app.use("/internal", createInternalRouter(services.searchProvider, services.imageProvider));

  return app;
}
