import { mkdir } from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright-core";
import dotenv from "dotenv";

dotenv.config();

const chromePath = process.env.TAOBAO_CHROME_PATH ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const userDataDir = process.env.TAOBAO_USER_DATA_DIR ?? "server/storage/taobao-browser-profile";

await mkdir(userDataDir, { recursive: true });

const context = await chromium.launchPersistentContext(path.resolve(userDataDir), {
  executablePath: chromePath,
  headless: false,
  locale: "zh-CN",
  viewport: { width: 1440, height: 1100 },
  args: ["--disable-blink-features=AutomationControlled", "--no-first-run"]
});

const page = context.pages()[0] ?? (await context.newPage());
await page.goto("https://login.taobao.com/member/login.jhtml", {
  waitUntil: "domcontentloaded",
  timeout: 30000
});

console.log("请在打开的 Chrome 窗口中登录淘宝，并完成可能出现的验证。");
console.log("登录完成后可以在该窗口打开 https://s.taobao.com/search?q=短款针织上衣 测试是否能看到商品。");
console.log("完成后回到终端按 Enter 保存会话并关闭浏览器。");

process.stdin.setEncoding("utf8");
process.stdin.resume();
await new Promise((resolve) => process.stdin.once("data", resolve));

await context.close();
console.log("淘宝登录会话已保存。");
