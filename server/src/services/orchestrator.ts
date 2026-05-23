import { existsSync, statSync } from "node:fs";
import type { ErrorCode, OutfitResult } from "../domain/types.js";
import { getTryOnProductValidationMessage } from "../domain/productRules.js";
import { ImageDirector } from "../agents/imageDirector.js";
import { OutfitBuilder } from "../agents/outfitBuilder.js";
import { PhotoAnalyst } from "../agents/photoAnalyst.js";
import { StylistAgent } from "../agents/stylistAgent.js";
import type { TryOnImageProvider } from "../adapters/image/imageProvider.js";
import { getLastSearchIssue, type SearchProvider } from "../adapters/search/searchProvider.js";
import type { TaskStore } from "./taskStore.js";

class TaskFailure extends Error {
  constructor(
    public readonly errorCode: ErrorCode,
    public readonly userMessage: string,
    internalMessage?: string
  ) {
    super(internalMessage ?? userMessage);
  }
}

const userMessages: Record<ErrorCode, string> = {
  PHOTO_INVALID: "请上传一张清晰的全身照。",
  PHOTO_NOT_FULL_BODY: "照片需要尽量包含完整身体。",
  SEARCH_EMPTY: "暂时没有找到合适商品，请稍后重试。",
  SCRAPE_BLOCKED: "商品搜索失败，请稍后重试。",
  OUTFIT_BUILD_FAILED: "暂时没有生成合适穿搭，请稍后重试。",
  IMAGE_GENERATION_FAILED: "本次试穿图生成失败，请换一张更清晰的全身照后重试。",
  QUALITY_CHECK_FAILED: "本次试穿图生成失败，请换一张更清晰的全身照后重试。",
  TIMEOUT: "生成超时，请稍后重试。"
};

export class Orchestrator {
  constructor(
    private readonly store: TaskStore,
    private readonly photoAnalyst: PhotoAnalyst,
    private readonly stylistAgent: StylistAgent,
    private readonly searchProvider: SearchProvider,
    private readonly outfitBuilder: OutfitBuilder,
    private readonly imageDirector: ImageDirector,
    private readonly imageProvider: TryOnImageProvider
  ) {}

  async run(taskId: string) {
    try {
      const task = this.store.get(taskId);

      this.store.setStatus(taskId, "photo_uploaded");
      this.store.setStatus(taskId, "validating_photo");
      this.validatePhoto(task.input.photoPath);

      this.store.setStatus(taskId, "analyzing_photo");
      const profile = await this.photoAnalyst.analyze(task.input);
      if (!profile.photoQuality.isFullBody) {
        throw new TaskFailure("PHOTO_NOT_FULL_BODY", userMessages.PHOTO_NOT_FULL_BODY);
      }
      this.store.patch(taskId, { profile });

      this.store.setStatus(taskId, "profile_ready");
      this.store.setStatus(taskId, "planning_outfit");
      const strategy = this.stylistAgent.plan(profile, task.input);
      this.store.patch(taskId, { strategy });

      this.store.setStatus(taskId, "searching_products");
      const products = await this.searchProvider.search({
        strategy,
        budget: task.input.budget,
        limitPerQuery: 20
      });
      if (products.length < 1) {
        throw new TaskFailure("SEARCH_EMPTY", userMessages.SEARCH_EMPTY);
      }

      this.store.setStatus(taskId, "parsing_products");
      this.store.patch(taskId, { products });

      this.store.setStatus(taskId, "building_outfit");
      let outfit;
      try {
        outfit = this.outfitBuilder.build(profile, strategy, products, task.input);
      } catch (error) {
        throw new TaskFailure("OUTFIT_BUILD_FAILED", userMessages.OUTFIT_BUILD_FAILED, String(error));
      }

      this.store.setStatus(taskId, "outfit_ready");
      const productValidationMessage = getTryOnProductValidationMessage(outfit.items);
      if (productValidationMessage) {
        const searchIssue = getLastSearchIssue(this.searchProvider);
        throw new TaskFailure(
          "OUTFIT_BUILD_FAILED",
          searchIssue?.message ?? "照片分析已完成，但暂时没有拿到可用于试穿的淘宝/天猫或 Amazon 商品详情页和商品图。",
          productValidationMessage
        );
      }

      this.store.setStatus(taskId, "generating_image");
      const prompt = this.imageDirector.buildPrompt(outfit);

      let image;
      try {
        image = await this.imageProvider.generate({
          taskId,
          taskInput: task.input,
          outfit,
          prompt
        });
      } catch (error) {
        throw new TaskFailure("IMAGE_GENERATION_FAILED", userMessages.IMAGE_GENERATION_FAILED, String(error));
      }

      this.store.setStatus(taskId, "quality_checking");
      if (!image.qc.passed) {
        throw new TaskFailure("QUALITY_CHECK_FAILED", userMessages.QUALITY_CHECK_FAILED);
      }

      const result: OutfitResult = {
        taskId,
        status: "succeeded",
        tryOnImageUrl: image.imageUrl,
        outfit
      };

      this.store.patch(taskId, { result });
      this.store.setStatus(taskId, "succeeded");
    } catch (error) {
      const failure =
        error instanceof TaskFailure
          ? error
          : new TaskFailure("TIMEOUT", userMessages.TIMEOUT, error instanceof Error ? error.message : String(error));
      this.store.fail(taskId, {
        errorCode: failure.errorCode,
        userMessage: failure.userMessage,
        internalMessage: failure.message
      });
    }
  }

  private validatePhoto(photoPath: string) {
    if (!existsSync(photoPath)) {
      throw new TaskFailure("PHOTO_INVALID", userMessages.PHOTO_INVALID, "Photo file is missing");
    }

    const stat = statSync(photoPath);
    if (stat.size <= 0 || stat.size > 8 * 1024 * 1024) {
      throw new TaskFailure("PHOTO_INVALID", userMessages.PHOTO_INVALID, "Photo file size is invalid");
    }
  }
}
