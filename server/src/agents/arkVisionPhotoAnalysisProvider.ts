import { readFile } from "node:fs/promises";
import path from "node:path";
import OpenAI from "openai";
import { z } from "zod";
import { config } from "../config.js";
import type { Scene, StyleTaskInput, UserStyleProfile } from "../domain/types.js";
import type { PhotoAnalysisProvider } from "./photoAnalysisProvider.js";

const categorySchema = z.enum(["top", "bottom", "dress", "outerwear", "shoes", "bag", "accessory"]);

const outfitStrategySchema = z.object({
  outfitTheme: z.string().min(2).max(60),
  styleDirection: z.array(z.string()).default([]),
  requiredCategories: z.array(categorySchema).min(2).max(5),
  colorDirection: z.array(z.string()).default([]),
  fitDirection: z.array(z.string()).default([]),
  searchQueries: z.array(z.string().min(2).max(80)).min(2).max(8),
  avoidQueries: z.array(z.string()).default([])
});

const profileSchema = z.object({
  bodyProportion: z.enum(["petite", "balanced", "tall", "curvy", "straight"]),
  heightImpression: z.enum(["petite", "average", "tall"]),
  undertone: z.enum(["warm", "cool", "neutral"]),
  hairTone: z.enum(["dark", "brown", "light", "red", "covered"]),
  currentStyle: z.array(z.string()).default([]),
  fitAdvice: z.array(z.string()).default([]),
  palette: z.array(z.string()).default([]),
  occasionFit: z.array(z.enum(["daily", "commute", "date", "travel", "party"])).default(["daily"]),
  confidence: z.number().min(0).max(1).default(0.6),
  photoQuality: z.object({
    isFullBody: z.boolean(),
    faceVisible: z.boolean(),
    lighting: z.enum(["poor", "fair", "good"]),
    occlusion: z.enum(["low", "medium", "high"])
  }),
  summary: z.string(),
  recommendedOutfitStrategy: outfitStrategySchema.optional().catch(undefined)
});

export class ArkVisionPhotoAnalysisProvider implements PhotoAnalysisProvider {
  private readonly client: OpenAI;

  constructor(apiKey: string) {
    this.client = new OpenAI({
      apiKey,
      baseURL: config.arkBaseUrl
    });
  }

  async analyze(input: StyleTaskInput): Promise<UserStyleProfile> {
    const response = await this.client.responses.create({
      model: config.arkVisionModel,
      input: [
        {
          role: "user",
          content: [
            {
              type: "input_image",
              image_url: await this.getImageReference(input.photoPath, input.photoUrl)
            },
            {
              type: "input_text",
              text: this.buildPrompt(input)
            }
          ]
        }
      ]
    } as never);

    const text = this.extractOutputText(response);
    const parsedJson = this.parseJson(text);
    const profile = profileSchema.parse(parsedJson);

    return {
      ...profile,
      summary: profile.summary.slice(0, 80),
      occasionFit: profile.occasionFit as Scene[],
      recommendedOutfitStrategy: profile.recommendedOutfitStrategy
    };
  }

