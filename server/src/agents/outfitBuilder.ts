import type { Outfit, OutfitStrategy, Product, ProductCategory, StyleTaskInput, UserStyleProfile } from "../domain/types.js";
import { isTryOnProduct } from "../domain/productRules.js";

const categoryPriority: ProductCategory[] = ["dress", "top", "bottom", "outerwear", "shoes", "bag", "accessory"];

export class OutfitBuilder {
  build(profile: UserStyleProfile, strategy: OutfitStrategy, products: Product[], input: StyleTaskInput): Outfit {
    const selected = new Map<ProductCategory, Product>();
    const allowedCategories = new Set(strategy.requiredCategories);

    for (const category of categoryPriority) {
      if (!allowedCategories.has(category)) continue;
      const best = products
        .filter((product) => product.category === category)
        .sort((a, b) => this.selectionRank(b) - this.selectionRank(a) || (b.score ?? 0) - (a.score ?? 0))[0];
      if (best) selected.set(category, best);
    }

    const hasDress = selected.has("dress");
    const hasSeparateCore = selected.has("top") && selected.has("bottom");
    if (!hasDress && !hasSeparateCore) {
      throw new Error("Core outfit categories are missing");
    }

    const items = [...selected.values()].slice(0, 5).map((product) => ({
      ...product,
      matchReason: product.reason ?? "与当前场景、版型和配色方向匹配。",
      sizeAdvice: input.usualSize ? `可优先参考平时 ${input.usualSize} 码，最终以商品尺码表为准。` : "尺码建议仅供参考，请以商品尺码表为准。"
    }));

    const totalPrice = items.reduce((sum, item) => sum + item.price, 0);
    const sceneHint = input.scene === "commute" ? "适合通勤，也能保持轻松感。" : "适合日常出街，决策成本低。";
    const colorHint = profile.palette.slice(0, 3).join("、");

    return {
      title: strategy.outfitTheme,
      reason: `这套搭配用高腰线和干净轮廓强化比例，${sceneHint} 主色参考 ${colorHint}，整体清爽耐看。`,
      items,
      totalPrice,
      tryOnDescription: items.map((item) => `${item.category}: ${item.title}`).join("; ")
    };
  }

  private selectionRank(product: Product) {
    if (isTryOnProduct(product)) return 2;
    if (!product.isExternalSearchLanding) return 1;
    return 0;
  }
}
