import type { Budget, OutfitStrategy, Product, ProductCategory } from "../../domain/types.js";
import type { SearchProvider } from "./searchProvider.js";

const categoryKeywords: Record<ProductCategory, string[]> = {
  top: ["上衣", "针织", "衬衫", "短袖"],
  bottom: ["裤", "裙", "牛仔", "西装裤"],
  dress: ["连衣裙", "裙"],
  outerwear: ["外套", "西装", "开衫"],
  shoes: ["鞋", "单鞋", "乐福"],
  bag: ["包", "托特", "腋下包"],
  accessory: ["项链", "耳环", "腰带"]
};

const demoProducts: Product[] = [
  {
    productId: "demo_top_001",
    platform: "demo",
    category: "top",
    title: "短款针织上衣女春夏薄款显比例",
    price: 129,
    imageUrl: "https://images.unsplash.com/photo-1434389677669-e08b4cac3105?auto=format&fit=crop&w=900&q=80",
    productUrl: "https://s.taobao.com/search?q=%E7%9F%AD%E6%AC%BE%E9%92%88%E7%BB%87%E4%B8%8A%E8%A1%A3%20%E5%A5%B3",
    shopName: "Demo 商品源",
    salesText: "搜索热词样例",
    colors: ["ivory"],
    sizes: ["S", "M", "L"],
    styleTags: ["干净", "显比例"],
    fitTags: ["短款", "修身"],
    reason: "短款廓形能强化腰线，适合作为显比例核心单品。"
  },
  {
    productId: "demo_top_002",
    platform: "demo",
    category: "top",
    title: "通勤短袖衬衫女垂感宽松不沉闷",
    price: 159,
    imageUrl: "https://images.unsplash.com/photo-1485462537746-965f33f7f6a7?auto=format&fit=crop&w=900&q=80",
    productUrl: "https://s.taobao.com/search?q=%E9%80%9A%E5%8B%A4%E7%9F%AD%E8%A2%96%E8%A1%AC%E8%A1%AB%20%E5%A5%B3",
    shopName: "Demo 商品源",
    salesText: "搜索热词样例",
    colors: ["white"],
    sizes: ["S", "M", "L"],
    styleTags: ["通勤", "利落"],
    fitTags: ["垂感", "短袖"],
    reason: "白色衬衫清爽利落，适合通勤和日常切换。"
  },
  {
    productId: "demo_bottom_001",
    platform: "demo",
    category: "bottom",
    title: "高腰直筒牛仔裤女春夏显腿长",
    price: 199,
    imageUrl: "https://images.unsplash.com/photo-1542272604-787c3835535d?auto=format&fit=crop&w=900&q=80",
    productUrl: "https://s.taobao.com/search?q=%E9%AB%98%E8%85%B0%E7%9B%B4%E7%AD%92%E7%89%9B%E4%BB%94%E8%A3%A4%20%E5%A5%B3",
    shopName: "Demo 商品源",
    salesText: "搜索热词样例",
    colors: ["denim"],
    sizes: ["S", "M", "L", "XL"],
    styleTags: ["日常", "百搭"],
    fitTags: ["高腰", "直筒"],
    reason: "高腰直筒版型能拉长下半身线条。"
  },
  {
    productId: "demo_bottom_002",
    platform: "demo",
    category: "bottom",
    title: "高腰西装裤女通勤垂感显瘦",
    price: 229,
    imageUrl: "https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?auto=format&fit=crop&w=900&q=80",
    productUrl: "https://s.taobao.com/search?q=%E9%AB%98%E8%85%B0%E8%A5%BF%E8%A3%85%E8%A3%A4%20%E5%A5%B3",
    shopName: "Demo 商品源",
    salesText: "搜索热词样例",
    colors: ["navy", "black"],
    sizes: ["S", "M", "L"],
    styleTags: ["通勤", "利落"],
    fitTags: ["高腰", "垂感"],
    reason: "垂感裤型更适合通勤场景，保持干净线条。"
  },
  {
    productId: "demo_shoes_001",
    platform: "demo",
    category: "shoes",
    title: "低跟单鞋女通勤百搭舒适",
    price: 169,
    imageUrl: "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?auto=format&fit=crop&w=900&q=80",
    productUrl: "https://s.taobao.com/search?q=%E4%BD%8E%E8%B7%9F%E5%8D%95%E9%9E%8B%20%E5%A5%B3%20%E9%80%9A%E5%8B%A4",
    shopName: "Demo 商品源",
    salesText: "搜索热词样例",
    colors: ["black", "ivory"],
    sizes: ["35", "36", "37", "38", "39"],
    styleTags: ["百搭", "通勤"],
    fitTags: ["低跟"],
    reason: "低跟鞋能补足精致度，又不会牺牲舒适性。"
  },
  {
    productId: "demo_shoes_002",
    platform: "demo",
    category: "shoes",
    title: "浅口乐福鞋女日常通勤",
    price: 189,
    imageUrl: "https://images.unsplash.com/photo-1533867617858-e7b97e060509?auto=format&fit=crop&w=900&q=80",
    productUrl: "https://s.taobao.com/search?q=%E4%B9%90%E7%A6%8F%E9%9E%8B%20%E5%A5%B3%20%E9%80%9A%E5%8B%A4",
    shopName: "Demo 商品源",
    salesText: "搜索热词样例",
    colors: ["brown", "black"],
    sizes: ["35", "36", "37", "38", "39"],
    styleTags: ["利落", "百搭"],
    fitTags: ["浅口"],
    reason: "乐福鞋增强整体利落感，适配裤装。"
  },
  {
    productId: "demo_bag_001",
    platform: "demo",
    category: "bag",
    title: "简约腋下包女小众百搭",
    price: 139,
    imageUrl: "https://images.unsplash.com/photo-1594223274512-ad4803739b7c?auto=format&fit=crop&w=900&q=80",
    productUrl: "https://s.taobao.com/search?q=%E7%AE%80%E7%BA%A6%E8%85%8B%E4%B8%8B%E5%8C%85%20%E5%A5%B3",
    shopName: "Demo 商品源",
    salesText: "搜索热词样例",
    colors: ["ivory"],
    sizes: ["F"],
    styleTags: ["简约", "日常"],
    fitTags: ["小包"],
    reason: "小包能提升完整度，不会压低视觉重心。"
  },
  {
    productId: "demo_bag_002",
    platform: "demo",
    category: "bag",
    title: "通勤托特包女大容量简洁",
    price: 179,
    imageUrl: "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?auto=format&fit=crop&w=900&q=80",
    productUrl: "https://s.taobao.com/search?q=%E9%80%9A%E5%8B%A4%E6%89%98%E7%89%B9%E5%8C%85%20%E5%A5%B3",
    shopName: "Demo 商品源",
    salesText: "搜索热词样例",
    colors: ["black", "brown"],
    sizes: ["F"],
    styleTags: ["通勤", "简洁"],
    fitTags: ["大容量"],
    reason: "托特包更适合通勤容量需求。"
  },
  {
    productId: "demo_outerwear_001",
    platform: "demo",
    category: "outerwear",
    title: "短款薄西装外套女通勤显比例",
    price: 269,
    imageUrl: "https://images.unsplash.com/photo-1551488831-00ddcb6c6bd3?auto=format&fit=crop&w=900&q=80",
    productUrl: "https://s.taobao.com/search?q=%E7%9F%AD%E6%AC%BE%E8%A5%BF%E8%A3%85%E5%A4%96%E5%A5%97%20%E5%A5%B3",
    shopName: "Demo 商品源",
    salesText: "搜索热词样例",
    colors: ["gray", "navy"],
    sizes: ["S", "M", "L"],
    styleTags: ["通勤", "轻熟"],
    fitTags: ["短款", "直线条"],
    reason: "短外套能保持腰线清晰，适合通勤场景。"
  },
  {
    productId: "demo_accessory_001",
    platform: "demo",
    category: "accessory",
    title: "细链项链女简约锁骨链",
    price: 69,
    imageUrl: "https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?auto=format&fit=crop&w=900&q=80",
    productUrl: "https://s.taobao.com/search?q=%E7%BB%86%E9%93%BE%E9%A1%B9%E9%93%BE%20%E5%A5%B3%20%E7%AE%80%E7%BA%A6",
    shopName: "Demo 商品源",
    salesText: "搜索热词样例",
    colors: ["silver"],
    sizes: ["F"],
    styleTags: ["精致", "简约"],
    fitTags: ["细链"],
    reason: "小体量配饰能增加精致感，不抢整体比例。"
  }
];

