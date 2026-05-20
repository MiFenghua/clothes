from __future__ import annotations

import re
from typing import Protocol
from urllib.parse import quote, urlencode
from uuid import uuid5, NAMESPACE_URL

from app.config import Settings
from app.schemas.domain import Budget, Marketplace, ProductCandidate, ProductCategory


class ProductSearchProvider(Protocol):
    async def search(
        self,
        *,
        query: str,
        marketplaces: list[Marketplace],
        budget: Budget,
        limit: int,
    ) -> list[ProductCandidate]:
        ...


class LocalDemoSearchProvider:
    """Deterministic search provider used for local development and tests."""

    async def search(
        self,
        *,
        query: str,
        marketplaces: list[Marketplace],
        budget: Budget,
        limit: int,
    ) -> list[ProductCandidate]:
        category = self._category_from_query(query)
        products: list[ProductCandidate] = []
        market_pool = marketplaces or [Marketplace.taobao, Marketplace.amazon]
        for index in range(limit):
            marketplace = market_pool[index % len(market_pool)]
            price = self._price_for(category, index, budget)
            product_id = f"{marketplace}_{uuid5(NAMESPACE_URL, query + str(index)).hex[:12]}"
            products.append(
                ProductCandidate(
                    product_id=product_id,
                    marketplace=marketplace,
                    category=category,
                    title=f"{query} 高质候选 {index + 1}",
                    price=price,
                    price_text=f"¥{price:.0f}" if marketplace != Marketplace.amazon else f"${max(price / 7, 9):.2f}",
                    image_url=self._preview_image(category, index),
                    product_url=self._detail_url(marketplace, product_id),
                    shop_name=f"{marketplace.value}精选店",
                    sizes=["S", "M", "L"],
                    colors=["ivory", "denim", "black"] if category != ProductCategory.shoes else ["black", "cream"],
                    style_tags=self._style_tags(query),
                    fit_tags=self._fit_tags(query),
                    source_reliability=0.82 if index < 8 else 0.72,
                    score=max(0.55, 0.92 - index * 0.025),
                )
            )
        return products

    def _category_from_query(self, query: str) -> ProductCategory:
        lowered = query.lower()
        checks = [
            (ProductCategory.dress, ["dress", "连衣裙", "裙"]),
            (ProductCategory.bottom, ["裤", "牛仔裤", "半身裙", "bottom", "pants"]),
            (ProductCategory.outerwear, ["外套", "西装", "jacket", "coat"]),
            (ProductCategory.shoes, ["鞋", "单鞋", "boots", "shoes"]),
            (ProductCategory.bag, ["包", "bag"]),
            (ProductCategory.accessory, ["项链", "耳环", "accessory"]),
        ]
        for category, words in checks:
            if any(word in lowered or word in query for word in words):
                return category
        return ProductCategory.top

    def _price_for(self, category: ProductCategory, index: int, budget: Budget) -> float:
        base = {
            ProductCategory.top: 159,
            ProductCategory.bottom: 229,
            ProductCategory.dress: 329,
            ProductCategory.outerwear: 399,
            ProductCategory.shoes: 259,
            ProductCategory.bag: 199,
            ProductCategory.accessory: 89,
        }[category]
        price = base + index * 17
        if budget.max and price > budget.max * 0.72:
            price = max(base * 0.85, budget.max * 0.45)
        return round(price, 2)

    def _detail_url(self, marketplace: Marketplace, product_id: str) -> str:
        if marketplace == Marketplace.amazon:
            return f"https://www.amazon.com/dp/{product_id[-10:].upper()}"
        if marketplace == Marketplace.tmall:
            return f"https://detail.tmall.com/item.htm?id={product_id}"
        if marketplace == Marketplace.taobao:
            return f"https://item.taobao.com/item.htm?id={product_id}"
        if marketplace == Marketplace.jd:
            return f"https://item.jd.com/{product_id}.html"
        if marketplace == Marketplace.pdd:
            return f"https://mobile.yangkeduo.com/goods.html?goods_id={product_id}"
        return f"owned://wardrobe/{product_id}"

    def _style_tags(self, query: str) -> list[str]:
        tags = []
        for word in ["通勤", "日常", "约会", "旅行", "轻熟", "干净", "温柔", "显比例", "质感"]:
            if word in query:
                tags.append(word)
        return tags or ["日常", "干净"]

    def _fit_tags(self, query: str) -> list[str]:
        tags = []
        for word in ["高腰", "收腰", "直筒", "短款", "显腿长", "利落"]:
            if word in query:
                tags.append(word)
        return tags or ["线条干净"]

    def _preview_image(self, category: ProductCategory, index: int) -> str:
        palette = {
            ProductCategory.top: ("#f6d7cf", "#e85d4f"),
            ProductCategory.bottom: ("#dce8f3", "#4c6f91"),
            ProductCategory.dress: ("#f8dce4", "#b84f77"),
            ProductCategory.outerwear: ("#e8e2d8", "#6e6258"),
            ProductCategory.shoes: ("#ece8e1", "#303940"),
            ProductCategory.bag: ("#e7f1ea", "#2f7668"),
            ProductCategory.accessory: ("#fff3dc", "#bb842f"),
        }[category]
        label = category.value.upper()
        svg = f"""
        <svg xmlns="http://www.w3.org/2000/svg" width="360" height="360" viewBox="0 0 360 360">
          <rect width="360" height="360" fill="{palette[0]}"/>
          <rect x="84" y="72" width="192" height="216" rx="28" fill="{palette[1]}" opacity="0.88"/>
          <circle cx="252" cy="84" r="34" fill="#fffdf9" opacity="0.42"/>
          <text x="180" y="188" text-anchor="middle" font-family="Arial" font-size="34" font-weight="700" fill="#fffdf9">{label}</text>
          <text x="180" y="230" text-anchor="middle" font-family="Arial" font-size="20" fill="#fffdf9">Candidate {index + 1}</text>
        </svg>
        """
        return f"data:image/svg+xml;charset=utf-8,{quote(svg)}"


