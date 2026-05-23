import type { StyleTaskInput, UserStyleProfile } from "../domain/types.js";
import type { PhotoAnalysisProvider } from "./photoAnalysisProvider.js";

export class LocalPhotoAnalysisProvider implements PhotoAnalysisProvider {
  async analyze(input: StyleTaskInput): Promise<UserStyleProfile> {
    const ageStyleWords = this.ageStyleWords(input.ageYears);
    const preferredPalette = input.likedStyle?.includes("温柔")
      ? ["ivory", "misty pink", "denim", "silver"]
      : ["ivory", "denim", "navy", "silver"];

    return {
      bodyProportion: "balanced",
      heightImpression: input.heightCm && input.heightCm < 160 ? "petite" : "average",
      undertone: "neutral",
      hairTone: "dark",
      currentStyle: ["clean", "casual"],
      fitAdvice: ["提高腰线", "选择纵向线条", "避免过长无腰线外套"],
      palette: preferredPalette,
      occasionFit: ["daily", "commute"],
      confidence: 0.68,
      photoQuality: {
        isFullBody: true,
        faceVisible: true,
        lighting: "good",
        occlusion: "low"
      },
      summary: "适合干净利落、显比例的城市日常造型。",
      recommendedOutfitStrategy: {
        outfitTheme: input.scene === "date" ? "图片理解约会穿搭" : "图片理解日常穿搭",
        styleDirection: input.likedStyle ? input.likedStyle.split(/[，,、\s]+/).filter(Boolean) : ["干净", "显比例", ...ageStyleWords],
        requiredCategories: input.scene === "date" ? ["dress", "shoes", "bag"] : ["top", "bottom", "shoes", "bag"],
        colorDirection: preferredPalette,
        fitDirection: ["高腰线", "线条干净"],
        searchQueries:
          input.scene === "date"
            ? [
                `收腰连衣裙 女 约会 显比例 ${ageStyleWords.join(" ")}`.trim(),
                `浅口低跟单鞋 女 约会 ${ageStyleWords[0] ?? ""}`.trim(),
                `小方包 女 精致 ${ageStyleWords[0] ?? ""}`.trim()
              ]
            : [
                `短款上衣 女 显比例 ${ageStyleWords.join(" ")}`.trim(),
                "高腰直筒裤 女",
                "低跟单鞋 女 百搭",
                "小包 女 简约"
              ],
        avoidQueries: input.avoid ? input.avoid.split(/[，,、\s]+/).filter(Boolean) : []
      }
    };
  }

  private ageStyleWords(ageYears: number | null) {
    if (!ageYears) return [];
    if (ageYears < 24) return ["清爽", "轻甜"];
    if (ageYears < 35) return ["轻熟", "精致"];
    if (ageYears < 50) return ["质感", "优雅"];
    return ["成熟优雅", "舒适质感"];
  }
}
