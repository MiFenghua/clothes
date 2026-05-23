import { mkdir } from "node:fs/promises";
import path from "node:path";
import { chromium, type BrowserContext, type Page } from "playwright-core";
import { config } from "../../config.js";
import type { Budget, OutfitStrategy, Product, ProductCategory } from "../../domain/types.js";
import type { SearchProvider, SearchProviderIssue } from "./searchProvider.js";
import { buildAmazonSearchUrl, getAmazonMarketplaceOrigin } from "./amazonSearchUrl.js";
import { inferCategoryFromQuery } from "./demoSearchProvider.js";

interface ScrapedAmazonItem {
  asin: string;
  title: string;
  priceText?: string;
  imageUrl: string;
  productUrl: string;
  shopName?: string;
  salesText?: string;
}

export class AmazonBrowserSearchProvider implements SearchProvider {
  private contextPromise: Promise<BrowserContext> | null = null;
  private lastSearchIssue: SearchProviderIssue | null = null;

  async search({ strategy, limitPerQuery }: { strategy: OutfitStrategy; budget: Budget; limitPerQuery: number }) {
    if (!config.amazonBrowserEnabled) return [];
    this.lastSearchIssue = null;

    const products: Product[] = [];
    const queries = strategy.searchQueries.slice(0, Math.max(1, Math.ceil(limitPerQuery / 6)));

    for (const query of queries) {
      const category = inferCategoryFromQuery(query);
      const amazonQuery = this.toAmazonQuery(query, category);
      const items = await this.searchOneQuery(amazonQuery, query, category, Math.max(6, Math.ceil(limitPerQuery / queries.length)));
      products.push(...items);
      if (products.length >= limitPerQuery) break;
    }

    return this.dedupe(products)
      .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
      .slice(0, limitPerQuery);
  }

