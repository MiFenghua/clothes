import type { Outfit, StyleTaskInput } from "../../domain/types.js";

export interface TryOnImageProvider {
  generate(input: {
    taskId: string;
    taskInput: StyleTaskInput;
    outfit: Outfit;
    prompt: string;
  }): Promise<{
    imageUrl: string;
    qc: {
      passed: boolean;
      score: number;
    };
  }>;
}
