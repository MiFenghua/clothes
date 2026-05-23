import { readFile } from "node:fs/promises";
import path from "node:path";
import OpenAI from "openai";
import { config } from "../../config.js";
import type { TryOnImageProvider } from "./imageProvider.js";

export class ArkSeedreamImageProvider implements TryOnImageProvider {
  private readonly client: OpenAI;

  constructor(apiKey: string) {
    this.client = new OpenAI({
      apiKey,
      baseURL: config.arkBaseUrl
    });
  }

  async generate({ taskInput, outfit, prompt }: Parameters<TryOnImageProvider["generate"]>[0]) {
    const referenceImages = await this.buildReferenceImages(taskInput.photoPath, taskInput.photoUrl, outfit.items.map((item) => item.imageUrl));

    const response = await this.client.images.generate({
      model: config.arkImageModel,
      prompt: this.buildArkPrompt(prompt, outfit),
      image: referenceImages,
      size: config.arkImageSize as never,
      response_format: "url",
      watermark: config.arkWatermark
    } as never);

    const imageUrl = response.data?.[0]?.url;
    if (!imageUrl) {
      throw new Error("Ark image response did not include image URL");
    }

    return {
      imageUrl,
      qc: {
        passed: true,
        score: 0.75
      }
    };
  }

  private buildArkPrompt(basePrompt: string, outfit: Parameters<TryOnImageProvider["generate"]>[0]["outfit"]) {
    const productRefs = outfit.items
      .map((item, index) => {
        const sourceLabel =
          item.platform === "amazon" ? "Amazon 商品图" : item.platform === "tmall" ? "天猫商品图" : item.platform === "taobao" ? "淘宝商品图" : "商品图";
        return `${index + 1}. ${item.category}｜${item.title}｜${sourceLabel}：${item.imageUrl}｜商品链接：${item.productUrl}｜搭配理由：${item.matchReason}`;
      })
      .join("\n");

    return `${basePrompt}

输入参考图说明：
第 1 张参考图是用户本人全身照，需要保留人物身份、脸部特征、发型、肤色、身材比例和整体体态。
第 2 张及之后参考图是选中的电商商品图，需要作为服装颜色、廓形、材质和细节参考。

请严格参考以下商品信息生成穿搭，不要自行替换服装品类、颜色和廓形：
${productRefs}

输出要求：
真实时装试穿预览，完整人物，全身构图，干净光线，质感真实。
服装必须来自上面的商品参考，尽量保持商品颜色、轮廓、材质和主要细节。
不要添加未列出的额外服装，不要过度性感化，不要改变人物年龄、体型和面部身份。`;
  }

  private async buildReferenceImages(photoPath: string, photoUrl: string, productImageUrls: string[]) {
    const userPhotoReference = this.isLocalPublicUrl(photoUrl)
      ? await this.fileToDataUrl(photoPath)
      : photoUrl;

    return [userPhotoReference, ...productImageUrls].slice(0, 15);
  }

  private isLocalPublicUrl(url: string) {
    return /^https?:\/\/(127\.0\.0\.1|localhost|\[::1\])(?::\d+)?\//i.test(url);
  }

  private async fileToDataUrl(filePath: string) {
    const buffer = await readFile(filePath);
    const mimeType = this.mimeTypeFromPath(filePath);
    return `data:${mimeType};base64,${buffer.toString("base64")}`;
  }

  private mimeTypeFromPath(filePath: string) {
    const ext = path.extname(filePath).toLowerCase();
    if (ext === ".png") return "image/png";
    if (ext === ".webp") return "image/webp";
    return "image/jpeg";
  }
}
