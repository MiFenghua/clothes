from __future__ import annotations

from collections import Counter
from collections.abc import Callable

from app.agents.state import StyleGraphState
from app.providers.query_planner import LocalSearchQueryPlanner, SearchQueryPlanner
from app.providers.search import ProductSearchProvider
from app.providers.tracing import TraceRecorder
from app.schemas.domain import ProductCandidate


class ProductScoutAgent:
    node_name = "ProductScoutAgent"

    def __init__(
        self,
        tracer: TraceRecorder,
        search_provider: ProductSearchProvider,
        query_planner: SearchQueryPlanner | None = None,
        wardrobe_products: Callable[[list[str]], list[ProductCandidate]] | None = None,
    ) -> None:
        self.tracer = tracer
        self.search_provider = search_provider
        self.query_planner = query_planner or LocalSearchQueryPlanner()
        self.wardrobe_products = wardrobe_products

    async def run(self, state: StyleGraphState) -> StyleGraphState:
        if state.constraints is None or state.profile is None:
            raise ValueError("Profile and preference constraints are required before product scouting")

        queries = await self.query_planner.build_queries(
            request=state.request,
            profile=state.profile,
            constraints=state.constraints,
        )
        products: list[ProductCandidate] = []
        query_summaries = []
        for query in queries:
            results = await self._search(query, state)
            products.extend(results)
            query_summaries.append(self._query_summary(query, results))

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
                "query_source": self.query_planner.source,
                "search_source": getattr(self.search_provider, "source_id", type(self.search_provider).__name__),
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

    async def _search(self, query: str, state: StyleGraphState) -> list[ProductCandidate]:
        if state.constraints is None:
            raise ValueError("Preference constraints are required before product search")
        return await self.search_provider.search(
            query=query,
            marketplaces=state.constraints.marketplaces,
            budget=state.constraints.budget,
            limit=20,
        )

    def _query_summary(self, query: str, products: list[ProductCandidate]) -> dict:
        categories = Counter(product.category.value for product in products)
        marketplaces = Counter(product.marketplace.value for product in products)
        return {
            "query": query,
            "count": len(products),
            "category_counts": dict(categories),
            "marketplace_counts": dict(marketplaces),
        }
