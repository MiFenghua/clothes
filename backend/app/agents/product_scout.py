from __future__ import annotations

from collections import Counter
from collections.abc import Callable

from app.agents.state import StyleGraphState
from app.providers.search import ProductSearchProvider
from app.providers.tracing import TraceRecorder
from app.schemas.domain import ProductCandidate, ProductCategory, Scene


class ProductScoutAgent:
    node_name = "ProductScoutAgent"

    def __init__(
        self,
        tracer: TraceRecorder,
        search_provider: ProductSearchProvider,
        wardrobe_products: Callable[[list[str]], list[ProductCandidate]] | None = None,
    ) -> None:
        self.tracer = tracer
        self.search_provider = search_provider
        self.wardrobe_products = wardrobe_products

    async def run(self, state: StyleGraphState) -> StyleGraphState:
        if state.constraints is None:
            raise ValueError("Preference constraints are required before product scouting")
        queries = self._build_queries(state)
        products = []
        query_summaries = []
        for query in queries:
            results = await self.search_provider.search(
                query=query,
                marketplaces=state.constraints.marketplaces,
                budget=state.constraints.budget,
                limit=20,
            )
            products.extend(results)
            categories = Counter(product.category.value for product in results)
            marketplaces = Counter(product.marketplace.value for product in results)
            query_summaries.append(
                {
                    "query": query,
                    "count": len(results),
                    "category_counts": dict(categories),
                    "marketplace_counts": dict(marketplaces),
                }
            )
        owned_products = self._wardrobe_products(state.constraints.wardrobe_item_ids)
        products.extend(owned_products)
        category_counts = Counter(product.category.value for product in products)
        marketplace_counts = Counter(product.marketplace.value for product in products)
        self.tracer.record(
            state.task_id,
            self.node_name,
            "products_scouted",
            {
                "queries": queries,
                "query_summaries": query_summaries,
                "product_count": len(products),
                "owned_product_count": len(owned_products),
                "category_counts": dict(category_counts),
                "marketplace_counts": dict(marketplace_counts),
            },
        )
        return state.model_copy(update={"search_queries": queries, "raw_products": products})

    def _wardrobe_products(self, item_ids: list[str]) -> list[ProductCandidate]:
        if not item_ids or self.wardrobe_products is None:
            return []
        return self.wardrobe_products(item_ids)

    def _build_queries(self, state: StyleGraphState) -> list[str]:
        assert state.constraints is not None
        style = " ".join(state.constraints.positive_style_terms[:3])
        fit = " ".join(state.constraints.required_fit_terms[:2])
        palette = " ".join(state.constraints.palette[:2])
        scene_words = {
            Scene.daily: ["短款上衣 女 日常", "高腰直筒裤 女 日常", "低跟单鞋 女 百搭", "小包 女 简约"],
            Scene.commute: ["衬衫 女 通勤 利落", "高腰西装裤 女 通勤", "薄外套 女 通勤", "低跟单鞋 女"],
            Scene.date: ["收腰连衣裙 女 约会", "浅口低跟单鞋 女 温柔", "小方包 女 精致"],
            Scene.travel: ["上镜上衣 女 旅行", "高腰休闲裤 女 旅行", "舒适平底鞋 女", "轻便斜挎包 女"],
            Scene.party: ["设计感上衣 女 聚会", "高腰半身裙 女 聚会", "低跟单鞋 女 精致", "项链 女 精致"],
        }[state.constraints.scene]
        queries = [f"{query} {style} {fit} {palette}".strip() for query in scene_words]
        if not any(self._category_hint(query) == ProductCategory.shoes for query in queries):
            queries.append(f"低跟单鞋 女 {style} 百搭")
        return queries

    def _category_hint(self, query: str) -> ProductCategory:
        if "鞋" in query:
            return ProductCategory.shoes
        if "裤" in query or "裙" in query:
            return ProductCategory.bottom
        return ProductCategory.top
