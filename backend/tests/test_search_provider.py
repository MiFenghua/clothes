from __future__ import annotations

import unittest

from app.config import Settings
from app.providers.search import (
    CompositeProductSearchProvider,
    LocalDemoSearchProvider,
    TaobaoUnionProductSearchProvider,
    _fit_tags,
    _style_tags,
)
from app.schemas.domain import Budget, Marketplace, ProductCategory


def taobao_settings() -> Settings:
    return Settings(
        taobao_union_app_key="app-key",
        taobao_union_app_secret="app-secret",
        taobao_union_adzone_id="123456",
        taobao_union_site_id="7890",
    )


class FakeTaobaoUnionProductSearchProvider(TaobaoUnionProductSearchProvider):
    def __init__(self) -> None:
        super().__init__(taobao_settings())
        self.last_request: tuple[str, Budget, int] | None = None

    def _request(self, query: str, budget: Budget, limit: int):
        self.last_request = (query, budget, limit)
        return {
            "tbk_dg_material_optional_upgrade_response": {
                "result_list": {
                    "map_data": [
                        {
                            "item_id": "612345678901",
                            "title": "高腰直筒裤 女 通勤 显比例",
                            "pict_url": "//img.alicdn.com/bao/uploaded/item.jpg",
                            "coupon_share_url": "//uland.taobao.com/coupon/edetail?e=abc",
                            "item_url": "https://detail.tmall.com/item.htm?id=612345678901",
                            "zk_final_price": "199.00",
                            "shop_title": "测试天猫店",
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
    async def test_taobao_union_maps_material_rows_to_product_candidates(self) -> None:
        provider = FakeTaobaoUnionProductSearchProvider()

        products = await provider.search(
            query="高腰直筒裤 女 通勤 显比例",
            marketplaces=[Marketplace.taobao, Marketplace.tmall],
            budget=Budget(min=100, max=500),
            limit=6,
        )

        self.assertEqual(len(products), 1)
        product = products[0]
        self.assertEqual(product.source_provider, "taobao_union")
        self.assertEqual(product.marketplace, Marketplace.tmall)
        self.assertEqual(product.category, ProductCategory.bottom)
        self.assertEqual(product.price, 199.0)
        self.assertTrue(product.image_url.startswith("https://img.alicdn.com/"))
        self.assertTrue(product.product_url.startswith("https://uland.taobao.com/"))
        self.assertEqual(product.raw["item_id"], "612345678901")

    async def test_taobao_union_ignores_non_taobao_marketplace_requests(self) -> None:
        provider = FakeTaobaoUnionProductSearchProvider()

        products = await provider.search(
            query="women dress",
            marketplaces=[Marketplace.amazon],
            budget=Budget(min=100, max=500),
            limit=6,
        )

        self.assertEqual(products, [])
        self.assertIsNone(provider.last_request)

    def test_taobao_union_request_is_signed_for_top_api(self) -> None:
        provider = FakeTaobaoUnionProductSearchProvider()

        params = provider._signed_params(query="衬衫 女 通勤", budget=Budget(min=100, max=600), limit=20)

        self.assertEqual(params["method"], "taobao.tbk.dg.material.optional.upgrade")
        self.assertEqual(params["app_key"], "app-key")
        self.assertEqual(params["adzone_id"], "123456")
        self.assertEqual(params["q"], "衬衫 女 通勤")
        self.assertIn("sign", params)
        self.assertNotEqual(params["sign"], "app-secret")

    async def test_composite_provider_keeps_future_source_extension_point(self) -> None:
        provider = CompositeProductSearchProvider([LocalDemoSearchProvider()])

        products = await provider.search(
            query="women daily top",
            marketplaces=[Marketplace.taobao],
            budget=Budget(min=100, max=500),
            limit=3,
        )

        self.assertEqual(len(products), 3)
        self.assertEqual({product.source_provider for product in products}, {"local_demo"})


def test_query_tags_preserve_common_style_and_fit_terms() -> None:
    assert "可爱" in _style_tags("可爱 宽松 上衣")
    assert "休闲" in _style_tags("白色 舒适 休闲鞋")
    assert "宽松" in _fit_tags("可爱 宽松 上衣")
    assert "舒适" in _fit_tags("白色 舒适 休闲鞋")


if __name__ == "__main__":
    unittest.main()
