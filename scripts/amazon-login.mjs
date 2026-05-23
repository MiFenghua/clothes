import { mkdir } from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright-core";
import dotenv from "dotenv";

dotenv.config();

const chromePath =
  process.env.AMAZON_CHROME_PATH ?? process.env.TAOBAO_CHROME_PATH ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const userDataDir = process.env.AMAZON_USER_DATA_DIR ?? "server/storage/amazon-browser-profile";
const marketplaceBaseUrl = process.env.AMAZON_MARKETPLACE_BASE_URL ?? "https://www.amazon.com";

await mkdir(userDataDir, { recursive: true });

const context = await chromium.launchPersistentContext(path.resolve(userDataDir), {
  executablePath: chromePath,
  headless: false,
  locale: "en-US",
  viewport: { width: 1440, height: 1100 },
  args: ["--disable-blink-features=AutomationControlled", "--no-first-run"]
});

const page = context.pages()[0] ?? (await context.newPage());
await page.goto(marketplaceBaseUrl, {
  waitUntil: "domcontentloaded",
  timeout: 30000
});

console.log("请在打开的 Chrome 窗口中完成 Amazon 登录、地区选择或人机验证。");
console.log("完成后可以在该窗口搜索 women cropped knit top，确认能看到商品卡片和主图。");
console.log("完成后回到终端按 Enter 保存会话并关闭浏览器。");

process.stdin.setEncoding("utf8");
process.stdin.resume();
await new Promise((resolve) => process.stdin.once("data", resolve));

await context.close();
console.log("Amazon 浏览器会话已保存。");
