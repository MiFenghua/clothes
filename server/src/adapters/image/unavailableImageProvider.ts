import type { TryOnImageProvider } from "./imageProvider.js";

export class UnavailableImageProvider implements TryOnImageProvider {
  async generate(): Promise<never> {
    throw new Error("OpenAI image generation is not enabled");
  }
}
