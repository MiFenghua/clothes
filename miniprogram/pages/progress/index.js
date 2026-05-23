const { request } = require("../../utils/api");

const stepConfig = [
  {
    status: "analyzing_photo",
    title: "分析照片特征",
    desc: "提取造型相关信息"
  },
  {
    status: "searching_products",
    title: "搜索淘宝商品",
    desc: "整理候选商品"
  },
  {
    status: "building_outfit",
    title: "组合最佳穿搭",
    desc: "只输出一套方案"
  },
  {
    status: "generating_image",
    title: "生成试穿效果图",
    desc: "保留本人特征与完整人物"
  }
];

const statusOrder = [
  "created",
  "photo_uploaded",
  "validating_photo",
  "analyzing_photo",
  "profile_ready",
  "planning_outfit",
  "searching_products",
  "parsing_products",
  "building_outfit",
  "outfit_ready",
  "generating_image",
  "quality_checking",
  "succeeded"
];

Page({
  data: {
    taskId: "",
    progress: 0,
    message: "任务已创建",
    steps: stepConfig.map((step) => ({ ...step, state: "" }))
  },

  onLoad(options) {
    this.setData({ taskId: options.taskId });
    this.poll();
  },

  onUnload() {
    if (this.timer) clearTimeout(this.timer);
  },

  goHome() {
    wx.reLaunch({
      url: "/pages/index/index"
    });
  },

  async poll() {
    if (!this.data.taskId) return;
    try {
      const task = await request({
        url: `/api/v1/style-tasks/${this.data.taskId}`
      });
      this.setData({
        progress: task.progress,
        message: task.userMessage || task.message,
        steps: this.buildSteps(task.status)
      });

      if (task.status === "succeeded") {
        wx.redirectTo({
          url: `/pages/result/index?taskId=${this.data.taskId}`
        });
        return;
      }

      if (task.status === "failed") {
        wx.redirectTo({
          url: `/pages/error/index?taskId=${this.data.taskId}&message=${encodeURIComponent(task.userMessage || "生成失败")}`
        });
        return;
      }
    } catch (error) {
      this.setData({ message: "网络请求失败，请稍后重试" });
    }

    this.timer = setTimeout(() => this.poll(), 1500);
  },

  buildSteps(status) {
    const currentIndex = statusOrder.indexOf(status);
    return stepConfig.map((step) => {
      const stepIndex = statusOrder.indexOf(step.status);
      let state = "";
      if (currentIndex > stepIndex) state = "done";
      if (currentIndex === stepIndex) state = "active";
      return { ...step, state };
    });
  }
});
