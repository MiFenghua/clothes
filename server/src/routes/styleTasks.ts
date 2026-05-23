import fs from "node:fs";
import path from "node:path";
import type { Router } from "express";
import express from "express";
import multer from "multer";
import { z } from "zod";
import { getCurrentUser } from "../auth/currentUser.js";
import { config } from "../config.js";
import type { Scene, StyleTaskInput } from "../domain/types.js";
import type { Orchestrator } from "../services/orchestrator.js";
import type { TaskStore } from "../services/taskStore.js";
import { AppError, sendError } from "../utils/http.js";

const sceneValues = ["daily", "commute", "date", "travel", "party"] as const;

const emptyStringToUndefined = (value: unknown) => (value === "" ? undefined : value);
const optionalNumber = () => z.preprocess(emptyStringToUndefined, z.coerce.number().optional());
const optionalBoundedNumber = (min: number, max: number) =>
  z.preprocess(emptyStringToUndefined, z.coerce.number().min(min).max(max).optional());

const createTaskSchema = z.object({
  scene: z.enum(sceneValues).default("daily"),
  budgetMin: optionalNumber(),
  budgetMax: optionalNumber(),
  ageYears: optionalBoundedNumber(12, 90),
  heightCm: optionalBoundedNumber(100, 230),
  weightKg: optionalBoundedNumber(25, 200),
  usualSize: z.string().trim().max(20).optional(),
  likedStyle: z.string().trim().max(120).optional(),
  avoid: z.string().trim().max(120).optional()
});

const ensureUploadDir = () => {
  fs.mkdirSync(config.uploadDir, { recursive: true });
};

const upload = multer({
  storage: multer.diskStorage({
    destination: (_req, _file, cb) => {
      ensureUploadDir();
      cb(null, config.uploadDir);
    },
    filename: (_req, file, cb) => {
      const ext = path.extname(file.originalname).toLowerCase() || ".jpg";
      cb(null, `${Date.now()}-${Math.round(Math.random() * 1e9)}${ext}`);
    }
  }),
  limits: {
    fileSize: 8 * 1024 * 1024
  },
  fileFilter: (_req, file, cb) => {
    const isAllowed = ["image/jpeg", "image/png", "image/webp"].includes(file.mimetype);
    if (!isAllowed) {
      cb(new AppError(400, "UNSUPPORTED_IMAGE_TYPE", "Only JPG, PNG and WEBP images are supported"));
      return;
    }
    cb(null, true);
  }
});

function normalizeInput(file: Express.Multer.File, fields: z.infer<typeof createTaskSchema>): StyleTaskInput {
  return {
    photoPath: file.path,
    photoUrl: `${config.publicBaseUrl}/uploads/${path.basename(file.path)}`,
    scene: fields.scene as Scene,
    budget: {
      min: fields.budgetMin ?? null,
      max: fields.budgetMax ?? null
    },
    ageYears: fields.ageYears ?? null,
    heightCm: fields.heightCm ?? null,
    weightKg: fields.weightKg ?? null,
    usualSize: fields.usualSize || null,
    likedStyle: fields.likedStyle || null,
    avoid: fields.avoid || null
  };
}

export function createStyleTaskRouter(store: TaskStore, orchestrator: Orchestrator): Router {
  const router = express.Router();

  router.post("/", upload.single("photo"), async (req, res) => {
    try {
      if (!req.file) {
        throw new AppError(400, "PHOTO_REQUIRED", "Photo is required");
      }

      const user = getCurrentUser(req);
      const fields = createTaskSchema.parse(req.body);
      const task = store.create(normalizeInput(req.file, fields), user?.userId ?? null);

      void orchestrator.run(task.taskId);

      res.status(201).json({
        taskId: task.taskId,
        status: task.status
      });
    } catch (error) {
      sendError(res, error);
    }
  });

  router.get("/:taskId", (req, res) => {
    try {
      const user = getCurrentUser(req);
      res.json(store.toProgressView(req.params.taskId, user?.userId ?? null));
    } catch (error) {
      sendError(res, error);
    }
  });

  router.get("/:taskId/result", (req, res) => {
    try {
      const user = getCurrentUser(req);
      const task = store.getForUser(req.params.taskId, user?.userId ?? null);
      if (task.status === "failed") {
        return res.json({
          taskId: task.taskId,
          status: "failed",
          errorCode: task.error?.errorCode,
          userMessage: task.error?.userMessage
        });
      }

      if (task.status !== "succeeded" || !task.result) {
        throw new AppError(409, "TASK_NOT_READY", "Task result is not ready");
      }

      res.json(task.result);
    } catch (error) {
      sendError(res, error);
    }
  });

  return router;
}