class BrowserProductSearchProvider:
    """Playwright-backed real product search for Taobao/Tmall and Amazon detail cards."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def search(
        self,
        *,
        query: str,
        marketplaces: list[Marketplace],
        budget: Budget,
        limit: int,
    ) -> list[ProductCandidate]:
        if limit <= 0:
            return []
        products: list[ProductCandidate] = []
        target_marketplaces = marketplaces or [Marketplace.taobao, Marketplace.tmall, Marketplace.amazon]
        if Marketplace.taobao in target_marketplaces or Marketplace.tmall in target_marketplaces:
            products.extend(await self._search_taobao(query=query, budget=budget, limit=max(4, limit // 2)))
        if Marketplace.amazon in target_marketplaces:
            products.extend(await self._search_amazon(query=query, limit=max(4, limit // 2)))
        return self._dedupe(products)[:limit]

    async def _search_taobao(self, *, query: str, budget: Budget, limit: int) -> list[ProductCandidate]:
        try:
            from playwright.async_api import async_playwright
        except Exception as exc:  # pragma: no cover - depends on optional browser runtime
            raise RuntimeError("playwright is required for STYLE_BACKEND_SEARCH_PROVIDER=browser") from exc

        async with async_playwright() as playwright:
            context = await self._new_context(playwright)
            page = await context.new_page()
            try:
                await page.goto(f"https://s.taobao.com/search?q={quote(query)}", wait_until="domcontentloaded", timeout=self.settings.browser_timeout_ms)
                await page.wait_for_timeout(1800)
                for _ in range(3):
                    await page.mouse.wheel(0, 650)
                    await page.wait_for_timeout(500)
                rows = await page.evaluate(
                    """(limit) => {
                      const normalizeUrl = (url) => {
                        if (!url) return "";
                        if (url.startsWith("//")) return `https:${url}`;
                        if (url.startsWith("/")) return `https://s.taobao.com${url}`;
                        return url;
                      };
                      const pickImage = (root) => {
                        for (const img of Array.from(root.querySelectorAll("img"))) {
                          const src = img.currentSrc || img.src || img.getAttribute("data-src") || img.getAttribute("data-ks-lazyload") || "";
                          const normalized = normalizeUrl(src);
                          if (normalized && !/data:image|transparent|loading|placeholder|logo/i.test(normalized)) return normalized;
                        }
                        return "";
                      };
                      const pickPrice = (text) => {
                        const matches = Array.from(text.matchAll(/(?:¥|￥)?\\s*(\\d{1,5}(?:\\.\\d{1,2})?)/g))
                          .map((match) => Number(match[1]))
                          .filter((value) => value > 1 && value < 100000);
                        return matches[0] || 0;
                      };
                      const anchors = Array.from(document.querySelectorAll(
                        'a[href*="item.taobao.com/item.htm"], a[href*="detail.tmall.com/item.htm"], a[href*="world.taobao.com/item/"]'
                      ));
                      const seen = new Set();
                      const items = [];
                      for (const anchor of anchors) {
                        const productUrl = normalizeUrl(anchor.href || anchor.getAttribute("href") || "");
                        if (!/^https:\\/\\/(item\\.taobao\\.com\\/item\\.htm|detail\\.tmall\\.com\\/item\\.htm|world\\.taobao\\.com\\/item\\/)/i.test(productUrl)) continue;
                        const root = anchor.closest('[data-nid], [data-item-id], [class*="Card"], [class*="card"], [class*="item"], [class*="Item"]') || anchor.parentElement || anchor;
                        const imageUrl = pickImage(root);
                        const text = root.textContent || "";
                        const title = (root.querySelector("img")?.alt || anchor.textContent || text.split(/\\n|\\s{2,}/).find((line) => line.trim().length > 6) || "淘宝商品").trim().slice(0, 140);
                        const price = pickPrice(text);
                        const id = new URL(productUrl).searchParams.get("id") || productUrl;
                        if (!title || !imageUrl || !price || seen.has(id)) continue;
                        seen.add(id);
                        items.push({ title, price, imageUrl, productUrl, shopName: "", salesText: text.match(/\\d+(?:\\.\\d+)?万?\\+?人(?:付款|购买|看过)|月销\\s*\\d+(?:\\.\\d+)?万?\\+?/i)?.[0] || "" });
                        if (items.length >= limit) break;
                      }
                      return items;
                    }""",
                    limit,
                )
            finally:
                await context.close()

        category = _category_from_query(query)
        products = []
        for index, row in enumerate(rows):
            price = float(row.get("price") or 0)
            if budget.max is not None and price > budget.max * 1.5:
                continue
            marketplace = Marketplace.tmall if "tmall.com" in row["productUrl"] else Marketplace.taobao
            product_id = f"{marketplace.value}_{_stable_id(row['productUrl'])}"
            products.append(
                ProductCandidate(
                    product_id=product_id,
                    marketplace=marketplace,
                    category=category,
                    title=row["title"],
                    price=price,
                    price_text=f"¥{price:.0f}",
                    image_url=row["imageUrl"],
                    product_url=row["productUrl"],
                    shop_name=row.get("shopName") or None,
                    sizes=["S", "M", "L"],
                    colors=_color_tags(query),
                    style_tags=_style_tags(query),
                    fit_tags=_fit_tags(query),
                    source_reliability=0.88,
                    score=max(0.55, 0.94 - index * 0.035),
                    raw=dict(row),
                )
            )
        return products

    async def _search_amazon(self, *, query: str, limit: int) -> list[ProductCandidate]:
        try:
            from playwright.async_api import async_playwright
        except Exception as exc:  # pragma: no cover - depends on optional browser runtime
            raise RuntimeError("playwright is required for STYLE_BACKEND_SEARCH_PROVIDER=browser") from exc

        amazon_query = _amazon_query(query)
        base = self.settings.amazon_marketplace_base_url.rstrip("/")
        async with async_playwright() as playwright:
            context = await self._new_context(playwright, locale="en-US")
            page = await context.new_page()
            try:
                await page.goto(f"{base}/s?{urlencode({'k': amazon_query})}", wait_until="domcontentloaded", timeout=self.settings.browser_timeout_ms)
                await page.wait_for_timeout(1800)
                for _ in range(3):
                    await page.mouse.wheel(0, 650)
                    await page.wait_for_timeout(500)
                rows = await page.evaluate(
                    """({ limit, base }) => {
                      const normalizeUrl = (url) => {
                        try { return new URL(url || "", base).href; } catch { return ""; }
                      };
                      const cards = Array.from(document.querySelectorAll('[data-component-type="s-search-result"][data-asin], [data-asin][data-index]'));
                      const items = [];
                      const seen = new Set();
                      for (const root of cards) {
                        const asin = root.getAttribute("data-asin") || "";
                        const anchor = root.querySelector('a[href*="/dp/"], a[href*="/gp/product/"]');
                        const productUrl = asin ? `${base}/dp/${asin}` : normalizeUrl(anchor?.getAttribute("href") || "");
                        const image = root.querySelector("img.s-image") || root.querySelector("img");
                        const imageUrl = normalizeUrl(image?.currentSrc || image?.src || image?.getAttribute("src") || "");
                        const title = (root.querySelector("h2 span")?.textContent || image?.alt || anchor?.textContent || "Amazon product").trim().slice(0, 180);
                        const priceText = root.querySelector(".a-price .a-offscreen")?.textContent?.trim() || "Amazon 实时价格";
                        if (!asin || !title || !imageUrl || seen.has(asin) || /favicon|sprite|spinner|transparent/i.test(imageUrl)) continue;
                        seen.add(asin);
                        items.push({ asin, title, priceText, imageUrl, productUrl });
                        if (items.length >= limit) break;
                      }
                      return items;
                    }""",
                    {"limit": limit, "base": base},
                )
            finally:
                await context.close()

        category = _category_from_query(query)
        return [
            ProductCandidate(
                product_id=f"amazon_{row['asin']}",
                marketplace=Marketplace.amazon,
                category=category,
                title=row["title"],
                price=0,
                price_text=row.get("priceText") or "Amazon 实时价格",
                image_url=row["imageUrl"],
                product_url=row["productUrl"],
                shop_name="Amazon",
                sizes=["S", "M", "L"],
                colors=_color_tags(query),
                style_tags=_style_tags(query),
                fit_tags=_fit_tags(query),
                source_reliability=0.86,
                score=max(0.56, 0.92 - index * 0.035),
                raw=dict(row),
            )
            for index, row in enumerate(rows)
        ]

    async def _new_context(self, playwright, *, locale: str = "zh-CN"):
        self.settings.browser_user_data_dir.mkdir(parents=True, exist_ok=True)
        launch_args = {
            "headless": self.settings.browser_headless,
            "locale": locale,
            "viewport": {"width": 1440, "height": 1100},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "args": ["--disable-blink-features=AutomationControlled", "--no-first-run", "--disable-dev-shm-usage"],
        }
        if self.settings.browser_chrome_path:
            launch_args["executable_path"] = self.settings.browser_chrome_path
        return await playwright.chromium.launch_persistent_context(str(self.settings.browser_user_data_dir), **launch_args)

    def _dedupe(self, products: list[ProductCandidate]) -> list[ProductCandidate]:
        seen: set[str] = set()
        deduped = []
        for product in sorted(products, key=lambda item: item.score, reverse=True):
            key = product.product_id or product.product_url
            if key in seen:
                continue
            seen.add(key)
            deduped.append(product)
        return deduped


def _category_from_query(query: str) -> ProductCategory:
    checks = [
        (ProductCategory.dress, ["dress", "连衣裙", "茶歇裙", "针织裙"]),
        (ProductCategory.bottom, ["裤", "牛仔裤", "西装裤", "半身裙", "skirt", "pants", "jeans"]),
        (ProductCategory.outerwear, ["外套", "西装", "开衫", "jacket", "coat", "cardigan"]),
        (ProductCategory.shoes, ["鞋", "单鞋", "乐福", "boots", "shoes", "flats"]),
        (ProductCategory.bag, ["包", "托特", "腋下包", "bag"]),
        (ProductCategory.accessory, ["项链", "耳环", "accessory", "necklace"]),
    ]
    lowered = query.lower()
    for category, words in checks:
        if any(word in query or word in lowered for word in words):
            return category
    return ProductCategory.top


def _style_tags(query: str) -> list[str]:
    return [word for word in ["通勤", "日常", "约会", "旅行", "轻熟", "干净", "温柔", "显比例", "质感", "精致"] if word in query] or ["日常", "干净"]


def _fit_tags(query: str) -> list[str]:
    return [word for word in ["高腰", "收腰", "直筒", "短款", "显腿长", "利落", "垂感"] if word in query] or ["线条干净"]


def _color_tags(query: str) -> list[str]:
    tags = []
    mapping = {
        "白": "ivory",
        "米": "cream",
        "粉": "misty pink",
        "蓝": "denim",
        "黑": "black",
        "灰": "gray",
        "棕": "brown",
    }
    for source, target in mapping.items():
        if source in query:
            tags.append(target)
    return tags or ["ivory", "denim", "black"]


def _stable_id(value: str) -> str:
    return uuid5(NAMESPACE_URL, value).hex[:12]


def _amazon_query(query: str) -> str:
    if re.search(r"[a-z]", query, re.I):
        return query
    category = _category_from_query(query)
    category_terms = {
        ProductCategory.top: "women fashion top",
        ProductCategory.bottom: "women high waist pants skirt",
        ProductCategory.dress: "women waist defining dress",
        ProductCategory.outerwear: "women lightweight jacket cardigan",
        ProductCategory.shoes: "women low heel flats loafers",
        ProductCategory.bag: "women small shoulder bag",
        ProductCategory.accessory: "women delicate necklace accessory",
    }[category]
    scene_terms = [
        "office work" if "通勤" in query else "",
        "casual daily" if "日常" in query else "",
        "soft elegant" if "约会" in query else "",
        "comfortable travel" if "旅行" in query else "",
        "flattering" if "显比例" in query or "显腿长" in query else "",
        "elegant" if "精致" in query or "质感" in query else "",
    ]
    return " ".join([category_terms, *[term for term in scene_terms if term]]).strip()
