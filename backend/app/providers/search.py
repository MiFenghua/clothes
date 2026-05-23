from __future__ import annotations

import asyncio
import hashlib
import hmac
import html
import json
import re
import time
from typing import Any, Protocol
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from uuid import NAMESPACE_URL, uuid5

from app.config import Settings
from app.schemas.domain import Budget, Marketplace, ProductCandidate, ProductCategory


class ProductSearchProvider(Protocol):
    source_id: str

    async def search(
        self,
        *,
        query: str,
        marketplaces: list[Marketplace],
        budget: Budget,
        limit: int,
    ) -> list[ProductCandidate]:
        ...


class CompositeProductSearchProvider:
    """Aggregates product sources while keeping each source independently replaceable."""

    source_id = "composite"

    def __init__(self, providers: list[ProductSearchProvider]) -> None:
        if not providers:
            raise ValueError("At least one product search provider is required")
        self.providers = providers

    async def search(
        self,
        *,
        query: str,
        marketplaces: list[Marketplace],
        budget: Budget,
        limit: int,
    ) -> list[ProductCandidate]:
        products: list[ProductCandidate] = []
        per_source_limit = max(limit, 1)
        for provider in self.providers:
            products.extend(
                await provider.search(
                    query=query,
                    marketplaces=marketplaces,
                    budget=budget,
                    limit=per_source_limit,
                )
            )
        return _dedupe(products)[:limit]


class LocalDemoSearchProvider:
    """Deterministic search provider used only for local development and tests."""

    source_id = "local_demo"

    async def search(
        self,
        *,
        query: str,
        marketplaces: list[Marketplace],
        budget: Budget,
        limit: int,
    ) -> list[ProductCandidate]:
        category = _category_from_query(query)
        products: list[ProductCandidate] = []
        market_pool = marketplaces or [Marketplace.taobao]
        for index in range(limit):
            marketplace = market_pool[index % len(market_pool)]
            price = _price_for(category, index, budget)
            product_id = f"{marketplace}_{uuid5(NAMESPACE_URL, query + str(index)).hex[:12]}"
            products.append(
                ProductCandidate(
                    product_id=product_id,
                    marketplace=marketplace,
                    source_provider=self.source_id,
                    category=category,
                    title=f"{query} quality candidate {index + 1}",
                    price=price,
                    price_text=f"¥{price:.0f}",
                    image_url=_preview_image(category, index),
                    product_url=_detail_url(marketplace, product_id),
                    shop_name=f"{marketplace.value} demo shop",
                    sizes=["S", "M", "L"],
                    colors=["ivory", "denim", "black"] if category != ProductCategory.shoes else ["black", "cream"],
                    style_tags=_style_tags(query),
                    fit_tags=_fit_tags(query),
                    source_reliability=0.82 if index < 8 else 0.72,
                    score=max(0.55, 0.92 - index * 0.025),
                )
            )
        return products


