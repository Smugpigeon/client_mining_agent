const api = require("../../utils/api");

Page({
  data: { leads: [], selected: [], loading: false, jobId: "" },

  onSearch() {
    this.setData({ loading: true, leads: [], selected: [], jobId: "" });
    api
      .startJob({ source: "beauty_west_africa", limit: 20 })
      .then((job) => this._poll(job.job_id))
      .catch(() => this._fail("启动失败，检查后端"));
  },

  _poll(jobId) {
    api
      .getJob(jobId)
      .then((job) => {
        if (job.status === "done") {
          this.setData({ leads: job.leads, jobId: jobId, loading: false });
        } else if (job.status === "error") {
          this._fail("搜索出错");
        } else {
          setTimeout(() => this._poll(jobId), 2000);
        }
      })
      .catch(() => this._fail("查询失败"));
  },

  _fail(msg) {
    this.setData({ loading: false });
    wx.showToast({ title: msg, icon: "none" });
  },

  onSelectChange(e) {
    this.setData({ selected: e.detail });
  },

  // 批量导出「勾选行」为 CSV 文件（客户端，两种模式都可用，尊重勾选）。
  onBatchExport() {
    const rows = this.data.selected.map((i) => this.data.leads[i]);
    if (!rows.length) {
      wx.showToast({ title: "请先勾选客户", icon: "none" });
      return;
    }
    const esc = (v) => '"' + String(v == null ? "" : v).replace(/"/g, '""') + '"';
    const header = ["公司名称", "国家", "客户类型", "邮箱", "电话", "网站", "优先级"];
    const lines = [header.join(",")].concat(
      rows.map((r) =>
        [r.company_name, r.country, r.lead_type, r.email, r.phone, r.website, r.priority]
          .map(esc)
          .join(",")
      )
    );
    const filePath = `${wx.env.USER_DATA_PATH}/leads_${Date.now()}.csv`;
    wx.getFileSystemManager().writeFile({
      filePath: filePath,
      data: "﻿" + lines.join("\n"), // BOM，Excel 正确识别中文
      encoding: "utf-8",
      success: () =>
        wx.openDocument({ filePath: filePath, showMenu: true, fail: () => this._clip(lines) }),
      fail: () => this._clip(lines)
    });
  },

  _clip(lines) {
    wx.setClipboardData({
      data: lines.join("\n"),
      success: () => wx.showToast({ title: "已复制到剪贴板", icon: "success" })
    });
  },

  // 下载「整个 job」的服务端 xlsx（走后端 /export）。
  onExportAll() {
    if (!this.data.jobId) {
      wx.showToast({ title: "请先搜索", icon: "none" });
      return;
    }
    wx.showLoading({ title: "生成中…" });
    wx.downloadFile({
      url: api.exportUrl(this.data.jobId, "xlsx"),
      success: (res) => {
        wx.hideLoading();
        if (res.statusCode === 200) {
          wx.openDocument({ filePath: res.tempFilePath, showMenu: true });
        } else {
          wx.showToast({ title: "下载失败", icon: "none" });
        }
      },
      fail: () => {
        wx.hideLoading();
        wx.showToast({ title: "下载失败", icon: "none" });
      }
    });
  }
});
