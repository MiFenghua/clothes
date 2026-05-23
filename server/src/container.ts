import { config } from "./config.js";
import { AmazonBrowserSearchProvider } from "./adapters/search/amazonBrowserSearchProvider.js";
import { DemoSearchProvider } from "./adapters/search/demoSearchProvider.js";
import { ExternalEcommerceSearchProvider } from "./adapters/search/externalEcommerceSearchProvider.js";
import { HybridSearchProvider } from "./adapters/search/hybridSearchProvider.js";
import { TaobaoBrowserSearchProvider } from "./adapters/search/taobaoBrowserSearchProvider.js";
import { ArkSeedreamImageProvider } from "./adapters/image/arkSeedreamImageProvider.js";
import { OpenAiImageProvider } from "./adapters/image/openAiImageProvider.js";
import { UnavailableImageProvider } from "./adapters/image/unavailableImageProvider.js";
import { ImageDirector } from "./agents/imageDirector.js";
import { OutfitBuilder } from "./agents/outfitBuilder.js";
import { PhotoAnalyst } from "./agents/photoAnalyst.js";
import { ArkVisionPhotoAnalysisProvider } from "./agents/arkVisionPhotoAnalysisProvider.js";
import { LocalPhotoAnalysisProvider } from "./agents/localPhotoAnalysisProvider.js";
import { StylistAgent } from "./agents/stylistAgent.js";
import { AuthStore } from "./auth/authStore.js";
import { Orchestrator } from "./services/orchestrator.js";
import { taskStore } from "./services/taskStore.js";

const demoSearchProvider = new DemoSearchProvider();
const externalSearchProvider = new ExternalEcommerceSearchProvider();
const amazonBrowserSearchProvider = new AmazonBrowserSearchProvider();
const taobaoBrowserSearchProvider = new TaobaoBrowserSearchProvider();

function createSearchProvider() {
  if (config.searchProvider === "amazon-browser") {
    return new HybridSearchProvider(amazonBrowserSearchProvider, externalSearchProvider);
  }
  if (config.searchProvider === "taobao-browser") {
    return new HybridSearchProvider(taobaoBrowserSearchProvider, externalSearchProvider);
  }
  if (config.searchProvider === "external") {
    return externalSearchProvider;
  }
  if (config.searchProvider === "demo") {
    return demoSearchProvider;
  }

  const browserSearchProvider = new HybridSearchProvider(
    new HybridSearchProvider(amazonBrowserSearchProvider, taobaoBrowserSearchProvider),
    externalSearchProvider
  );
  return config.enableDemoSearch ? new HybridSearchProvider(browserSearchProvider, demoSearchProvider) : browserSearchProvider;
}

const searchProvider = createSearchProvider();
const imageProvider =
  config.imageProvider === "ark" && config.arkApiKey
    ? new ArkSeedreamImageProvider(config.arkApiKey)
    : config.imageProvider === "openai" && config.enableOpenAiImage && config.openAiApiKey
    ? new OpenAiImageProvider(config.openAiApiKey)
    : new UnavailableImageProvider();
const photoAnalysisProvider =
  config.visionProvider === "ark" && config.arkApiKey
    ? new ArkVisionPhotoAnalysisProvider(config.arkApiKey)
    : new LocalPhotoAnalysisProvider();

export const services = {
  authStore: new AuthStore(),
  taskStore,
  searchProvider,
  imageProvider,
  orchestrator: new Orchestrator(
    taskStore,
    new PhotoAnalyst(photoAnalysisProvider),
    new StylistAgent(),
    searchProvider,
    new OutfitBuilder(),
    new ImageDirector(),
    imageProvider
  )
};
