const { uploadStyleTask } = require("../../utils/api");

const scenes = [
  { label: "日常", value: "daily" },
  { label: "通勤", value: "commute" },
  { label: "约会", value: "date" },
  { label: "旅行", value: "travel" },
  { label: "聚会", value: "party" }
];

const budgets = [
  { label: "300以内", min: 0, max: 300 },
  { label: "300-800", min: 300, max: 800 },
  { label: "800以上", min: 800, max: 2000 }
];

const analysisFeatures = [
  { icon: "身", label: "身形", value: "梨形" },
  { icon: "高", label: "身高", value: "168cm" },
  { icon: "肤", label: "肤色", value: "暖白皮" },
  { icon: "发", label: "发色", value: "深棕色" },
  { icon: "调", label: "风格关键词", value: "清新 · 优雅 · 简约" }
];

const looks = [
  { title: "浅色温柔通勤", tone: "soft" },
  { title: "黑白极简气质", tone: "black" },
  { title: "蓝调清爽出街", tone: "blue" },
  { title: "奶油系约会", tone: "cream" }
];

const tabs = [
  { label: "首页", icon: "⌂" },
  { label: "灵感", icon: "☆" },
  { label: "衣橱", icon: "□" },
  { label: "我的", icon: "○" }
];

Page({
  data: {
    scenes,
    budgets,
    analysisFeatures,
    looks,
    tabs,
    budgetIndex: 1,
    photoPath: "",
    submitting: false,
    form: {
      scene: "daily",
      budgetMin: 300,
      budgetMax: 800,
      ageYears: "",
      heightCm: "",
      weightKg: "",
      usualSize: "",
      likedStyle: "",
      avoid: ""
    }
  },

  choosePhoto() {
    wx.chooseMedia({
      count: 1,
      mediaType: ["image"],
      sourceType: ["album", "camera"],
      sizeType: ["compressed"],
      success: (res) => {
        const file = res.tempFiles[0];
        if (!file) return;
        if (file.size > 8 * 1024 * 1024) {
          wx.showToast({ title: "图片需小于 8MB", icon: "none" });
          return;
        }
        this.setData({ photoPath: file.tempFilePath });
      }
    });
  },

  selectScene(event) {
    this.setData({
      "form.scene": event.currentTarget.dataset.value
    });
  },

  selectBudget(event) {
    const index = Number(event.currentTarget.dataset.index);
    const budget = budgets[index];
    this.setData({
      budgetIndex: index,
      "form.budgetMin": budget.min,
      "form.budgetMax": budget.max
    });
  },

  onInput(event) {
    const key = event.currentTarget.dataset.key;
    this.setData({
      [`form.${key}`]: event.detail.value
    });
  },

  async submitTask() {
    if (!this.data.photoPath || this.data.submitting) return;
    this.setData({ submitting: true });
    try {
      const formData = {};
      Object.keys(this.data.form).forEach((key) => {
        const value = this.data.form[key];
        if (value !== "" && value !== null && value !== undefined) {
          formData[key] = String(value);
        }
      });
      const result = await uploadStyleTask({
        filePath: this.data.photoPath,
        formData
      });
      wx.navigateTo({
        url: `/pages/progress/index?taskId=${result.taskId}`
      });
    } catch (error) {
      wx.showToast({
        title: "创建任务失败",
        icon: "none"
      });
    } finally {
      this.setData({ submitting: false });
    }
  }
});
