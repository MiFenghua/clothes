import type { Router } from "express";
import express from "express";
import { z } from "zod";
import { sendError } from "../utils/http.js";

const copyEventSchema = z.object({
  taskId: z.string(),
  productId: z.string()
});

const copyEvents: Array<{ taskId: string; productId: string; createdAt: string }> = [];

export function createEventsRouter(): Router {
  const router = express.Router();

  router.post("/copy-product-link", (req, res) => {
    try {
      const event = copyEventSchema.parse(req.body);
      copyEvents.push({
        ...event,
        createdAt: new Date().toISOString()
      });

      res.status(202).json({ ok: true });
    } catch (error) {
      sendError(res, error);
    }
  });

  return router;
}
