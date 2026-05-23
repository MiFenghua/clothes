import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { getTryOnProductValidationMessage, isAmazonTryOnProduct, isTryOnProduct } from "../src/domain/productRules.js";
import type { Product } from "../src/domain/types.js";

const baseProduct: Product = {
  productId: "amazon_B0TESTITEM",
  platform: "amazon",
  category: "top",
  title: "Women cropped knit top",
  price: 0,
  priceText: "$29.99",
  imageUrl: "https://m.media-amazon.com/images/I/71example._AC_UL320_.jpg",
  productUrl: "https://www.amazon.com/dp/B0TESTITEM",
  isExternalSearchLanding: false
};

describe("product rules", () => {
  it("allows Amazon detail products with product images for try-on", () => {
    assert.equal(isAmazonTryOnProduct(baseProduct), true);
    assert.equal(isTryOnProduct(baseProduct), true);
    assert.equal(getTryOnProductValidationMessage([baseProduct]), null);
  });

  it("rejects Amazon search landing links for try-on", () => {
    const landingProduct: Product = {
      ...baseProduct,
      productId: "amazon_landing",
      productUrl: "https://www.amazon.com/s?k=women+top",
      isExternalSearchLanding: true
    };

    assert.equal(isTryOnProduct(landingProduct), false);
    assert.match(getTryOnProductValidationMessage([landingProduct]) ?? "", /Amazon product detail items/);
  });
});
