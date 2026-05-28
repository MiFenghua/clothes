from __future__ import annotations

import unittest

from app.config import Settings
from app.providers.search import (
    CompositeProductSearchProvider,
    TAOBAO_CATEGORY_IDS,
    LocalDemoSearchProvider,
    TaobaoUnionProductSearchProvider,
)
from app.schemas.domain import Budget, Marketplace, ProductCategory


def taobao_settings() -> Settings:
    return Settings(
        taobao_union_app_key="app-key",
        taobao_union_app_secret="app-secret",
        taobao_union_adzone_id="123456",
        taobao_union_site_id="7890",
        taobao_union_material_id=80309,
    )


class FakeTaobaoUnionProductSearchProvider(TaobaoUnionProductSearchProvider):
    def __init__(self) -> None:
        super().__init__(taobao_settings())
        self.last_request: tuple[str, ProductCategory, Budget, int] | None = None

    def _request(self, query: str, category: ProductCategory, budget: Budget, limit: int):
        self.last_request = (query, category, budget, limit)
        return {
            "tbk_dg_material_optional_upgrade_response": {
                "result_list": {
                    "map_data": [
                        {
                            "item_id": "612345678901",
                            "title": "model selected high waist pants",
                            "pict_url": "//img.alicdn.com/bao/uploaded/item.jpg",
                            "coupon_share_url": "//uland.taobao.com/coupon/edetail?e=abc",
                            "item_url": "https://detail.tmall.com/item.htm?id=612345678901",
                            "zk_final_price": "199.00",
                            "shop_title": "Tmall Test Store",
                            "user_type": "1",
                            "coupon_amount": "20",
                            "volume": "3000",
                            "commission_rate": "1200",
                        }
                    ]
                }
            }
        }


