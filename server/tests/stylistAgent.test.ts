import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { StylistAgent } from "../src/agents/stylistAgent.js";
import type { StyleTaskInput, UserStyleProfile } from "../src/domain/types.js";

const baseProfile: UserStyleProfile = {
  bodyProportion: "balanced",
  heightImpression: "average",
  undertone: "neutral",
  hairTone: "dark",
  currentStyle: ["干净"],
  fitAdvice: ["提高腰线"],
  palette: ["ivory", "denim"],
  occasionFit: ["date"],
  confidence: 0.8,
  photoQuality: {
    isFullBody: true,
    faceVisible: true,
    lighting: "good",
    occlusion: "low"
  },
  summary: "适合干净利落的约会造型。"
};

const baseInput: StyleTaskInput = {
  photoUrl: "http://127.0.0.1/uploads/test.jpg",
  photoPath: "server/storage/uploads/test.jpg",
  scene: "date",
  budget: { min: 300, max: 800 },
  ageYears: null,
  heightCm: null,
  weightKg: null,
  usualSize: null,
  likedStyle: null,
  avoid: null
};

describe("stylist agent", () => {
  it("uses vision-model outfit keywords as the source of truth", () => {
    const plan = new StylistAgent().plan(
      {
        ...baseProfile,
        recommendedOutfitStrategy: {
          outfitTheme: "轻甜约会穿搭",
          styleDirection: ["轻甜", "柔和"],
          requiredCategories: ["top", "bottom", "shoes", "bag"],
          colorDirection: ["misty pink", "ivory"],
          fitDirection: ["短款", "高腰"],
          searchQueries: ["雾粉短款针织上衣 女 约会", "高腰A字半身裙 女 显比例", "玛丽珍低跟单鞋 女", "腋下小包 女"],
          avoidQueries: []
        }
      },
      { ...baseInput, heightCm: 156, avoid: "厚底" }
    );

    assert.equal(plan.outfitTheme, "轻甜约会穿搭");
    assert.deepEqual(plan.requiredCategories, ["top", "bottom", "shoes", "bag"]);
    assert.deepEqual(plan.searchQueries, ["雾粉短款针织上衣 女 约会", "高腰A字半身裙 女 显比例", "玛丽珍低跟单鞋 女", "腋下小包 女"]);
    assert.ok(plan.avoidQueries.includes("厚底"));
  });

  it("keeps different vision-model recommendations different for the same scene", () => {
    const stylist = new StylistAgent();
    const firstPlan = stylist.plan(
      {
        ...baseProfile,
        recommendedOutfitStrategy: {
          outfitTheme: "法式裙装约会",
          styleDirection: ["法式", "温柔"],
          requiredCategories: ["dress", "shoes", "bag"],
          colorDirection: ["ivory"],
          fitDirection: ["收腰"],
          searchQueries: ["象牙白收腰茶歇连衣裙 女 约会", "浅口低跟单鞋 女 温柔", "链条小方包 女 精致"],
          avoidQueries: []
        }
      },
      baseInput
    );
    const secondPlan = stylist.plan(
      {
        ...baseProfile,
        recommendedOutfitStrategy: {
          outfitTheme: "松弛牛仔约会",
          styleDirection: ["松弛", "清爽"],
          requiredCategories: ["top", "bottom", "shoes", "bag"],
          colorDirection: ["denim", "white"],
          fitDirection: ["高腰", "肩颈留白"],
          searchQueries: ["白色方领短袖上衣 女 约会", "高腰直筒牛仔裤 女 显腿长", "乐福鞋 女", "简约小包 女"],
          avoidQueries: []
        }
      },
      baseInput
    );

    assert.notDeepEqual(firstPlan.searchQueries, secondPlan.searchQueries);
    assert.deepEqual(firstPlan.requiredCategories, ["dress", "shoes", "bag"]);
    assert.deepEqual(secondPlan.requiredCategories, ["top", "bottom", "shoes", "bag"]);
  });

  it("falls back only when the vision model does not return a usable strategy", () => {
    const plan = new StylistAgent().plan(baseProfile, { ...baseInput, ageYears: 37 });

    assert.equal(plan.outfitTheme, "图片理解约会穿搭");
    assert.deepEqual(plan.requiredCategories, ["dress", "shoes", "bag"]);
    assert.match(plan.searchQueries.join(" "), /收腰连衣裙/);
    assert.match(plan.searchQueries.join(" "), /质感|优雅/);
  });
});