  private buildPrompt(input: StyleTaskInput) {
    return `你是一名专业但克制的女性穿搭顾问。
请只基于照片中可见的造型相关信息进行分析。
不要推断年龄、民族、身份、健康状况、收入或体重数值。
如果用户没有填写年龄，不要从照片推断年龄。
如果用户填写了年龄，只把它用于选择年龄适宜的风格成熟度、单品和穿着场合，不要评价年龄本身。
不要使用贬低身体的表达。

用户补充信息：
- 场景：${input.scene}
- 预算：${input.budget.min ?? "未填"}-${input.budget.max ?? "未填"}
- 用户填写年龄：${input.ageYears ?? "未填"}
- 身高：${input.heightCm ?? "未填"}
- 体重：不需要推断或评价
- 常穿尺码：${input.usualSize ?? "未填"}
- 喜欢风格：${input.likedStyle ?? "未填"}
- 避雷项：${input.avoid ?? "未填"}

请同时基于图片理解结果直接产出电商搜索关键词，不要使用固定模板。
关键词要求：
- 必须贴合照片里可见的体态比例、当前风格、发色/肤色冷暖、适合的颜色和用户场景。
- 搜索词用于 Amazon/淘宝等电商检索，应是中文商品关键词，不要写品牌名。
- 每条搜索词要包含品类、性别、场景/风格、关键版型或颜色，例如“雾粉收腰茶歇连衣裙 女 约会 显比例”。
- 如果用户填写年龄，可把年龄转化成“清爽、学院感、轻熟、成熟优雅、质感”等风格成熟度；不要在搜索词里写具体年龄数字。
- requiredCategories 必须能组成完整穿搭：要么包含 dress，要么同时包含 top 和 bottom；可再加入 shoes、bag、outerwear 或 accessory。
- searchQueries 要和 requiredCategories 对应，数量 3-5 条优先。
- 如果用户填写了喜欢风格或避雷项，要体现在关键词或 avoidQueries 中。

请输出严格 JSON，不要输出 Markdown，不要输出额外解释。结构如下：
{
  "bodyProportion": "petite | balanced | tall | curvy | straight",
  "heightImpression": "petite | average | tall",
  "undertone": "warm | cool | neutral",
  "hairTone": "dark | brown | light | red | covered",
  "currentStyle": ["中文关键词"],
  "fitAdvice": ["中文建议"],
  "palette": ["ivory", "denim"],
  "occasionFit": ["daily", "commute"],
  "confidence": 0.0,
  "photoQuality": {
    "isFullBody": true,
    "faceVisible": true,
    "lighting": "poor | fair | good",
    "occlusion": "low | medium | high"
  },
  "summary": "不超过80字中文总结",
  "recommendedOutfitStrategy": {
    "outfitTheme": "不超过20字中文穿搭主题",
    "styleDirection": ["由图片理解得出的中文风格关键词"],
    "requiredCategories": ["dress", "shoes", "bag"],
    "colorDirection": ["ivory", "misty pink"],
    "fitDirection": ["收腰", "高腰线"],
    "searchQueries": [
      "雾粉收腰茶歇连衣裙 女 约会 显比例",
      "浅口低跟单鞋 女 约会 温柔",
      "珍珠链条小方包 女 精致"
    ],
    "avoidQueries": ["用户明确避雷的关键词"]
  }
}`;
  }

  private async getImageReference(photoPath: string, photoUrl: string) {
    if (!this.isLocalPublicUrl(photoUrl)) {
      return photoUrl;
    }

    const buffer = await readFile(photoPath);
    return `data:${this.mimeTypeFromPath(photoPath)};base64,${buffer.toString("base64")}`;
  }

  private isLocalPublicUrl(url: string) {
    return /^https?:\/\/(127\.0\.0\.1|localhost|\[::1\])(?::\d+)?\//i.test(url);
  }

  private mimeTypeFromPath(filePath: string) {
    const ext = path.extname(filePath).toLowerCase();
    if (ext === ".png") return "image/png";
    if (ext === ".webp") return "image/webp";
    return "image/jpeg";
  }

  private extractOutputText(response: unknown) {
    const outputText = (response as { output_text?: string }).output_text;
    if (outputText) return outputText;

    const output = (response as { output?: Array<{ content?: Array<{ text?: string; type?: string }> }> }).output;
    const text = output
      ?.flatMap((item) => item.content ?? [])
      .map((content) => content.text)
      .filter(Boolean)
      .join("\n");

    if (!text) {
      throw new Error("Ark vision response did not include output text");
    }

    return text;
  }

  private parseJson(text: string) {
    const trimmed = text.trim();
    try {
      return JSON.parse(trimmed);
    } catch {
      const match = /```(?:json)?\s*([\s\S]*?)```/i.exec(trimmed) ?? /(\{[\s\S]*\})/.exec(trimmed);
      if (!match) throw new Error("Ark vision response is not JSON");
      return JSON.parse(match[1]);
    }
  }
}
