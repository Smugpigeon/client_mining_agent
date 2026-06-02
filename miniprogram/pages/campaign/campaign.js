const api = require("../../utils/api");
const app = getApp();
const catalog = require("../../utils/catalog");
const userProfile = require("../../utils/profile");

Page({
  data: {
    customers: [], // 群发对象候选(客源里带邮箱的客户),直接在本页勾选
    recipCount: 0,
    allCustSel: false,
    subject: "你好「公司名」",
    body: "我们是中国的护肤品出口商，看到「公司名」在「国家」的业务，想了解是否有合作或采购的机会。",
    fromName: "",
    products: [],
    personalize: false,
    subjLabel: "主题",
    subjPh: "你好「公司名」",
    bodyLabel: "正文",
    bodyPh: "我们是中国护肤品出口商，想与「公司名」合作…",
    busy: false,
    dry: true,
    results: []
  },

  onShow() {
    if (typeof this.getTabBar === "function" && this.getTabBar()) {
      this.getTabBar().setData({ active: 3 });
    }
    this._loadCustomers();
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
    // 落款名默认用「我的」里的署名
    if (!this.data.fromName) {
      const p = userProfile.load();
      if (p.signer) this.setData({ fromName: p.signer });
    }
  },

  // 从客源清单(本地)加载带邮箱的客户;沿用客源页/本页已有的勾选
  _loadCustomers() {
    const prevSel = {};
    (app.globalData.leads || []).forEach((x) => {
      if (x.sel && x.email) prevSel[x.email] = true;
    });
    (this.data.customers || []).forEach((c) => {
      if (c.sel) prevSel[c.email] = true;
    });
    const seen = {};
    const customers = [];
    (catalog.load() || []).forEach((l) => {
      const email = (l.email || "").trim();
      if (!email || seen[email]) return;
      seen[email] = true;
      customers.push({ raw: l, name: l.company_name, email: email, sel: !!prevSel[email] });
    });
    this._setCustomers(customers);
  },

  _setCustomers(customers) {
    const recipCount = customers.reduce((n, c) => n + (c.sel ? 1 : 0), 0);
    this.setData({
      customers: customers,
      recipCount: recipCount,
      allCustSel: customers.length > 0 && recipCount === customers.length
    });
  },

  onToggleCustomer(e) {
    const i = e.currentTarget.dataset.i;
    const customers = this.data.customers;
    customers[i].sel = !customers[i].sel;
    this._setCustomers(customers);
  },

  onSelectAllCustomers() {
    const customers = this.data.customers;
    const target = !(customers.length > 0 && customers.every((c) => c.sel));
    customers.forEach((c) => {
      c.sel = target;
    });
    this._setCustomers(customers);
  },

  _recipients() {
    return this.data.customers
      .filter((c) => c.sel)
      .map((c) => ({
        email: c.email,
        company_name: c.raw.company_name,
        country: c.raw.country || "",
        business: c.raw.business || "",
        website: c.raw.website || ""
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

  onTogglePersonalize() {
    const on = !this.data.personalize;
    this.setData({
      personalize: on,
      subjLabel: on ? "主题（AI 自动生成，可留空）" : "主题",
      bodyLabel: on ? "写信意图 / 卖点（AI 据此 + 客户资料逐个写信）" : "正文",
      bodyPh: on
        ? "例：推广玻尿酸面膜、约视频会议、强调医用级原料"
        : "我们是中国护肤品出口商，想与「公司名」合作…"
    });
  },

  // 点标签把「公司名」/「国家」插到正文里(自动追加到末尾)
  onInsertVar(e) {
    const v = e.currentTarget.dataset.v;
    this.setData({ body: (this.data.body || "") + v });
  },

  onPreview() {
    this._run(true);
  },

  onSend() {
    wx.showModal({
      title: "确认发送",
      content: `将向 ${this.data.recipCount} 个邮箱发送，请确认后端已配置发件邮箱(SMTP)。`,
      success: (r) => {
        if (r.confirm) this._run(false);
      }
    });
  },

  _run(dry) {
    let recipients = this._recipients();
    if (!recipients.length) {
      wx.showToast({ title: "请先在上方勾选群发对象", icon: "none" });
      return;
    }
    if (!this.data.body.trim()) {
      wx.showToast({ title: this.data.personalize ? "请填写信意图" : "请填正文", icon: "none" });
      return;
    }
    if (!this.data.personalize && !this.data.subject.trim()) {
      wx.showToast({ title: "请填主题", icon: "none" });
      return;
    }
    // AI 预览只生成第 1 个做样本(省时省钱);真发才全量
    if (dry && this.data.personalize) recipients = recipients.slice(0, 1);
    this.setData({ busy: true, dry: dry, results: [] });
    const prof = userProfile.load();
    api
      .startCampaign({
        subject: this.data.subject,
        body: this.data.body,
        from_name: this.data.fromName || prof.signer || "",
        recipients: recipients,
        products: this._selectedProducts(),
        personalize: this.data.personalize,
        profile: prof,
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
    const rows = this.data.customers.filter((c) => c.sel).map((c) => c.raw);
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
