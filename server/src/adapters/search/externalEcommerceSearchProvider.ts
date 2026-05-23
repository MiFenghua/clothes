import crypto from "node:crypto";
import { config } from "../../config.js";
import type { Budget, OutfitStrategy, Product, ProductCategory } from "../../domain/types.js";
import type { SearchProvider } from "./searchProvider.js";
import { buildAmazonSearchUrl } from "./amazonSearchUrl.js";
import { inferCategoryFromQuery } from "./demoSearchProvider.js";

type EcommercePlatform = "amazon" | "taobao" | "jd" | "pdd";

interface PlatformConfig {
  platform: EcommercePlatform;
  label: string;
  buildSearchUrl: (query: string) => string;
  imageUrl: string;
}

const platforms: Record<EcommercePlatform, PlatformConfig> = {
  amazon: {
    platform: "amazon",
    label: "Amazon",
    buildSearchUrl: buildAmazonSearchUrl,
    imageUrl: "https://www.amazon.com/favicon.ico"
  },
  taobao: {
    platform: "taobao",
    label: "淘宝",
    buildSearchUrl: (query) => `https://s.taobao.com/search?q=${encodeURIComponent(query)}`,
    imageUrl: "https://img.alicdn.com/imgextra/i4/O1CN01PiwQF81R0Pr5k8Yck_!!6000000002098-2-tps-192-192.png"
  },
  jd: {
    platform: "jd",
    label: "京东",
    buildSearchUrl: (query) => `https://search.jd.com/Search?keyword=${encodeURIComponent(query)}&enc=utf-8`,
    imageUrl: "https://img10.360buyimg.com/img/jfs/t1/178680/10/17304/1214/60d0358eE354f28f0/83be6644c02f0b37.png"
  },
  pdd: {
    platform: "pdd",
    label: "拼多多",
    buildSearchUrl: (query) => `https://mobile.yangkeduo.com/search_result.html?search_key=${encodeURIComponent(query)}`,
    imageUrl: "https://funimg.pddpic.com/common/2020-07-22/2b40de6d-5b68-4c0f-a245-41ea5122019b.png"
  }
};

export class ExternalEcommerceSearchProvider implements SearchProvider {
  private readonly activePlatforms: PlatformConfig[];

  constructor(platformNames = config.ecommercePlatforms) {
    this.activePlatforms = platformNames
      .map((name) => platforms[name as EcommercePlatform])
      .filter((platform): platform is PlatformConfig => Boolean(platform));
  }

  async search({ strategy, budget, limitPerQuery }: { strategy: OutfitStrategy; budget: Budget; limitPerQuery: number }) {
    const products: Product[] = [];
    const queries = strategy.searchQueries.slice(0, Math.max(1, Math.ceil(limitPerQuery / 3)));

    for (const query of queries) {
      for (const platform of this.activePlatforms) {
        products.push(await this.buildProductCard(platform, query, strategy, budget, products.length));
      }
    }

    return products.sort((a, b) => (b.score ?? 0) - (a.score ?? 0)).slice(0, limitPerQuery);
  }

  private async buildProductCard(
    platform: PlatformConfig,
    query: string,
    strategy: OutfitStrategy,
    budget: Budget,
    index: number
  ): Promise<Product> {
    const url = platform.buildSearchUrl(query);
    const metadata = await this.fetchMetadata(url);
    const category = inferCategoryFromQuery(query);
    const priceText = budget.max ? `进入${platform.label}查看价格，建议总预算 ¥${budget.min ?? 0}-${budget.max}` : `进入${platform.label}查看实时价格`;
    const productId = `${platform.platform}_${crypto.createHash("sha1").update(query).digest("hex").slice(0, 12)}`;

    return {
      productId,
      platform: platform.platform,
      category,
      title: this.isUsefulTitle(metadata.title) ? metadata.title : `${platform.label}搜索：${query}`,
      price: 0,
      priceText,
      imageUrl: metadata.imageUrl || platform.imageUrl,
      productUrl: url,
      isExternalSearchLanding: true,
      shopName: platform.label,
      salesText: "外部电商实时搜索入口",
      colors: strategy.colorDirection,
      sizes: [],
      styleTags: strategy.styleDirection,
      fitTags: strategy.fitDirection,
      reason: `跳转到${platform.label}查看“${query}”的实时商品结果。`,
      score: this.score(category, strategy.requiredCategories, index)
    };
  }

  private async fetchMetadata(url: string) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 4500);
    try {
      const response = await fetch(url, {
        redirect: "follow",
        signal: controller.signal,
        headers: {
          "user-agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
          accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
          "accept-language": "zh-CN,zh;q=0.9,en;q=0.7"
        }
      });
      if (!response.ok) return {};
      const html = await response.text();
      return {
        title: this.extractTitle(html),
        imageUrl: this.extractMeta(html, "og:image")
      };
    } catch {
      return {};
    } finally {
      clearTimeout(timeout);
    }
  }

  private extractTitle(html: string) {
    const ogTitle = this.extractMeta(html, "og:title");
    if (ogTitle) return ogTitle;
    const title = /<title[^>]*>([^<]+)<\/title>/i.exec(html)?.[1];
    return title ? this.decodeHtml(title).trim() : undefined;
  }

  private extractMeta(html: string, property: string) {
    const pattern = new RegExp(`<meta[^>]+(?:property|name)=["']${property}["'][^>]+content=["']([^"']+)["'][^>]*>`, "i");
    const value = pattern.exec(html)?.[1];
    return value ? this.decodeHtml(value).trim() : undefined;
  }

  private decodeHtml(value: string) {
    return value
      .replace(/&amp;/g, "&")
      .replace(/&lt;/g, "<")
      .replace(/&gt;/g, ">")
      .replace(/&quot;/g, '"')
      .replace(/&#39;/g, "'");
  }

  private isUsefulTitle(title: string | undefined): title is string {
    if (!title) return false;
    return !["淘宝搜索", "京东验证", "JD.COM", "轻松购物", "拼多多"].some((blocked) => title.includes(blocked));
  }

  private score(category: ProductCategory, requiredCategories: ProductCategory[], index: number) {
    const categoryFit = requiredCategories.includes(category) ? 0.55 : 0.2;
    const platformDiversity = Math.max(0.2, 1 - index * 0.035);
    return categoryFit + platformDiversity * 0.25 + 0.2;
  }
}
