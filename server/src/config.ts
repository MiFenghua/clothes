import dotenv from "dotenv";

dotenv.config();

const parseBoolean = (value: string | undefined, fallback: boolean) => {
  if (value === undefined) return fallback;
  return ["1", "true", "yes", "on"].includes(value.toLowerCase());
};

export const config = {
  port: Number(process.env.PORT ?? 3000),
  publicBaseUrl: process.env.PUBLIC_BASE_URL ?? "http://127.0.0.1:3000",
  searchProvider: process.env.SEARCH_PROVIDER ?? "hybrid",
  amazonBrowserEnabled: parseBoolean(process.env.AMAZON_BROWSER_ENABLED, true),
  amazonHeadless: parseBoolean(process.env.AMAZON_HEADLESS, true),
  amazonChromePath: process.env.AMAZON_CHROME_PATH ?? process.env.TAOBAO_CHROME_PATH ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  amazonUserDataDir: process.env.AMAZON_USER_DATA_DIR ?? "server/storage/amazon-browser-profile",
  amazonMarketplaceBaseUrl: process.env.AMAZON_MARKETPLACE_BASE_URL ?? "https://www.amazon.com",
  amazonSearchUrlTemplate: process.env.AMAZON_SEARCH_URL_TEMPLATE,
  amazonSearchTimeoutMs: Number(process.env.AMAZON_SEARCH_TIMEOUT_MS ?? 30000),
  taobaoBrowserEnabled: parseBoolean(process.env.TAOBAO_BROWSER_ENABLED, true),
  taobaoHeadless: parseBoolean(process.env.TAOBAO_HEADLESS, true),
  taobaoChromePath: process.env.TAOBAO_CHROME_PATH ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  taobaoUserDataDir: process.env.TAOBAO_USER_DATA_DIR ?? "server/storage/taobao-browser-profile",
  taobaoSearchTimeoutMs: Number(process.env.TAOBAO_SEARCH_TIMEOUT_MS ?? 30000),
  ecommercePlatforms: (process.env.ECOMMERCE_PLATFORMS ?? "amazon,taobao,jd,pdd")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean),
  enableDemoSearch: parseBoolean(process.env.ENABLE_DEMO_SEARCH, true),
  authStorePath: process.env.AUTH_STORE_PATH ?? "server/storage/auth-store.json",
  authSessionCookieName: process.env.AUTH_SESSION_COOKIE_NAME ?? "clothes_session",
  authSessionMaxAgeDays: Number(process.env.AUTH_SESSION_MAX_AGE_DAYS ?? 30),
  googleOAuthStateCookieName: "clothes_google_oauth_state",
  googleClientId: process.env.GOOGLE_CLIENT_ID,
  googleClientSecret: process.env.GOOGLE_CLIENT_SECRET,
  googleOAuthRedirectUri: process.env.GOOGLE_OAUTH_REDIRECT_URI,
  imageProvider: process.env.IMAGE_PROVIDER ?? "ark",
  enableOpenAiImage: parseBoolean(process.env.ENABLE_OPENAI_IMAGE, false),
  openAiApiKey: process.env.OPENAI_API_KEY,
  openAiImageModel: process.env.OPENAI_IMAGE_MODEL ?? "gpt-image-2",
  arkApiKey: process.env.ARK_API_KEY,
  arkBaseUrl: process.env.ARK_BASE_URL ?? "https://ark.cn-beijing.volces.com/api/v3",
  arkImageModel: process.env.ARK_IMAGE_MODEL ?? "doubao-seedream-5-0-260128",
  arkImageSize: process.env.ARK_IMAGE_SIZE ?? "2K",
  arkWatermark: parseBoolean(process.env.ARK_WATERMARK, true),
  visionProvider: process.env.VISION_PROVIDER ?? "ark",
  arkVisionModel: process.env.ARK_VISION_MODEL ?? "doubao-seed-1-6-vision-250815",
  uploadDir: "server/storage/uploads",
  generatedDir: "server/storage/generated"
};
