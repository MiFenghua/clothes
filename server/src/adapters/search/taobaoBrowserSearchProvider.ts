import { mkdir } from "node:fs/promises";
import path from "node:path";
import { chromium, type BrowserContext, type Page } from "playwright-core";
import { config } from "../../config.js";
import type { Budget, OutfitStrategy, Product, ProductCategory } from "../../domain/types.js";
import type { SearchProvider, SearchProviderIssue } from "./searchProvider.js";
import { inferCategoryFromQuery } from "./demoSearchProvider.js";

interface ScrapedTaobaoItem {
  title: string;
  price: number;
  imageUrl: string;
  productUrl: string;
  shopName?: string;
  salesText?: string;
}

export class TaobaoBrowserSearchProvider implements SearchProvider {
  private contextPromise: Promise<BrowserContext> | null = null;
  private lastSearchIssue: SearchProviderIssue | null = null;

  async search({ strategy, budget, limitPerQuery }: { strategy: OutfitStrategy; budget: Budget; limitPerQuery: number }) {
    if (!config.taobaoBrowserEnabled) return [];
    this.lastSearchIssue = null;

    const products: Product[] = [];
    const queries = strategy.searchQueries.slice(0, Math.max(1, Math.ceil(limitPerQuery / 6)));

    for (const query of queries) {
      const category = inferCategoryFromQuery(query);
      const items = await this.searchOneQuery(query, category, budget, Math.max(6, Math.ceil(limitPerQuery / queries.length)));
      products.push(...items);
      if (products.length >= limitPerQuery) break;
    }

    return this.dedupe(products)
      .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
      .slice(0, limitPerQuery);
  }

  private async searchOneQuery(query: string, category: ProductCategory, budget: Budget, limit: number) {
    let page: Page | null = null;
    try {
      const context = await this.getContext();
      page = await context.newPage();
      await page.goto(`https://s.taobao.com/search?q=${encodeURIComponent(query)}`, {
        waitUntil: "domcontentloaded",
        timeout: config.taobaoSearchTimeoutMs
      });

      await this.waitForSearchResult(page);
      const scraped = await this.extractProducts(page, limit);
      return scraped
        .filter((item) => this.isUsableItem(item, budget))
        .map((item, index) => this.toProduct(item, query, category, budget, index));
    } catch (error) {
      console.warn(`[taobao-browser] ${query}: ${error instanceof Error ? error.message : String(error)}`);
      this.lastSearchIssue = this.toSearchIssue(error);
      if (this.shouldResetContext(error)) {
        await this.resetContext();
      }
      return [];
    } finally {
      await page?.close().catch(() => undefined);
    }
  }

  async close() {
    await this.resetContext();
  }

  getLastSearchIssue() {
    return this.lastSearchIssue;
  }

  private async getContext() {
    if (!this.contextPromise) {
      this.contextPromise = this.createContext().catch((error) => {
        this.contextPromise = null;
        throw error;
      });
    }
    return this.contextPromise;
  }

  private async createContext() {
    await mkdir(config.taobaoUserDataDir, { recursive: true });
    const context = await chromium.launchPersistentContext(path.resolve(config.taobaoUserDataDir), {
      executablePath: config.taobaoChromePath,
      headless: config.taobaoHeadless,
      locale: "zh-CN",
      viewport: { width: 1440, height: 1100 },
      userAgent:
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      args: ["--disable-blink-features=AutomationControlled", "--no-first-run", "--disable-dev-shm-usage"]
    });

    context.once("close", () => {
      const currentPromise = this.contextPromise;
      void currentPromise
        ?.then((currentContext) => {
          if (currentContext === context) {
            this.contextPromise = null;
          }
        })
        .catch(() => undefined);
    });

    return context;
  }

  private async resetContext() {
    const contextPromise = this.contextPromise;
    this.contextPromise = null;
    const context = await contextPromise?.catch(() => null);
    await context?.close().catch(() => undefined);
  }

  private shouldResetContext(error: unknown) {
    const message = error instanceof Error ? error.message : String(error);
    return /Target page, context or browser has been closed|Browser has been closed|launchPersistentContext|淘宝搜索需要登录|淘宝搜索触发验证|淘宝搜索超时/i.test(
      message
    );
  }