class TaobaoUnionProductSearchProviderTests(unittest.IsolatedAsyncioTestCase):
    def test_taobao_union_category_id_table_matches_business_rule(self) -> None:
        self.assertEqual(
            TAOBAO_CATEGORY_IDS,
            {
                "women_clothing": "16",
                "men_clothing": "30",
                "underwear_homewear": "1625",
                "women_shoes": "50006843",
                "men_shoes": "50011740",
                "sports_casual_clothing": "50010404",
                "kids_parent_child": "50008165",
                "bags_luggage": "50006842",
                "fashion_jewelry": "50013864",
                "watch": "50468001",
            },
        )

    async def test_taobao_union_maps_material_rows_to_product_candidates(self) -> None:
        provider = FakeTaobaoUnionProductSearchProvider()

        products = await provider.search(
            query="model selected high waist pants",
            category=ProductCategory.bottom,
            colors=["denim"],
            style_tags=["clean"],
            fit_tags=["high waist"],
            marketplaces=[Marketplace.taobao, Marketplace.tmall],
            budget=Budget(min=100, max=500),
            limit=6,
        )

        self.assertEqual(len(products), 1)
        product = products[0]
        self.assertEqual(product.source_provider, "taobao_union")
        self.assertEqual(product.marketplace, Marketplace.tmall)
        self.assertEqual(product.category, ProductCategory.bottom)
        self.assertEqual(product.colors, ["denim"])
        self.assertEqual(product.style_tags, ["clean"])
        self.assertEqual(product.fit_tags, ["high waist"])
        self.assertEqual(product.price, 199.0)
        self.assertTrue(product.image_url.startswith("https://img.alicdn.com/"))
        self.assertTrue(product.product_url.startswith("https://uland.taobao.com/"))
        self.assertEqual(product.raw["item_id"], "612345678901")

    async def test_taobao_union_maps_upgrade_nested_material_rows(self) -> None:
        class NestedUpgradeProvider(FakeTaobaoUnionProductSearchProvider):
            def _request(self, query: str, category: ProductCategory, budget: Budget, limit: int):
                return {
                    "tbk_dg_material_optional_upgrade_response": {
                        "result_list": {
                            "map_data": [
                                {
                                    "item_id": "712345678901",
                                    "item_basic_info": {
                                        "title": "Office cotton shirt women",
                                        "pict_url": "//img.alicdn.com/bao/uploaded/nested.jpg",
                                        "item_url": "https://detail.tmall.com/item.htm?id=712345678901",
                                        "shop_title": "Nested Tmall Store",
                                        "user_type": "1",
                                    },
                                    "price_promotion_info": {
                                        "zk_final_price": "188.50",
                                        "final_promotion_price": "168.50",
                                        "coupon_amount": "20",
                                    },
                                    "publish_info": {
                                        "click_url": "//s.click.taobao.com/nestedabc",
                                    },
                                    "scope_info": {
                                        "commission_rate": "1200",
                                    },
                                }
                            ]
                        }
                    }
                }

        products = await NestedUpgradeProvider().search(
            query="model selected office shirt",
            category=ProductCategory.top,
            colors=["white"],
            style_tags=["office"],
            fit_tags=["regular"],
            marketplaces=[Marketplace.taobao, Marketplace.tmall],
            budget=Budget(min=100, max=500),
            limit=6,
        )

        self.assertEqual(len(products), 1)
        product = products[0]
        self.assertEqual(product.title, "Office cotton shirt women")
        self.assertEqual(product.category, ProductCategory.top)
        self.assertEqual(product.marketplace, Marketplace.tmall)
        self.assertEqual(product.price, 168.5)
        self.assertTrue(product.image_url.startswith("https://img.alicdn.com/"))
        self.assertTrue(product.product_url.startswith("https://s.click.taobao.com/"))
        self.assertEqual(product.raw["detail_url"], "https://detail.tmall.com/item.htm?id=712345678901")
        self.assertEqual(product.raw["coupon_amount"], "20")

    async def test_taobao_union_filters_rows_with_mismatched_taobao_categories(self) -> None:
        class MixedCategoryProvider(FakeTaobaoUnionProductSearchProvider):
            def _request(self, query: str, category: ProductCategory, budget: Budget, limit: int):
                return {
                    "tbk_dg_material_optional_upgrade_response": {
                        "result_list": {
                            "map_data": [
                                {
                                    "item_id": "812345678901",
                                    "item_basic_info": {
                                        "title": "household paper towel tissue bulk pack",
                                        "category_id": "50022529",
                                        "category_name": "household paper",
                                        "level_one_category_id": "50016349",
                                        "level_one_category_name": "home goods",
                                        "pict_url": "//img.alicdn.com/bao/uploaded/paper.jpg",
                                        "shop_title": "Paper Store",
                                    },
                                    "price_promotion_info": {"final_promotion_price": "9.90"},
                                    "publish_info": {"click_url": "//s.click.taobao.com/paper"},
                                },
                                {
                                    "item_id": "912345678901",
                                    "item_basic_info": {
                                        "title": "white office cotton shirt women",
                                        "category_id": "162104",
                                        "category_name": "shirt",
                                        "level_one_category_id": "16",
                                        "level_one_category_name": "women clothing",
                                        "pict_url": "//img.alicdn.com/bao/uploaded/shirt.jpg",
                                        "shop_title": "Shirt Store",
                                    },
                                    "price_promotion_info": {"final_promotion_price": "129.00"},
                                    "publish_info": {"click_url": "//s.click.taobao.com/shirt"},
                                }
                            ]
                        }
                    }
                }

        products = await MixedCategoryProvider().search(
            query="white office shirt",
            category=ProductCategory.top,
            colors=[],
            style_tags=[],
            fit_tags=[],
            marketplaces=[Marketplace.taobao, Marketplace.tmall],
            budget=Budget(min=100, max=500),
            limit=6,
        )

        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].title, "white office cotton shirt women")
        self.assertEqual(products[0].category, ProductCategory.top)
        self.assertEqual(products[0].raw["category_match"], "exact")

    async def test_taobao_union_ignores_non_taobao_marketplace_requests(self) -> None:
        provider = FakeTaobaoUnionProductSearchProvider()

        products = await provider.search(
            query="women dress",
            category=ProductCategory.dress,
            colors=[],
            style_tags=[],
            fit_tags=[],
            marketplaces=[Marketplace.amazon],
            budget=Budget(min=100, max=500),
            limit=6,
        )

        self.assertEqual(products, [])
        self.assertIsNone(provider.last_request)

    async def test_taobao_union_no_result_response_returns_empty_list(self) -> None:
        class NoResultProvider(FakeTaobaoUnionProductSearchProvider):
            def _request(self, query: str, category: ProductCategory, budget: Budget, limit: int):
                return {"error_response": {"msg": "Remote service error", "sub_msg": "无结果"}}

        products = await NoResultProvider().search(
            query="white handbag",
            category=ProductCategory.bag,
            colors=[],
            style_tags=[],
            fit_tags=[],
            marketplaces=[Marketplace.taobao, Marketplace.tmall],
            budget=Budget(min=100, max=500),
            limit=6,
        )

        self.assertEqual(products, [])

    def test_taobao_union_request_is_signed_for_top_api(self) -> None:
        provider = FakeTaobaoUnionProductSearchProvider()

        params = provider._signed_params(
            query="model raw shirt query",
            category=ProductCategory.top,
            budget=Budget(min=100, max=600),
            limit=20,
        )

        self.assertEqual(params["method"], "taobao.tbk.dg.material.optional.upgrade")
        self.assertEqual(params["app_key"], "app-key")
        self.assertEqual(params["adzone_id"], "123456")
        self.assertEqual(params["q"], "model raw shirt query")
        self.assertIn("sign", params)
        self.assertNotEqual(params["sign"], "app-secret")

    def test_taobao_union_keyword_search_uses_documented_default_material(self) -> None:
        provider = FakeTaobaoUnionProductSearchProvider()

        params = provider._signed_params(
            query="women shirt",
            category=ProductCategory.top,
            budget=Budget(min=100, max=600),
            limit=20,
        )

        self.assertEqual(params["material_id"], "80309")
        self.assertEqual(params["sort"], "match")
        self.assertEqual(params["has_coupon"], "false")
        self.assertEqual(params["need_free_shipment"], "false")
        self.assertEqual(params["need_prepay"], "false")
        self.assertEqual(params["include_good_rate"], "false")
        self.assertEqual(params["include_rfd_rate"], "false")
        self.assertNotIn("include_pay_rate_30", params)
        self.assertNotIn("platform", params)

    def test_taobao_union_uses_supplied_taobao_category_table_for_cat_filter(self) -> None:
        provider = FakeTaobaoUnionProductSearchProvider()

        cases = {
            ProductCategory.top: "16",
            ProductCategory.bottom: "16",
            ProductCategory.dress: "16",
            ProductCategory.outerwear: "16",
            ProductCategory.shoes: "50006843",
            ProductCategory.bag: "50006842",
        }
        for category, taobao_cat in cases.items():
            with self.subTest(category=category):
                params = provider._signed_params(
                    query="same model keyword",
                    category=category,
                    budget=Budget(min=100, max=600),
                    limit=20,
                )
                self.assertEqual(params["cat"], taobao_cat)

    def test_taobao_union_routes_specific_queries_to_focused_taobao_category_ids(self) -> None:
        provider = FakeTaobaoUnionProductSearchProvider()

        top_params = provider._signed_params(
            query="通勤 衬衫 女",
            category=ProductCategory.top,
            budget=Budget(min=100, max=600),
            limit=20,
        )
        bottom_params = provider._signed_params(
            query="高腰 牛仔裤 女",
            category=ProductCategory.bottom,
            budget=Budget(min=100, max=600),
            limit=20,
        )
        accessory_params = provider._signed_params(
            query="珍珠 项链",
            category=ProductCategory.accessory,
            budget=Budget(min=100, max=600),
            limit=20,
        )

        self.assertIn("162104", top_params["cat"])
        self.assertNotEqual(top_params["cat"], "16")
        self.assertEqual(bottom_params["cat"], "162205")
        self.assertIn("50013865", accessory_params["cat"])
        self.assertNotIn("16", accessory_params["cat"].split(","))

    def test_taobao_union_splits_outfit_budget_into_category_item_price_window(self) -> None:
        provider = FakeTaobaoUnionProductSearchProvider()
        budget = Budget(min=900, max=2000)

        for category in (ProductCategory.top, ProductCategory.shoes, ProductCategory.bag):
            params = provider._signed_params(
                query="model query",
                category=category,
                budget=budget,
                limit=20,
            )
            start_price = int(params["start_price"])
            end_price = int(params["end_price"])

            self.assertLess(start_price, budget.min)
            self.assertLess(end_price, budget.max)
            self.assertGreaterEqual(end_price, start_price)

    def test_taobao_union_preserves_model_query_verbatim(self) -> None:
        provider = FakeTaobaoUnionProductSearchProvider()
        query = "pearl white top https://item.taobao.com/item.htm?id=123 clean proportion"

        params = provider._signed_params(
            query=query,
            category=ProductCategory.top,
            budget=Budget(min=100, max=600),
            limit=20,
        )

        self.assertEqual(params["q"], query)

    def test_taobao_union_accepts_full_pid_in_adzone_config(self) -> None:
        settings = Settings(
            taobao_union_app_key="app-key",
            taobao_union_app_secret="app-secret",
            taobao_union_adzone_id="mm_111111_222222_333333",
        )
        provider = TaobaoUnionProductSearchProvider(settings)

        params = provider._signed_params(
            query="women shirt",
            category=ProductCategory.top,
            budget=Budget(min=100, max=600),
            limit=20,
        )

        self.assertEqual(params["site_id"], "222222")
        self.assertEqual(params["adzone_id"], "333333")

    async def test_composite_provider_keeps_future_source_extension_point(self) -> None:
        provider = CompositeProductSearchProvider([LocalDemoSearchProvider()])

        products = await provider.search(
            query="model daily top",
            category=ProductCategory.top,
            colors=["ivory"],
            style_tags=["clean"],
            fit_tags=["short"],
            marketplaces=[Marketplace.taobao],
            budget=Budget(min=100, max=500),
            limit=3,
        )

        self.assertEqual(len(products), 3)
        self.assertEqual({product.source_provider for product in products}, {"local_demo"})
        self.assertEqual({product.category for product in products}, {ProductCategory.top})
        self.assertEqual(products[0].colors, ["ivory"])


if __name__ == "__main__":
    unittest.main()
