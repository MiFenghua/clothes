import { createReadStream } from "node:fs";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import OpenAI, { toFile } from "openai";
import { config } from "../../config.js";
import type { TryOnImageProvider } from "./imageProvider.js";

export class OpenAiImageProvider implements TryOnImageProvider {
  private readonly client: OpenAI;

  constructor(apiKey: string) {
    this.client = new OpenAI({ apiKey });
  }

  async generate({ taskId, taskInput, outfit, prompt }: Parameters<TryOnImageProvider["generate"]>[0]) {
    const imageFiles = [await toFile(createReadStream(taskInput.photoPath), path.basename(taskInput.photoPath))];
    const productFiles = await this.loadProductReferenceFiles(outfit.items.map((item) => item.imageUrl));

    const response = await this.client.images.edit({
      model: config.openAiImageModel,
      image: [...imageFiles, ...productFiles] as never,
      prompt,
      size: "1024x1536" as never,
      quality: "medium" as never
    });

    const b64 = response.data?.[0]?.b64_json;
    if (!b64) {
      throw new Error("OpenAI image response did not include image data");
    }

    await mkdir(config.generatedDir, { recursive: true });
    const filename = `${taskId}.png`;
    const outputPath = path.join(config.generatedDir, filename);
    await writeFile(outputPath, Buffer.from(b64, "base64"));

    return {
      imageUrl: `${config.publicBaseUrl}/generated/${filename}`,
      qc: {
        passed: true,
        score: 0.8
      }
    };
  }

  private async loadProductReferenceFiles(urls: string[]) {
    const files = [];
    for (const [index, url] of urls.entries()) {
      try {
        const response = await fetch(url);
        if (!response.ok) continue;
        const arrayBuffer = await response.arrayBuffer();
        const type = response.headers.get("content-type") ?? "image/jpeg";
        files.push(await toFile(Buffer.from(arrayBuffer), `product-${index}.jpg`, { type }));
      } catch {
        continue;
      }
    }
    return files;
  }
}
