import type { Router } from "express";
import express from "express";
import { z } from "zod";
import { getLastSearchIssue, type SearchProvider } from "../adapters/search/searchProvider.js";
import { DemoSearchProvider } from "../adapters/search/demoSearchProvider.js";
import type { TryOnImageProvider } from "../adapters/image/imageProvider.js";
import type { OutfitStrategy } from "../domain/types.js";
import { ImageDirector } from "../agents/imageDirector.js";
import { AppError, sendError } from "../utils/http.js";

const searchSchema = z.object({
  queries: z.array(z.string()).min(1),
  budget: z
    .object({
      min: z.number().nullable().optional(),
      max: z.number().nullable().optional()
    })
    .default({}),
  limitPerQuery: z.number().int().min(1).max(50).default(20)
});

const generateTryOnSchema = z.object({
  taskId: z.string(),
  userPhotoUrl: z.string(),
  productImageUrls: z.array(z.string()),
  outfitPrompt: z.string()
});

export function createInternalRouter(searchProvider: SearchProvider, imageProvider: TryOnImageProvider): Router {
  const router = express.Router();

  router.post("/search-products", async (req, res) => {
    try {
      const body = searchSchema.parse(req.body);
      const strategy: OutfitStrategy = {
        outfitTheme: "内部搜索",
        styleDirection: body.queries,
        requiredCategories: ["top", "bottom", "shoes", "bag"],
        colorDirection: [],
        fitDirection: [],
        searchQueries: body.queries,
        avoidQueries: []
      };
      const products = await searchProvider.search({
        strategy,
        budget: {
          min: body.budget.min ?? null,
          max: body.budget.max ?? null
        },
        limitPerQuery: body.limitPerQuery
      });

      res.json({ products, searchIssue: getLastSearchIssue(searchProvider) });
    } catch (error) {
      sendError(res, error);
    }
  });

  router.post("/generate-try-on", async (req, res) => {
    try {
      const body = generateTryOnSchema.parse(req.body);
      const demoProvider = new DemoSearchProvider();
      const products = await demoProvider.search({
        strategy: {
          outfitTheme: "内部试穿",
          styleDirection: [],
          requiredCategories: ["top", "bottom"],
          colorDirection: [],
          fitDirection: [],
          searchQueries: [],
          avoidQueries: []
        },
        budget: { min: null, max: null },
        limitPerQuery: 2
      });
      const outfit = {
        title: "内部试穿",
        reason: body.outfitPrompt,
        items: products.slice(0, 2).map((product) => ({ ...product, matchReason: "内部接口参考商品" })),
        totalPrice: products.slice(0, 2).reduce((sum, product) => sum + product.price, 0),
        tryOnDescription: body.outfitPrompt
      };
      const prompt = new ImageDirector().buildPrompt(outfit);
      const result = await imageProvider.generate({
        taskId: body.taskId,
        taskInput: {
          photoUrl: body.userPhotoUrl,
          photoPath: body.userPhotoUrl,
          scene: "daily",
          budget: { min: null, max: null },
          ageYears: null,
          heightCm: null,
          weightKg: null,
          usualSize: null,
          likedStyle: null,
          avoid: null
        },
        outfit,
        prompt
      });
      res.json(result);
    } catch (error) {
      if (error instanceof Error && error.message.includes("not enabled")) {
        return sendError(res, new AppError(503, "IMAGE_PROVIDER_UNAVAILABLE", "Image generation provider is not enabled"));
      }
      sendError(res, error);
    }
  });

  return router;
}
