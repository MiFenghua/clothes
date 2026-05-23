import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { OutfitBuilder } from "../src/agents/outfitBuilder.js";
import type { OutfitStrategy, Product, StyleTaskInput, UserStyleProfile } from "../src/domain/types.js";

const profile: UserStyleProfile = {
  bodyProportion: "balanced",
  heightImpression: "average",
  undertone: "neutral",
  hairTone: "dark",
  currentStyle: ["clean"],
  fitAdvice: [],
  palette: ["ivory", "denim"],
  occasionFit: ["daily"],
  confidence: 0.8,
  photoQuality: {
    isFullBody: true,
    faceVisible: true,
    lighting: "good",
    occlusion: "low"
  },
  summary: "test"
};

const input: StyleTaskInput = {
  photoUrl: "http://127.0.0.1/uploads/test.jpg",
  photoPath: "server/storage/uploads/test.jpg",
  scene: "daily",
  budget: { min: 300, max: 800 },
  ageYears: null,
  heightCm: null,
  weightKg: null,
  usualSize: null,
  likedStyle: null,
  avoid: null
};

const strategy: OutfitStrategy = {
  outfitTheme: "test outfit",
  styleDirection: [],
  requiredCategories: ["top", "bottom"],
  colorDirection: [],
  fitDirection: [],
  searchQueries: [],
  avoidQueries: []
};

const realAmazonProduct = (category: Product["category"], score: number): Product => ({
  productId: `amazon_real_${category}`,
  platform: "amazon",
  category,
  title: `Real Amazon ${category}`,
  price: 0,
  priceText: "$29.99",
  imageUrl: `https://m.media-amazon.com/images/I/71real${category}.jpg`,
  productUrl: "https://www.amazon.com/dp/B0TESTITEM",
  isExternalSearchLanding: false,
  score
});

const landingProduct = (category: Product["category"], score: number): Product => ({
  productId: `amazon_landing_${category}`,
  platform: "amazon",
  category,
  title: `Amazon search landing ${category}`,
  price: 0,
  priceText: "进入Amazon查看价格",
  imageUrl: "https://www.amazon.com/favicon.ico",
  productUrl: "https://www.amazon.com/s?k=test",
  isExternalSearchLanding: true,
  score
});

describe("outfit builder", () => {
  it("prefers real try-on products over higher-scored search landing cards", () => {
    const outfit = new OutfitBuilder().build(profile, strategy, [
      landingProduct("top", 1),
      realAmazonProduct("top", 0.6),
      landingProduct("bottom", 1),
      realAmazonProduct("bottom", 0.6)
    ], input);

    assert.deepEqual(
      outfit.items.map((item) => item.productId),
      ["amazon_real_top", "amazon_real_bottom"]
    );
  });
});
