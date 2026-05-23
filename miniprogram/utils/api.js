const { API_BASE_URL } = require("./config");

function request({ url, method = "GET", data }) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${API_BASE_URL}${url}`,
      method,
      data,
      header: {
        "content-type": "application/json"
      },
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          reject(res.data || { message: "请求失败" });
        }
      },
      fail: reject
    });
  });
}

function uploadStyleTask({ filePath, formData }) {
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: `${API_BASE_URL}/api/v1/style-tasks`,
      filePath,
      name: "photo",
      formData,
      success(res) {
        try {
          const data = JSON.parse(res.data);
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(data);
          } else {
            reject(data);
          }
        } catch (error) {
          reject(error);
        }
      },
      fail: reject
    });
  });
}

module.exports = {
  API_BASE_URL,
  request,
  uploadStyleTask
};