  private toSearchIssue(error: unknown): SearchProviderIssue {
    const message = error instanceof Error ? error.message : String(error);

    if (/淘宝搜索需要登录|请登录|登录/i.test(message)) {
      return {
        code: "TAOBAO_LOGIN_REQUIRED",
        provider: "taobao-browser",
        message: "淘宝搜索需要登录。请先运行 npm run taobao:login 完成人工登录，关闭登录窗口后重新发起测试。"
      };
    }

    if (/淘宝搜索触发验证|验证|滑块|baxia/i.test(message)) {
      return {
        code: "TAOBAO_VERIFICATION_REQUIRED",
        provider: "taobao-browser",
        message: "淘宝搜索触发安全验证。请运行 npm run taobao:login，在可见浏览器里完成验证后再测试。"
      };
    }

    if (/Target page, context or browser has been closed|Browser has been closed|launchPersistentContext|user data dir|profile/i.test(message)) {
      return {
        code: "TAOBAO_BROWSER_UNAVAILABLE",
        provider: "taobao-browser",
        message: "淘宝浏览器启动失败或 profile 被占用。请关闭使用 taobao-browser-profile 的 Chrome 窗口后重试。"
      };
    }

    return {
      code: "TAOBAO_TIMEOUT",
      provider: "taobao-browser",
      message: "淘宝搜索超时，暂时没有拿到真实商品卡片。请稍后重试或重新完成淘宝登录验证。"
    };
  }

  private async waitForSearchResult(page: Page) {
    const deadline = Date.now() + config.taobaoSearchTimeoutMs;

    while (Date.now() < deadline) {
      const state = await page.evaluate(() => {
        const text = document.body.innerText;
        const productLinks = document.querySelectorAll(
          'a[href*="item.taobao.com/item.htm"], a[href*="detail.tmall.com/item.htm"], a[href*="world.taobao.com/item/"]'
        ).length;
        return {
          productLinks,
          needsLogin: /亲，请登录|登录后|扫码登录|密码登录|会员登录/.test(text) && productLinks === 0,
          verifying: /验证|滑块|安全检测|请完成验证|baxia|加载中\.\.\./i.test(text) && productLinks === 0
        };
      });

      if (state.productLinks > 0) return;
      if (state.needsLogin) {
        throw new Error("淘宝搜索需要登录。请先运行 npm run taobao:login 完成人工登录。");
      }
      if (state.verifying && Date.now() + 2500 >= deadline) {
        throw new Error("淘宝搜索触发验证或一直加载中。请运行 npm run taobao:login 在可见浏览器里完成验证。");
      }

      await page.mouse.wheel(0, 650).catch(() => undefined);
      await page.waitForTimeout(1000);
    }

    throw new Error("淘宝搜索超时，未获取到商品卡片。");
  }

