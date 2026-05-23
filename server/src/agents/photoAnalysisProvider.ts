import type { StyleTaskInput, UserStyleProfile } from "../domain/types.js";

export interface PhotoAnalysisProvider {
  analyze(input: StyleTaskInput): Promise<UserStyleProfile>;
}