class TaobaoUnionProductSearchProvider:
    """Taobao Alliance/淘宝客 material search provider.

    Uses the official TOP API method `taobao.tbk.dg.material.optional.upgrade`.
    Future ecommerce sources should implement ProductSearchProvider and be registered
    in the container without changing product scouting or outfit composition.
    """

    source_id = "taobao_union"

    def __init__(self, settings: Settings) -> None:
        missing = [
            name
            for name, value in {
                "STYLE_BACKEND_TAOBAO_UNION_APP_KEY": settings.taobao_union_app_key,
                "STYLE_BACKEND_TAOBAO_UNION_APP_SECRET": settings.taobao_union_app_secret,
                "STYLE_BACKEND_TAOBAO_UNION_ADZONE_ID": settings.taobao_union_adzone_id,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(f"Taobao Union search is not configured: {', '.join(missing)}")
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
        if marketplaces and not ({Marketplace.taobao, Marketplace.tmall} & set(marketplaces)):
            return []

        payload = await asyncio.to_thread(self._request, query, budget, limit)
        rows = _extract_taobao_items(payload)
        products = [
            product
            for index, row in enumerate(rows)
            if (product := self._to_product(row, query=query, budget=budget, index=index)) is not None
        ]
        return _dedupe(products)[:limit]

    def _request(self, query: str, budget: Budget, limit: int) -> dict[str, Any]:
        params = self._signed_params(query=query, budget=budget, limit=limit)
        data = urlencode(params).encode("utf-8")
        request = Request(
            self.settings.taobao_union_endpoint,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
            method="POST",
        )
        with urlopen(request, timeout=self.settings.taobao_union_timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def _signed_params(self, *, query: str, budget: Budget, limit: int) -> dict[str, str]:
        params: dict[str, str] = {
            "method": self.settings.taobao_union_method,
            "app_key": self.settings.taobao_union_app_key or "",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "format": "json",
            "v": "2.0",
            "sign_method": self.settings.taobao_union_sign_method,
            "adzone_id": str(self.settings.taobao_union_adzone_id),
            "q": query,
            "page_no": "1",
            "page_size": str(max(1, min(limit, 100))),
            "platform": "1",
            "has_coupon": "true",
            "need_free_shipment": "true",
            "need_prepay": "true",
            "material_id": str(self.settings.taobao_union_material_id),
        }
        if self.settings.taobao_union_site_id:
            params["site_id"] = str(self.settings.taobao_union_site_id)
        if budget.min is not None:
            params["start_price"] = str(int(budget.min))
        if budget.max is not None:
            params["end_price"] = str(int(budget.max))
        params["sign"] = self._sign(params)
        return params

    def _sign(self, params: dict[str, str]) -> str:
        app_secret = (self.settings.taobao_union_app_secret or "").encode("utf-8")
        sign_base = "".join(f"{key}{value}" for key, value in sorted(params.items()) if key != "sign")
        if self.settings.taobao_union_sign_method.lower() == "hmac":
            return hmac.new(app_secret, sign_base.encode("utf-8"), hashlib.md5).hexdigest().upper()
        raw = app_secret + sign_base.encode("utf-8") + app_secret
        return hashlib.md5(raw).hexdigest().upper()

    def _to_product(
        self,
        row: dict[str, Any],
        *,
        query: str,
        budget: Budget,
        index: int,
    ) -> ProductCandidate | None:
        item_id = _first_text(row, "item_id", "num_iid", "itemId")
        title = html.unescape(_first_text(row, "title", "short_title", "item_description") or "").strip()
        image_url = _normalize_url(_first_text(row, "pict_url", "pic_url", "white_image", "pictUrl"))
        product_url = _normalize_url(
            _first_text(row, "coupon_click_url", "coupon_share_url", "click_url", "url", "item_url")
        )
        detail_url = _normalize_url(_first_text(row, "item_url", "item_url_h5"))
        if not product_url and item_id:
            product_url = f"https://item.taobao.com/item.htm?id={item_id}"
        if not title or not image_url or not product_url:
            return None

        price = _price_from_row(row)
        if budget.max is not None and price > budget.max * 1.5:
            return None
        marketplace = _taobao_marketplace(row, product_url, detail_url)
        stable_key = item_id or product_url
        source_reliability = 0.92 if detail_url or item_id else 0.86
        return ProductCandidate(
            product_id=f"tbk_{uuid5(NAMESPACE_URL, stable_key).hex[:12]}",
            marketplace=marketplace,
            source_provider=self.source_id,
            category=_category_from_query(query),
            title=title[:180],
            price=price,
            price_text=f"¥{price:.2f}" if price else _first_text(row, "zk_final_price", "reserve_price"),
            image_url=image_url,
            product_url=product_url,
            shop_name=_first_text(row, "shop_title", "nick", "seller_nick") or None,
            sizes=["S", "M", "L"],
            colors=_color_tags(query),
            style_tags=_style_tags(query),
            fit_tags=_fit_tags(query),
            source_reliability=source_reliability,
            score=_taobao_score(row, source_reliability, index),
            raw={
                "source_provider": self.source_id,
                "item_id": item_id,
                "detail_url": detail_url,
                "promotion_url": product_url,
                "commission_rate": _first_text(row, "commission_rate"),
                "coupon_amount": _first_text(row, "coupon_amount"),
                "volume": _first_text(row, "volume", "biz_30day"),
            },
        )


def _extract_taobao_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    error = payload.get("error_response")
    if isinstance(error, dict):
        message = error.get("sub_msg") or error.get("msg") or "Taobao Union API error"
        raise RuntimeError(str(message))

    candidate_roots: list[Any] = [payload]
    candidate_roots.extend(value for key, value in payload.items() if key.endswith("_response"))
    for root in candidate_roots:
        if not isinstance(root, dict):
            continue
        for key in ("result_list", "results", "result", "data"):
            items = _items_from_container(root.get(key))
            if items:
                return items
    return []


def _items_from_container(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if not isinstance(value, dict):
        return []
    for key in ("map_data", "n_tbk_item", "items", "item"):
        nested = value.get(key)
        if isinstance(nested, list):
            return [item for item in nested if isinstance(item, dict)]
        if isinstance(nested, dict):
            return [nested]
    return []


def _dedupe(products: list[ProductCandidate]) -> list[ProductCandidate]:
    seen: set[str] = set()
    deduped: list[ProductCandidate] = []
    for product in sorted(products, key=lambda item: item.score, reverse=True):
        key = product.raw.get("item_id") or product.product_id or product.product_url
        if key in seen:
            continue
        seen.add(str(key))
        deduped.append(product)
    return deduped


def _first_text(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _normalize_url(value: str) -> str:
    if not value:
        return ""
    value = html.unescape(value.strip())
    if value.startswith("//"):
        return f"https:{value}"
    if value.startswith(("http://", "https://")):
        return value
    if re.match(r"^[\w.-]+\.[a-z]{2,}/", value, re.I):
        return f"https://{value}"
    return value


def _price_from_row(row: dict[str, Any]) -> float:
    for key in ("final_price", "actual_price", "zk_final_price", "reserve_price"):
        value = _first_text(row, key)
        if value:
            try:
                return round(float(value), 2)
            except ValueError:
                continue
    return 0.0


def _taobao_marketplace(row: dict[str, Any], product_url: str, detail_url: str) -> Marketplace:
    user_type = _first_text(row, "user_type", "mall").lower()
    blob = f"{product_url} {detail_url}".lower()
    if "tmall.com" in blob or user_type in {"1", "tmall", "true"}:
        return Marketplace.tmall
    return Marketplace.taobao


def _taobao_score(row: dict[str, Any], source_reliability: float, index: int) -> float:
    coupon_bonus = 0.025 if _first_text(row, "coupon_amount", "coupon_info") else 0
    sales_text = _first_text(row, "volume", "biz_30day", "sales")
    sales_bonus = 0.02 if sales_text and sales_text != "0" else 0
    return max(0.58, min(0.96, source_reliability + coupon_bonus + sales_bonus - index * 0.018))


def _category_from_query(query: str) -> ProductCategory:
    lowered = query.lower()
    checks = [
        (ProductCategory.dress, ["dress", "连衣裙", "茶歇裙", "针织裙", "one piece"]),
        (ProductCategory.bottom, ["pants", "trousers", "jeans", "skirt", "裤", "牛仔裤", "西装裤", "半身裙"]),
        (ProductCategory.outerwear, ["jacket", "coat", "cardigan", "blazer", "外套", "西装", "开衫"]),
        (ProductCategory.shoes, ["shoe", "shoes", "boots", "flats", "loafers", "heel", "鞋", "单鞋", "乐福"]),
        (ProductCategory.bag, ["bag", "tote", "crossbody", "包", "托特", "腋下包"]),
        (ProductCategory.accessory, ["accessory", "necklace", "earring", "项链", "耳环", "配饰"]),
        (ProductCategory.top, ["top", "shirt", "blouse", "tee", "上衣", "衬衫", "针织", "短款"]),
    ]
    for category, words in checks:
        if any(word in lowered or word in query for word in words):
            return category
    return ProductCategory.top


def _style_tags(query: str) -> list[str]:
    tags = []
    mapping = {
        "commute": "通勤",
        "office": "通勤",
        "daily": "日常",
        "casual": "休闲",
        "date": "约会",
        "travel": "旅行",
        "party": "聚会",
        "clean": "干净",
        "minimal": "简约",
        "elegant": "轻熟",
        "soft": "温柔",
        "cute": "可爱",
        "preppy": "卡通",
        "comfortable": "舒适",
    }
    for word, tag in mapping.items():
        if word in query.lower() and tag not in tags:
            tags.append(tag)
    for tag in ["通勤", "日常", "约会", "旅行", "轻熟", "干净", "温柔", "显比例", "质感", "精致", "可爱", "休闲", "舒适", "卡通", "宽松"]:
        if tag in query and tag not in tags:
            tags.append(tag)
    return tags or ["日常", "干净"]


def _fit_tags(query: str) -> list[str]:
    tags = []
    mapping = {
        "high waist": "高腰线",
        "waist": "收腰",
        "cropped": "短款",
        "straight": "直筒",
        "loose": "宽松",
        "comfortable": "舒适",
    }
    for word, tag in mapping.items():
        if word in query.lower() and tag not in tags:
            tags.append(tag)
    for tag in ["高腰", "高腰线", "收腰", "直筒", "短款", "显腿长", "利落", "垂感", "宽松", "舒适"]:
        if tag in query and tag not in tags:
            tags.append(tag)
    return tags or ["线条干净"]


def _color_tags(query: str) -> list[str]:
    tags = []
    mapping = {
        "ivory": "ivory",
        "cream": "cream",
        "pink": "misty pink",
        "denim": "denim",
        "black": "black",
        "gray": "gray",
        "brown": "brown",
        "白": "ivory",
        "米": "cream",
        "粉": "misty pink",
        "蓝": "denim",
        "黑": "black",
        "灰": "gray",
        "棕": "brown",
    }
    for source, target in mapping.items():
        if source in query.lower() or source in query:
            tags.append(target)
    return tags or ["ivory", "denim", "black"]


def _price_for(category: ProductCategory, index: int, budget: Budget) -> float:
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


def _detail_url(marketplace: Marketplace, product_id: str) -> str:
    if marketplace == Marketplace.tmall:
        return f"https://detail.tmall.com/item.htm?id={product_id}"
    if marketplace == Marketplace.jd:
        return f"https://item.jd.com/{product_id}.html"
    if marketplace == Marketplace.pdd:
        return f"https://mobile.yangkeduo.com/goods.html?goods_id={product_id}"
    if marketplace == Marketplace.amazon:
        return f"https://www.amazon.com/dp/{product_id[-10:].upper()}"
    if marketplace == Marketplace.owned:
        return f"owned://wardrobe/{product_id}"
    return f"https://item.taobao.com/item.htm?id={product_id}"


def _preview_image(category: ProductCategory, index: int) -> str:
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
