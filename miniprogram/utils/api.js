// 后端调用：按 app.globalData.apiMode 走 wx.request(本地) 或 wx.cloud.callContainer(云托管)。
const app = getApp();

function request(method, path, data) {
  const g = app.globalData;
  return new Promise((resolve, reject) => {
    const success = (res) => {
      if (res.statusCode >= 200 && res.statusCode < 300) resolve(res.data);
      else reject(res);
    };
    if (g.apiMode === "callContainer") {
      wx.cloud.callContainer({
        config: { env: g.cloudEnv },
        path,
        method,
        header: { "X-WX-SERVICE": g.cloudService, "content-type": "application/json" },
        data,
        success,
        fail: reject
      });
    } else {
      wx.request({
        url: g.apiBase + path,
        method,
        data,
        header: { "content-type": "application/json" },
        success,
        fail: reject
      });
    }
  });
}

module.exports = {
  startJob: (params) => request("POST", "/jobs", params),
  getJob: (jobId) => request("GET", "/jobs/" + jobId, {}),
  startCampaign: (payload) => request("POST", "/campaign", payload),
  getCampaign: (id) => request("GET", "/campaign/" + id, {}),
  chatSend: (messages) => request("POST", "/chat", { messages: messages }),
  getChat: (id) => request("GET", "/chat/" + id, {}),
  // 整个 job 的服务端文件下载 URL（xlsx/csv）；用公网域名 + wx.downloadFile 取文件。
  exportUrl: (jobId, fmt) =>
    app.globalData.apiBase + "/jobs/" + jobId + "/export?fmt=" + (fmt || "xlsx")
};
