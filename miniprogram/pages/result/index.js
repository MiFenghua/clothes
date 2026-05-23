const { request } = require("../../utils/api");

Page({
  data: {
    taskId: "",
    matchScore: 92,
    itemsCount: 0,
    favorited: false,
    platformMap: {
      amazon: "Amazon",
      taobao: "淘宝",
      tmall: "天猫",
      jd: "京东",
      pdd: "拼多多",
      demo: "Demo"
    },
    result: {
      tryOnImageUrl: "",
      outfit: {
        title: "",
        reason: "",
        totalPrice: 0,
        items: []
      }
    }
  },

  onLoad(options) {
    this.setData({ taskId: options.taskId });
    this.loadResult();
  },

  async loadResult() {
    try {
      const result = await request({
        url: `/api/v1/style-tasks/${this.data.taskId}/result`
      });

      if (result.status === "failed") {
        wx.redirectTo({
          url: `/pages/error/index?taskId=${this.data.taskId}&message=${encodeURIComponent(result.userMessage || "生成失败")}`
        });
        return;
      }

      const items = (result.outfit && result.outfit.items) || [];
      const qcScore = result.qc && typeof result.qc.score === "number"
        ? Math.round(result.qc.score * 100)
        : 92;
      this.setData({
        result,
        matchScore: Math.max(68, Math.min(98, qcScore)),
        itemsCount: items.length
      });
    } catch (error) {
      wx.showToast({ title: "结果加载失败", icon: "none" });
    }
  },

  async copyLink(event) {
    const productId = event.currentTarget.dataset.productId;
    const url = event.currentTarget.dataset.url;
    wx.setClipboardData({
      data: url,
      success: async () => {
        try {
          await request({
            url: "/api/v1/events/copy-product-link",
            method: "POST",
            data: {
              taskId: this.data.taskId,
              productId
            }
          });
        } catch (error) {}
      }
    });
  },

  copyAllLinks() {
    const items = (this.data.result.outfit && this.data.result.outfit.items) || [];
    const links = items
      .filter((item) => item.productUrl)
      .map((item) => `${item.title}\n${item.productUrl}`);

    if (!links.length) {
      wx.showToast({ title: "暂无可复制链接", icon: "none" });
      return;
    }

    wx.setClipboardData({
      data: links.join("\n\n"),
      success: () => {
        wx.showToast({ title: "套装链接已复制", icon: "success" });
      }
    });
  },

  toggleFavorite() {
    const favorited = !this.data.favorited;
    this.setData({ favorited });
    wx.showToast({
      title: favorited ? "已收藏" : "已取消收藏",
      icon: "none"
    });
  },

  goBack() {
    wx.navigateBack({
      fail: () => this.goHome()
    });
  },

  goHome() {
    wx.reLaunch({
      url: "/pages/index/index"
    });
  },

  onShareAppMessage() {
    return {
      title: this.data.result.outfit.title || "AI 搭配师为我生成了一套穿搭",
      path: "/pages/index/index"
    };
  }
});
