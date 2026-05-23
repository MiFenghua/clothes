import { nanoid } from "nanoid";
import type { StyleTask, StyleTaskInput, TaskError, TaskProgressView, TaskStatus } from "../domain/types.js";
import { AppError } from "../utils/http.js";

const statusProgress: Record<TaskStatus, { progress: number; message: string }> = {
  created: { progress: 2, message: "任务已创建" },
  photo_uploaded: { progress: 8, message: "照片已上传" },
  validating_photo: { progress: 14, message: "正在校验照片质量" },
  analyzing_photo: { progress: 24, message: "正在分析照片特征" },
  profile_ready: { progress: 34, message: "照片画像已生成" },
  planning_outfit: { progress: 42, message: "正在生成搭配策略" },
  searching_products: { progress: 54, message: "正在搜索适合你的商品" },
  parsing_products: { progress: 64, message: "正在整理商品信息" },
  building_outfit: { progress: 74, message: "正在组合最佳穿搭" },
  outfit_ready: { progress: 82, message: "穿搭方案已生成" },
  generating_image: { progress: 90, message: "正在生成试穿效果图" },
  quality_checking: { progress: 96, message: "正在检查试穿效果图" },
  succeeded: { progress: 100, message: "搭配完成" },
  failed: { progress: 100, message: "生成失败" }
};

export class TaskStore {
  private readonly tasks = new Map<string, StyleTask>();

  create(input: StyleTaskInput, userId: string | null = null) {
    const now = new Date().toISOString();
    const taskId = `task_${nanoid(12)}`;
    const initial = statusProgress.created;
    const task: StyleTask = {
      taskId,
      userId,
      status: "created",
      progress: initial.progress,
      message: initial.message,
      createdAt: now,
      updatedAt: now,
      input,
      error: null
    };

    this.tasks.set(taskId, task);
    return task;
  }

  get(taskId: string) {
    const task = this.tasks.get(taskId);
    if (!task) {
      throw new AppError(404, "TASK_NOT_FOUND", "Task not found");
    }
    return task;
  }

  getForUser(taskId: string, userId: string | null) {
    const task = this.get(taskId);
    if (task.userId && task.userId !== userId) {
      throw new AppError(404, "TASK_NOT_FOUND", "Task not found");
    }
    return task;
  }

  setStatus(taskId: string, status: TaskStatus) {
    const task = this.get(taskId);
    const progress = statusProgress[status];
    task.status = status;
    task.progress = progress.progress;
    task.message = progress.message;
    task.updatedAt = new Date().toISOString();
    return task;
  }

  patch(taskId: string, patch: Partial<StyleTask>) {
    const task = this.get(taskId);
    Object.assign(task, patch, { updatedAt: new Date().toISOString() });
    return task;
  }

  fail(taskId: string, error: TaskError) {
    const task = this.setStatus(taskId, "failed");
    task.error = error;
    task.message = error.userMessage;
    task.updatedAt = new Date().toISOString();
    return task;
  }

  toProgressView(taskId: string, userId: string | null = null): TaskProgressView {
    const task = this.getForUser(taskId, userId);
    return {
      taskId: task.taskId,
      status: task.status,
      progress: task.progress,
      message: task.message,
      errorCode: task.error?.errorCode,
      userMessage: task.error?.userMessage
    };
  }
}

export const taskStore = new TaskStore();
