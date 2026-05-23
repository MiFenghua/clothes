import type { Response } from "express";

export class AppError extends Error {
  constructor(
    public readonly statusCode: number,
    public readonly code: string,
    message: string
  ) {
    super(message);
  }
}

export function sendError(res: Response, error: unknown) {
  if (error instanceof AppError) {
    return res.status(error.statusCode).json({
      error: {
        code: error.code,
        message: error.message
      }
    });
  }

  const message = error instanceof Error ? error.message : "Unexpected error";
  return res.status(500).json({
    error: {
      code: "INTERNAL_SERVER_ERROR",
      message
    }
  });
}