export class DemoSearchProvider implements SearchProvider {
  async search({ strategy, budget, limitPerQuery }: { strategy: OutfitStrategy; budget: Budget; limitPerQuery: number }) {
    const required = new Set(strategy.requiredCategories);
    const avoidText = strategy.avoidQueries.join(" ");
    const max = budget.max;

    return demoProducts
      .filter((product) => required.has(product.category))
      .filter((product) => !max || product.price <= max * 1.2)
      .filter((product) => !avoidText || !product.title.includes(avoidText))
      .map((product, index) => ({
        ...product,
        score: this.scoreProduct(product, strategy, budget, index)
      }))
      .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
      .slice(0, Math.max(10, limitPerQuery));
  }

  private scoreProduct(product: Product, strategy: OutfitStrategy, budget: Budget, index: number) {
    const categoryFit = strategy.requiredCategories.includes(product.category) ? 1 : 0;
    const styleText = [...strategy.styleDirection, ...strategy.fitDirection, ...strategy.colorDirection].join(" ");
    const productText = [product.title, ...(product.styleTags ?? []), ...(product.fitTags ?? []), ...(product.colors ?? [])].join(" ");
    const styleHits = styleText
      .split(/\s+/)
      .filter(Boolean)
      .reduce((hits, word) => hits + (productText.includes(word) ? 1 : 0), 0);
    const styleMatch = Math.min(styleHits / 4, 1);
    const budgetScore = budget.max ? Math.max(0, 1 - product.price / (budget.max * 1.2)) : 0.8;
    const trendScore = Math.max(0.4, 1 - index * 0.05);

    return categoryFit * 0.3 + styleMatch * 0.2 + 0.2 + 0.1 + trendScore * 0.1 + budgetScore * 0.1;
  }
}

export function inferCategoryFromQuery(query: string): ProductCategory {
  if (/连衣裙|茶歇裙|吊带裙|针织裙|礼服裙/.test(query)) return "dress";

  for (const [category, keywords] of Object.entries(categoryKeywords) as [ProductCategory, string[]][]) {
    if (keywords.some((keyword) => query.includes(keyword))) return category;
  }
  return "top";
}
