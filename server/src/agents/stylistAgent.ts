import type { OutfitStrategy, ProductCategory, Scene, StyleTaskInput, UserStyleProfile } from "../domain/types.js";

const productCategories: ProductCategory[] = ["top", "bottom", "dress", "outerwear", "shoes", "bag", "accessory"];

const sceneFallback: Record<Scene, { theme: string; categories: ProductCategory[]; queries: string[]; words: string[] }> = {
  daily: {
    theme: "图片理解日常穿搭",
    categories: ["top", "bottom", "shoes", "bag"],
    queries: ["短款上衣 女 日常 显比例", "高腰直筒裤 女 日常", "低跟单鞋 女 百搭", "小包 女 简约"],
    words: ["日常", "舒适", "显比例"]
  },
  commute: {
    theme: "图片理解通勤穿搭",
    categories: ["top", "bottom", "outerwear", "shoes"],
    queries: ["衬衫 女 通勤 利落", "高腰西装裤 女 通勤", "薄外套 女 通勤", "低跟单鞋 女"],
    words: ["通勤", "利落", "轻熟"]
  },
  date: {
    theme: "图片理解约会穿搭",
    categories: ["dress", "shoes", "bag"],
    queries: ["收腰连衣裙 女 约会 显比例", "浅口低跟单鞋 女 约会", "小方包 女 精致"],
    words: ["约会", "温柔", "精致"]
  },
  travel: {
    theme: "图片理解旅行穿搭",
    categories: ["top", "bottom", "shoes", "bag"],
    queries: ["上镜上衣 女 旅行 舒适", "高腰休闲裤 女 旅行", "舒适平底鞋 女", "轻便斜挎包 女"],
    words: ["旅行", "舒适", "上镜"]
  },
  party: {
    theme: "图片理解聚会穿搭",
    categories: ["top", "bottom", "shoes", "accessory"],
    queries: ["设计感上衣 女 聚会", "高腰半身裙 女 聚会", "低跟单鞋 女 精致", "项链 女 精致"],
    words: ["聚会", "设计感", "氛围"]
  }
};

export class StylistAgent {
  plan(profile: UserStyleProfile, input: StyleTaskInput): OutfitStrategy {
    const modelStrategy = this.strategyFromVisionModel(profile, input);
    if (modelStrategy) return modelStrategy;

    return this.fallbackStrategy(profile, input);
  }

  private strategyFromVisionModel(profile: UserStyleProfile, input: StyleTaskInput): OutfitStrategy | null {
    const source = profile.recommendedOutfitStrategy;
    if (!source) return null;

    const requiredCategories = this.normalizeCategories(source.requiredCategories);
    const searchQueries = this.normalizeQueries(source.searchQueries);
    if (!this.hasCoreOutfit(requiredCategories) || searchQueries.length < 2) return null;

    return {
      outfitTheme: source.outfitTheme?.trim() || sceneFallback[input.scene].theme,
      styleDirection: this.uniqueWords([...source.styleDirection, ...profile.currentStyle]).slice(0, 8),
      requiredCategories,
      colorDirection: this.uniqueWords(source.colorDirection.length > 0 ? source.colorDirection : profile.palette).slice(0, 6),
      fitDirection: this.uniqueWords([...source.fitDirection, ...profile.fitAdvice.slice(0, 2)]).slice(0, 8),
      searchQueries,
      avoidQueries: this.uniqueWords([...source.avoidQueries, ...this.splitWords(input.avoid)])
    };
  }

  private fallbackStrategy(profile: UserStyleProfile, input: StyleTaskInput): OutfitStrategy {
    const fallback = sceneFallback[input.scene];
    const ageStyleWords = this.ageStyleWords(input.ageYears);
    const styleWords = this.uniqueWords([...profile.currentStyle, ...fallback.words, ...ageStyleWords]).slice(0, 8);
    const colorWords = profile.palette.slice(0, 2);
    const fitWords = profile.fitAdvice.slice(0, 2);
    const querySuffix = this.uniqueWords([...styleWords.slice(0, 3), ...ageStyleWords, ...colorWords, ...fitWords]).join(" ");

    return {
      outfitTheme: fallback.theme,
      styleDirection: styleWords,
      requiredCategories: fallback.categories,
      colorDirection: profile.palette,
      fitDirection: this.uniqueWords(["高腰线", "线条干净", ...fitWords]),
      searchQueries: fallback.queries.map((query) => `${query} ${querySuffix}`.trim()),
      avoidQueries: this.splitWords(input.avoid)
    };
  }

  private normalizeCategories(categories: ProductCategory[]) {
    return this.uniqueWords(categories).filter((category): category is ProductCategory => productCategories.includes(category)).slice(0, 5);
  }

  private normalizeQueries(queries: string[]) {
    return this.uniqueWords(
      queries
        .map((query) => query.trim().replace(/\s+/g, " "))
        .filter((query) => query.length >= 2)
    ).slice(0, 8);
  }

  private hasCoreOutfit(categories: ProductCategory[]) {
    return categories.includes("dress") || (categories.includes("top") && categories.includes("bottom"));
  }

  private splitWords(value: string | null) {
    return value?.split(/[，,、\s]+/).map((word) => word.trim()).filter(Boolean) ?? [];
  }

  private ageStyleWords(ageYears: number | null) {
    if (!ageYears) return [];
    if (ageYears < 24) return ["清爽", "轻甜"];
    if (ageYears < 35) return ["轻熟", "精致"];
    if (ageYears < 50) return ["质感", "优雅"];
    return ["成熟优雅", "舒适质感"];
  }

  private uniqueWords<T extends string>(words: T[]) {
    return words.filter((word, index, list) => Boolean(word) && list.indexOf(word) === index);
  }
}
