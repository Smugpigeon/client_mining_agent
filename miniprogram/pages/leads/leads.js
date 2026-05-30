const api = require("../../utils/api");

Page({
  data: {
    leads: [],
    selected: [],
    loading: false
  },

  onSearch() {
    this.setData({ loading: true, leads: [], selected: [] });
    api
      .startJob({ source: "beauty_west_africa", limit: 20 })
      .then((job) => this._poll(job.job_id))
      .catch(() => {
        this.setData({ loading: false });
        wx.showToast({ title: "启动失败，检查后端", icon: "none" });
      });
  },

  _poll(jobId) {
    api
      .getJob(jobId)
      .then((job) => {
        if (job.status === "done") {
          this.setData({ leads: job.leads, loading: false });
        } else if (job.status === "error") {
          this.setData({ loading: false });
          wx.showToast({ title: "搜索出错", icon: "none" });
        } else {
          setTimeout(() => this._poll(jobId), 2000);
        }
      })
      .catch(() => {
        this.setData({ loading: false });
        wx.showToast({ title: "查询失败", icon: "none" });
      });
  },

  onSelectChange(e) {
    this.setData({ selected: e.detail });
  },

  onBatchExport() {
    const rows = this.data.selected.map((i) => this.data.leads[i]);
    if (!rows.length) {
      wx.showToast({ title: "请先勾选客户", icon: "none" });
      return;
    }
    const header = ["公司名称", "国家", "客户类型", "邮箱", "优先级"];
    const lines = [header.join(",")].concat(
      rows.map((r) =>
        [r.company_name, r.country, r.lead_type, r.email || "", r.priority].join(",")
      )
    );
    // 演示：批量导出到剪贴板。生产可改为调后端 /export 生成 xlsx 文件下载。
    wx.setClipboardData({
      data: lines.join("\n"),
      success: () => wx.showToast({ title: "已复制 " + rows.length + " 条", icon: "success" })
    });
  }
});
