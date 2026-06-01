const api = require("../../utils/api");
const app = getApp();

Page({
  data: {
    count: 0,
    withEmail: 0,
    subject: "你好 {{company_name}}",
    body: "我们是中国的护肤品出口商，看到{{company_name}}在{{country}}的业务，想了解是否有合作或采购的机会。",
    fromName: "",
    products: [],
    busy: false,
    dry: true,
    results: []
  },

  onShow() {
    if (typeof this.getTabBar === "function" && this.getTabBar()) {
      this.getTabBar().setData({ active: 3 });
    }
    this._refresh();
    // 读产品库,保留已勾选状态
    const prev = {};
    (this.data.products || []).forEach((p) => {
      prev[p.id] = p.sel;
    });
    const products = (wx.getStorageSync("products") || []).map((p) => ({
      ...p,
      sel: !!prev[p.id]
    }));
    this.setData({ products: products });
  },

  _refresh() {
    const selected = (app.globalData.leads || []).filter((x) => x.sel);
    const withEmail = selected.filter((x) => x.hasEmail).length;
    this.setData({ count: selected.length, withEmail: withEmail });
  },

  _recipients() {
    return (app.globalData.leads || [])
      .filter((x) => x.sel && x.hasEmail)
      .map((x) => ({
        email: x.email,
        company_name: x.raw.company_name,
        country: x.raw.country || ""
      }));
  },

  _selectedProducts() {
    return this.data.products
      .filter((p) => p.sel)
      .map((p) => ({
        name: p.name,
        intro: p.intro || "",
        highlights: p.highlights || [],
        price: p.price || ""
      }));
  },

  onToggleProduct(e) {
    const i = e.currentTarget.dataset.i;
    this.setData({ [`products[${i}].sel`]: !this.data.products[i].sel });
  },

  onSubject(e) {
    this.setData({ subject: e.detail.value });
  },
  onBody(e) {
    this.setData({ body: e.detail.value });
  },
  onFrom(e) {
    this.setData({ fromName: e.detail.value });
  },

  onPreview() {
    this._run(true);
  },

  onSend() {
    wx.showModal({
      title: "确认发送",
      content: `将向 ${this.data.withEmail} 个邮箱发送，请确认后端已配置发件邮箱(SMTP)。`,
      success: (r) => {
        if (r.confirm) this._run(false);
      }
    });
  },

  _run(dry) {
    const recipients = this._recipients();
    if (!recipients.length) {
      wx.showToast({ title: "没有可发的邮箱", icon: "none" });
      return;
    }
    if (!this.data.subject.trim() || !this.data.body.trim()) {
      wx.showToast({ title: "请填主题和正文", icon: "none" });
      return;
    }
    this.setData({ busy: true, dry: dry, results: [] });
    api
      .startCampaign({
        subject: this.data.subject,
        body: this.data.body,
        from_name: this.data.fromName,
        recipients: recipients,
        products: this._selectedProducts(),
        dry_run: dry
      })
      .then((c) => this._poll(c.campaign_id))
      .catch((err) => this._fail(err));
  },

  _poll(id) {
    api
      .getCampaign(id)
      .then((c) => {
        if (c.status === "done") {
          this.setData({ busy: false, results: c.results || [] });
          if (!this.data.dry) {
            wx.showToast({ title: `已发 ${c.sent} 封 · 失败 ${c.failed}`, icon: "none" });
          }
        } else if (c.status === "error") {
          this.setData({ busy: false });
          wx.showToast({ title: c.error || "出错", icon: "none" });
        } else {
          setTimeout(() => this._poll(id), 1500);
        }
      })
      .catch((err) => this._fail(err));
  },

  _fail(err) {
    this.setData({ busy: false });
    const detail = err && err.data && err.data.detail;
    wx.showToast({ title: detail || "请求失败，检查后端 / SMTP", icon: "none" });
  },

  onExportCsv() {
    const rows = (app.globalData.leads || []).filter((x) => x.sel).map((x) => x.raw);
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
      data: "﻿" + lines.join("\n"),
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

  onExportAll() {
    const jobId = app.globalData.jobId;
    if (!jobId) {
      wx.showToast({ title: "请先在客源页搜索", icon: "none" });
      return;
    }
    wx.showLoading({ title: "生成中…" });
    wx.downloadFile({
      url: api.exportUrl(jobId, "xlsx"),
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