  private async extractProducts(page: Page, limit: number): Promise<ScrapedTaobaoItem[]> {
    return page.evaluate((maxItems) => {
      const normalizeUrl = (url: string) => {
        if (!url) return "";
        if (url.startsWith("//")) return `https:${url}`;
        if (url.startsWith("/")) return `https://s.taobao.com${url}`;
        return url;
      };

      const productIdOf = (url: string) => {
        try {
          const parsed = new URL(normalizeUrl(url));
          return parsed.searchParams.get("id") ?? parsed.pathname.match(/item\/(\d+)/)?.[1] ?? "";
        } catch {
          return "";
        }
      };

      const isProductUrl = (url: string) => {
        const normalized = normalizeUrl(url);
        return /https:\/\/(item\.taobao\.com\/item\.htm|detail\.tmall\.com\/item\.htm|world\.taobao\.com\/item\/)/i.test(normalized);
      };

      const pickImage = (root: Element) => {
        const imgs = Array.from(root.querySelectorAll("img"));
        for (const img of imgs) {
          const src =
            img.getAttribute("src") ||
            img.getAttribute("data-src") ||
            img.getAttribute("data-ks-lazyload") ||
            img.getAttribute("data-lazyload-src") ||
            "";
          const normalized = normalizeUrl(src);
          if (normalized && !/TB1QZN|data:image|transparent|loading|placeholder/i.test(normalized)) {
            return normalized;
          }
        }
        return "";
      };

      const pickPrice = (text: string) => {
        const priceMatches = Array.from(text.matchAll(/(?:¥|￥)?\s*(\d{1,5}(?:\.\d{1,2})?)/g))
          .map((match) => Number(match[1]))
          .filter((value) => value > 1 && value < 100000);
        return priceMatches[0] ?? 0;
      };

      const pickTitle = (anchor: HTMLAnchorElement, root: Element, imageUrl: string) => {
        const imgAlt = Array.from(root.querySelectorAll("img"))
          .map((img) => img.getAttribute("alt")?.trim())
          .find(Boolean);
        const textLines = root.textContent
          ?.split(/\n|\s{2,}/)
          .map((line) => line.trim())
          .filter((line) => line.length > 6 && !/^¥|￥|\d+人/.test(line));
        return (imgAlt || anchor.textContent?.trim() || textLines?.[0] || imageUrl.split("/").pop() || "淘宝商品").slice(0, 120);
      };

      const anchors = Array.from(
        document.querySelectorAll<HTMLAnchorElement>(
          'a[href*="item.taobao.com/item.htm"], a[href*="detail.tmall.com/item.htm"], a[href*="world.taobao.com/item/"]'
        )
      );
      const seen = new Set<string>();
      const items: ScrapedTaobaoItem[] = [];

      for (const anchor of anchors) {
        const productUrl = normalizeUrl(anchor.href || anchor.getAttribute("href") || "");
        if (!isProductUrl(productUrl)) continue;

        const productId = productIdOf(productUrl);
        if (productId && seen.has(productId)) continue;
        if (productUrl && seen.has(productUrl)) continue;

        const root =
          anchor.closest('[data-nid], [data-item-id], [class*="Card"], [class*="card"], [class*="item"], [class*="Item"]') ||
          anchor.parentElement ||
          anchor;
        const imageUrl = pickImage(root);
        const text = root.textContent ?? "";
        const price = pickPrice(text);
        const title = pickTitle(anchor, root, imageUrl);

        if (!title || !imageUrl || !price) continue;

        seen.add(productId || productUrl);
        items.push({
          title,
          price,
          imageUrl,
          productUrl,
          shopName: Array.from(root.querySelectorAll("a, span, div"))
            .map((node) => node.textContent?.trim())
            .find((value) => Boolean(value && value.length >= 2 && value.length <= 24 && /店|旗舰|淘宝|天猫/.test(value))),
          salesText: text.match(/\d+(?:\.\d+)?万?\+?人(?:付款|购买|看过)|月销\s*\d+(?:\.\d+)?万?\+?/i)?.[0]
        });

        if (items.length >= maxItems) break;
      }

      return items;
    }, limit);
  }

  private isUsableItem(item: ScrapedTaobaoItem, budget: Budget) {
    if (!item.title || !item.imageUrl || !item.productUrl || !item.price) return false;
    if (budget.max && item.price > budget.max * 1.5) return false;
    return true;
  }

  private toProduct(item: ScrapedTaobaoItem, query: string, category: ProductCategory, budget: Budget, index: number): Product {
    const platform = item.productUrl.includes("tmall.com") ? "tmall" : "taobao";
    const productId = `${platform}_${this.extractProductId(item.productUrl) || Buffer.from(item.productUrl).toString("base64url").slice(0, 12)}`;
    const budgetScore = budget.max ? Math.max(0, 1 - item.price / (budget.max * 1.5)) : 0.7;

    return {
      productId,
      platform,
      category,
      title: item.title,
      price: item.price,
      imageUrl: item.imageUrl,
      productUrl: item.productUrl,
      isExternalSearchLanding: false,
      shopName: item.shopName,
      salesText: item.salesText,
      colors: [],
      sizes: [],
      styleTags: [query],
      fitTags: [],
      reason: `来自淘宝搜索“${query}”的实际商品卡片，可作为试穿参考。`,
      score: 0.55 + Math.max(0.1, 1 - index * 0.04) * 0.25 + budgetScore * 0.2,
      raw: item
    };
  }

  private extractProductId(url: string) {
    try {
      const parsed = new URL(url);
      return parsed.searchParams.get("id") ?? parsed.pathname.match(/item\/(\d+)/)?.[1] ?? undefined;
    } catch {
      return undefined;
    }
  }

  private dedupe(products: Product[]) {
    const seen = new Set<string>();
    return products.filter((product) => {
      const key = product.productId || product.productUrl;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }
}