  private async searchOneQuery(amazonQuery: string, originalQuery: string, category: ProductCategory, limit: number) {
    let page: Page | null = null;
    try {
      const context = await this.getContext();
      page = await context.newPage();
      await page.goto(buildAmazonSearchUrl(amazonQuery), {
        waitUntil: "domcontentloaded",
        timeout: config.amazonSearchTimeoutMs
      });

      await this.waitForSearchResult(page);
      const scraped = await this.extractProducts(page, limit);
      return scraped
        .filter((item) => this.isUsableItem(item))
        .map((item, index) => this.toProduct(item, amazonQuery, originalQuery, category, index));
    } catch (error) {
      console.warn(`[amazon-browser] ${amazonQuery}: ${error instanceof Error ? error.message : String(error)}`);
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
    await mkdir(config.amazonUserDataDir, { recursive: true });
    const context = await chromium.launchPersistentContext(path.resolve(config.amazonUserDataDir), {
      executablePath: config.amazonChromePath,
      headless: config.amazonHeadless,
      locale: "en-US",
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
    return /Target page, context or browser has been closed|Browser has been closed|launchPersistentContext|Amazon 搜索触发验证|Amazon 搜索超时/i.test(
      message
    );
  }

  private toSearchIssue(error: unknown): SearchProviderIssue {
    const message = error instanceof Error ? error.message : String(error);

    if (/Amazon 搜索触发验证|Robot Check|CAPTCHA|not a robot|characters you see|automated access/i.test(message)) {
      return {
        code: "AMAZON_VERIFICATION_REQUIRED",
        provider: "amazon-browser",
        message: "Amazon 搜索触发人机验证。请运行 npm run amazon:login，在可见浏览器里完成验证或登录后再测试。"
      };
    }

    if (/Target page, context or browser has been closed|Browser has been closed|launchPersistentContext|user data dir|profile/i.test(message)) {
      return {
        code: "AMAZON_BROWSER_UNAVAILABLE",
        provider: "amazon-browser",
        message: "Amazon 浏览器启动失败或 profile 被占用。请关闭使用 amazon-browser-profile 的 Chrome 窗口后重试。"
      };
    }

    return {
      code: "AMAZON_TIMEOUT",
      provider: "amazon-browser",
      message: "Amazon 搜索超时，暂时没有拿到真实商品卡片。请稍后重试或运行 npm run amazon:login 完成验证。"
    };
  }

  private async waitForSearchResult(page: Page) {
    const deadline = Date.now() + config.amazonSearchTimeoutMs;

    while (Date.now() < deadline) {
      const state = await page.evaluate(() => {
        const text = document.body.innerText;
        const productCards = document.querySelectorAll('[data-component-type="s-search-result"][data-asin]').length;
        const productLinks = document.querySelectorAll('a[href*="/dp/"], a[href*="/gp/product/"]').length;
        return {
          productCards,
          productLinks,
          blocked: /Robot Check|Enter the characters you see below|not a robot|CAPTCHA|automated access|Sorry, we just need to make sure/i.test(
            text
          ),
          noResults: /No results for|Try checking your spelling|did not match any products/i.test(text)
        };
      });

      if (state.productCards > 0 || state.productLinks > 0) return;
      if (state.blocked) {
        throw new Error("Amazon 搜索触发验证。请运行 npm run amazon:login 在可见浏览器里完成验证。");
      }
      if (state.noResults) return;

      await page.mouse.wheel(0, 650).catch(() => undefined);
      await page.waitForTimeout(1000);
    }

    throw new Error("Amazon 搜索超时，未获取到商品卡片。");
  }

  private async extractProducts(page: Page, limit: number): Promise<ScrapedAmazonItem[]> {
    return page.evaluate(
      ({ maxItems, marketplaceOrigin }) => {
        const normalizeUrl = (url: string) => {
          if (!url) return "";
          try {
            if (url.startsWith("//")) return `https:${url}`;
            return new URL(url, marketplaceOrigin).href;
          } catch {
            return "";
          }
        };

        const extractAsin = (root: Element, url: string) => {
          const asin = root.getAttribute("data-asin")?.trim();
          if (asin) return asin;
          return normalizeUrl(url).match(/\/(?:dp|gp\/product)\/([A-Z0-9]{10})(?:[/?]|$)/i)?.[1] ?? "";
        };

        const canonicalProductUrl = (asin: string, url: string) => {
          const normalized = normalizeUrl(url);
          const productAsin = asin || normalized.match(/\/(?:dp|gp\/product)\/([A-Z0-9]{10})(?:[/?]|$)/i)?.[1] || "";
          return productAsin ? `${marketplaceOrigin}/dp/${productAsin}` : normalized;
        };

        const pickImage = (root: Element) => {
          const image = root.querySelector<HTMLImageElement>("img.s-image") ?? root.querySelector<HTMLImageElement>("img");
          const srcset = image?.getAttribute("srcset")?.split(/\s+/)[0] ?? "";
          const src = image?.currentSrc || image?.src || image?.getAttribute("data-src") || image?.getAttribute("src") || srcset;
          const normalized = normalizeUrl(src);
          if (!normalized || /data:image|transparent|grey-pixel|spinner|sprite|favicon/i.test(normalized)) return "";
          return normalized.replace(/\._[^/]*_\.(jpe?g|png|webp)(\?.*)?$/i, ".$1$2");
        };

        const pickTitle = (root: Element, anchor: HTMLAnchorElement | null, imageUrl: string) => {
          const imageAlt = root.querySelector<HTMLImageElement>("img.s-image")?.alt?.trim();
          const headingText =
            root.querySelector("h2 span")?.textContent?.trim() ||
            root.querySelector("[data-cy='title-recipe'] span")?.textContent?.trim() ||
            root.querySelector(".a-size-base-plus.a-color-base.a-text-normal")?.textContent?.trim();
          const anchorText = anchor?.textContent?.replace(/\s+/g, " ").trim();
          return (headingText || imageAlt || anchorText || imageUrl.split("/").pop() || "Amazon product").slice(0, 160);
        };

        const pickPriceText = (root: Element) => {
          return (
            root.querySelector(".a-price .a-offscreen")?.textContent?.trim() ||
            root.querySelector(".a-color-price")?.textContent?.trim() ||
            undefined
          );
        };

        const pickSalesText = (root: Element) => {
          return (
            root.querySelector(".a-icon-alt")?.textContent?.trim() ||
            Array.from(root.querySelectorAll("span, div"))
              .map((node) => node.textContent?.replace(/\s+/g, " ").trim())
              .find((value) => Boolean(value && /bought|sold|stars|reviews/i.test(value)))
          );
        };

        const cards = Array.from(
          document.querySelectorAll('[data-component-type="s-search-result"][data-asin], [data-asin][data-index]')
        );
        const roots =
          cards.length > 0
            ? cards
            : Array.from(document.querySelectorAll('a[href*="/dp/"], a[href*="/gp/product/"]')).map(
                (anchor) => anchor.closest("[data-asin], .s-result-item, div") ?? anchor
              );
        const seen = new Set<string>();
        const items: ScrapedAmazonItem[] = [];

        for (const root of roots) {
          const anchor =
            root.querySelector<HTMLAnchorElement>('a.a-link-normal.s-no-outline[href*="/dp/"]') ||
            root.querySelector<HTMLAnchorElement>('h2 a[href*="/dp/"], h2 a[href*="/gp/product/"]') ||
            root.querySelector<HTMLAnchorElement>('a[href*="/dp/"], a[href*="/gp/product/"]');
          const href = anchor?.href || anchor?.getAttribute("href") || "";
          const asin = extractAsin(root, href);
          const productUrl = canonicalProductUrl(asin, href);
          const imageUrl = pickImage(root);
          const title = pickTitle(root, anchor, imageUrl);

          if (!asin || !productUrl || !imageUrl || !title) continue;
          if (seen.has(asin)) continue;

          seen.add(asin);
          items.push({
            asin,
            title,
            priceText: pickPriceText(root),
            imageUrl,
            productUrl,
            shopName: "Amazon",
            salesText: pickSalesText(root)
          });

          if (items.length >= maxItems) break;
        }

        return items;
      },
      { maxItems: limit, marketplaceOrigin: getAmazonMarketplaceOrigin() }
    );
  }

  private isUsableItem(item: ScrapedAmazonItem) {
    if (!item.asin || !item.title || !item.imageUrl || !item.productUrl) return false;
    if (!/^https:\/\/[^/]*amazon\.[^/]+\/dp\/[A-Z0-9]{10}/i.test(item.productUrl)) return false;
    return true;
  }

  private toProduct(
    item: ScrapedAmazonItem,
    amazonQuery: string,
    originalQuery: string,
    category: ProductCategory,
    index: number
  ): Product {
    return {
      productId: `amazon_${item.asin}`,
      platform: "amazon",
      category,
      title: item.title,
      price: 0,
      priceText: item.priceText || "Amazon 实时价格",
      imageUrl: item.imageUrl,
      productUrl: item.productUrl,
      isExternalSearchLanding: false,
      shopName: item.shopName,
      salesText: item.salesText,
      colors: [],
      sizes: [],
      styleTags: [originalQuery, amazonQuery],
      fitTags: [],
      reason: `来自 Amazon 搜索“${amazonQuery}”的实际商品卡片，可作为试穿参考。`,
      score: 0.62 + Math.max(0.1, 1 - index * 0.04) * 0.28,
      raw: item
    };
  }

  private toAmazonQuery(query: string, category: ProductCategory) {
    const compact = query.replace(/\s+/g, "");
    const asciiCount = Array.from(compact).filter((char) => /[a-z0-9]/i.test(char)).length;
    if (compact && asciiCount / compact.length > 0.65) return query;

    const sceneTerms = [
      query.includes("通勤") ? "office work" : "",
      query.includes("日常") ? "casual daily" : "",
      query.includes("约会") ? "soft elegant" : "",
      query.includes("旅行") ? "comfortable travel" : "",
      query.includes("聚会") ? "party" : "",
      query.includes("春夏") ? "spring summer" : "",
      query.includes("显比例") || query.includes("显腿长") ? "flattering" : "",
      query.includes("法式") ? "french style" : "",
      query.includes("温柔") || query.includes("柔和") ? "soft feminine" : "",
      query.includes("精致") ? "elegant" : "",
      query.includes("轻熟") ? "smart casual" : "",
      query.includes("松弛") ? "relaxed" : "",
      query.includes("收腰") ? "waist defining" : "",
      query.includes("垂坠") ? "draped" : "",
      ...this.colorTerms(query)
    ].filter(Boolean);

    const categoryQuery = this.categoryQuery(category, query);
    return [categoryQuery, ...sceneTerms].join(" ").replace(/\s+/g, " ").trim();
  }

  private categoryQuery(category: ProductCategory, query: string) {
    if (category === "top") {
      if (query.includes("吊带")) return "women satin camisole top";
      if (query.includes("方领")) return "women square neck top";
      if (query.includes("开衫")) return "women cropped cardigan";
      if (query.includes("衬衫")) return "women short sleeve blouse";
      if (query.includes("针织")) return "women cropped knit top";
      return "women fashion top";
    }

    if (category === "bottom") {
      if (query.includes("A字") || query.includes("半身裙")) return "women high waist a line skirt";
      if (query.includes("垂坠")) return "women draped midi skirt";
      if (query.includes("西装裤")) return "women high waist dress pants";
      if (query.includes("牛仔裤")) return "women high waist straight jeans";
      return "women high waist pants";
    }

    if (category === "dress") {
      if (query.includes("茶歇")) return "women wrap dress";
      if (query.includes("针织")) return "women knit waist dress";
      if (query.includes("收腰")) return "women waist defining dress";
      return "women date dress";
    }

    if (category === "outerwear") {
      if (query.includes("开衫")) return "women lightweight cardigan";
      return "women cropped blazer lightweight jacket";
    }

    if (category === "shoes") {
      if (query.includes("玛丽珍")) return "women low heel mary jane shoes";
      if (query.includes("乐福")) return "women loafers";
      if (query.includes("凉鞋")) return "women low heel sandals";
      if (query.includes("尖头")) return "women pointed toe low heel flats";
      return "women low heel flats loafers";
    }

    if (category === "bag") {
      if (query.includes("腋下")) return "women small shoulder hobo bag";
      if (query.includes("链条")) return "women chain crossbody bag";
      if (query.includes("方包")) return "women small square shoulder bag";
      return "women small shoulder bag minimalist";
    }

    return "women delicate necklace accessory";
  }

  private colorTerms(query: string) {
    return [
      query.includes("象牙白") || query.includes("白色") ? "ivory white" : "",
      query.includes("奶油色") || query.includes("米色") ? "cream beige" : "",
      query.includes("雾粉") || query.includes("粉色") ? "pink" : "",
      query.includes("牛仔蓝") || query.includes("蓝色") ? "blue" : "",
      query.includes("藏青") ? "navy" : "",
      query.includes("黑色") ? "black" : "",
      query.includes("棕色") ? "brown" : "",
      query.includes("灰色") ? "gray" : "",
      query.includes("银色") ? "silver" : ""
    ];
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
