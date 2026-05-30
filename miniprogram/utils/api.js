// 后端调用。本地用 wx.request；生产建议改成 wx.cloud.callContainer（微信云托管，免合法域名）。
const app = getApp();

function request(method, path, data) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: app.globalData.apiBase + path,
      method: method,
      data: data,
      header: { "content-type": "application/json" },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          reject(res);
        }
      },
      fail: reject
    });
  });
}

module.exports = {
  startJob: (params) => request("POST", "/jobs", params),
  getJob: (jobId) => request("GET", "/jobs/" + jobId, {})
};
