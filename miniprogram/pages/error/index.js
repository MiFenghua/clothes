Page({
  data: {
    message: "本次试穿图生成失败，请换一张更清晰的全身照后重试。"
  },

  onLoad(options) {
    if (options.message) {
      this.setData({
        message: decodeURIComponent(options.message)
      });
    }
  },

  goHome() {
    wx.reLaunch({
      url: "/pages/index/index"
    });
  }
});
