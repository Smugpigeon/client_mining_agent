// 后端接入配置。
// 本地调试：apiMode="request"，apiBase 指向本地后端；开发者工具勾「不校验合法域名」。
// 生产：apiMode="callContainer"，部署到微信云托管后填 cloudEnv/cloudService（免合法域名/备案）。
//        文件下载(/export)仍走 apiBase 公网域名 + wx.downloadFile（需配进 downloadFile 合法域名）。
App({
  globalData: {
    apiMode: "callContainer", // "request" | "callContainer"
    apiBase: "http://127.0.0.1:8000",
    cloudEnv: "prod-d2g9fid9xb059f686", // 云托管环境 ID（callContainer 模式）
    cloudService: "leadfinder", // 云托管服务名（callContainer 模式）
    leads: [], // 跨页共享:已加载客户(含选中态),供群发页读取
    jobId: "" // 当前搜索 job(用于下载全部 xlsx)
  },
  onLaunch() {
    if (this.globalData.apiMode === "callContainer" && wx.cloud) {
      wx.cloud.init({ env: this.globalData.cloudEnv });
    }
  }
});
