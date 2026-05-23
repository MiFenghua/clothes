import type { StyleTaskInput, UserStyleProfile } from "../domain/types.js";
import type { PhotoAnalysisProvider } from "./photoAnalysisProvider.js";
import { LocalPhotoAnalysisProvider } from "./localPhotoAnalysisProvider.js";

export class PhotoAnalyst {
  private readonly fallback = new LocalPhotoAnalysisProvider();

  constructor(private readonly provider: PhotoAnalysisProvider = new LocalPhotoAnalysisProvider()) {}

  async analyze(input: StyleTaskInput): Promise<UserStyleProfile> {
    try {
      return await this.provider.analyze(input);
    } catch {
      return this.fallback.analyze(input);
    }
  }
}
