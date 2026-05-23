export type Scene = "daily" | "commute" | "date" | "travel" | "party";

export type TaskStatus =
  | "created"
  | "photo_uploaded"
  | "validating_photo"
  | "analyzing_photo"
  | "profile_ready"
  | "planning_outfit"
  | "searching_products"
  | "parsing_products"
  | "building_outfit"
  | "outfit_ready"
  | "generating_image"
  | "quality_checking"
  | "succeeded"
  | "failed";

export type ErrorCode =
  | "PHOTO_INVALID"
  | "PHOTO_NOT_FULL_BODY"
  | "SEARCH_EMPTY"
  | "SCRAPE_BLOCKED"
  | "OUTFIT_BUILD_FAILED"
  | "IMAGE_GENERATION_FAILED"
  | "QUALITY_CHECK_FAILED"
  | "TIMEOUT";

export interface Budget {
  min: number | null;
  max: number | null;
}

export interface StyleTaskInput {
  photoUrl: string;
  photoPath: string;
  scene: Scene;
  budget: Budget;
  ageYears: number | null;
  heightCm: number | null;
  weightKg: number | null;
  usualSize: string | null;
  likedStyle: string | null;
  avoid: string | null;
}

export interface TaskError {
  errorCode: ErrorCode;
  userMessage: string;
  internalMessage?: string;
}

export interface StyleTask {
  taskId: string;
  userId: string | null;
  status: TaskStatus;
  progress: number;
  message: string;
  createdAt: string;
  updatedAt: string;
  input: StyleTaskInput;
  error: TaskError | null;
  profile?: UserStyleProfile;
  strategy?: OutfitStrategy;
  products?: Product[];
  result?: OutfitResult;
}

export interface UserStyleProfile {
  bodyProportion: "petite" | "balanced" | "tall" | "curvy" | "straight";
  heightImpression: "petite" | "average" | "tall";
  undertone: "warm" | "cool" | "neutral";
  hairTone: "dark" | "brown" | "light" | "red" | "covered";
  currentStyle: string[];
  fitAdvice: string[];
  palette: string[];
  occasionFit: Scene[];
  confidence: number;
  photoQuality: {
    isFullBody: boolean;
    faceVisible: boolean;
    lighting: "poor" | "fair" | "good";
    occlusion: "low" | "medium" | "high";
  };
  summary: string;
  recommendedOutfitStrategy?: OutfitStrategy;
}

export interface OutfitStrategy {
  outfitTheme: string;
  styleDirection: string[];
  requiredCategories: ProductCategory[];
  colorDirection: string[];
  fitDirection: string[];
  searchQueries: string[];
  avoidQueries: string[];
}

export type ProductCategory = "top" | "bottom" | "dress" | "outerwear" | "shoes" | "bag" | "accessory";

export interface Product {
  productId: string;
  platform: "amazon" | "taobao" | "tmall" | "jd" | "pdd" | "demo";
  category: ProductCategory;
  title: string;
  price: number;
  priceText?: string;
  imageUrl: string;
  productUrl: string;
  isExternalSearchLanding?: boolean;
  shopName?: string;
  salesText?: string;
  colors?: string[];
  sizes?: string[];
  styleTags?: string[];
  fitTags?: string[];
  reason?: string;
  score?: number;
  raw?: unknown;
}

export interface OutfitItem extends Product {
  matchReason: string;
  sizeAdvice?: string;
}

export interface Outfit {
  title: string;
  reason: string;
  items: OutfitItem[];
  totalPrice: number;
  tryOnDescription: string;
}

export interface OutfitResult {
  taskId: string;
  status: "succeeded";
  tryOnImageUrl: string;
  outfit: Outfit;
}

export interface TaskProgressView {
  taskId: string;
  status: TaskStatus;
  progress: number;
  message: string;
  errorCode?: ErrorCode;
  userMessage?: string;
}
