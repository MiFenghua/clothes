import type { OutfitItem, Product } from "./types.js";

const taobaoProductUrlPatterns = [
  /^https:\/\/item\.taobao\.com\/item\.htm/i,
  /^https:\/\/detail\.tmall\.com\/item\.htm/i,
  /^https:\/\/world\.taobao\.com\/item\//i
];

const amazonProductUrlPatterns = [
  /^https:\/\/[^/]*amazon\.[^/]+\/dp\/[A-Z0-9]{10}(?:[/?]|$)/i,
  /^https:\/\/[^/]*amazon\.[^/]+\/gp\/product\/[A-Z0-9]{10}(?:[/?]|$)/i
];

const blockedReferenceImagePatterns = [
  "O1CN01PiwQF81R0Pr5k8Yck",
  "360buyimg.com/img/jfs/t1/178680",
  "funimg.pddpic.com/base/logo",
  "amazon.com/favicon.ico"
];

export function isTaobaoTryOnProduct(product: Product | OutfitItem) {
  const isTaobaoPlatform = product.platform === "taobao" || product.platform === "tmall";
  const isProductDetailUrl = taobaoProductUrlPatterns.some((pattern) => pattern.test(product.productUrl));

  return isTaobaoPlatform && !product.isExternalSearchLanding && isProductDetailUrl && hasUsableProductImage(product);
}

export function isAmazonTryOnProduct(product: Product | OutfitItem) {
  const isAmazonPlatform = product.platform === "amazon";
  const isProductDetailUrl = amazonProductUrlPatterns.some((pattern) => pattern.test(product.productUrl));

  return isAmazonPlatform && !product.isExternalSearchLanding && isProductDetailUrl && hasUsableProductImage(product);
}

export function isTryOnProduct(product: Product | OutfitItem) {
  return isTaobaoTryOnProduct(product) || isAmazonTryOnProduct(product);
}

export function getTryOnProductValidationMessage(items: Array<Product | OutfitItem>) {
  const invalidItems = items.filter((item) => !isTryOnProduct(item));
  if (invalidItems.length === 0) return null;

  return `Try-on requires actual Taobao/Tmall or Amazon product detail items with product images. Invalid products: ${invalidItems
    .map((item) => `${item.productId}:${item.platform}:${item.productUrl}`)
    .join(", ")}`;
}

function hasUsableProductImage(product: Product | OutfitItem) {
  return Boolean(product.imageUrl) && !blockedReferenceImagePatterns.some((pattern) => product.imageUrl.includes(pattern));
}
