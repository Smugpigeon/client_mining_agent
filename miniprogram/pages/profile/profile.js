const profile = require("../../utils/profile");

Page({
  data: { company: "", products_desc: "", markets: "", signer: "", language: "英文" },

  onShow() {
    if (typeof this.getTabBar === "function" && this.getTabBar()) {
      this.getTabBar().setData({ active: 4 });
    }
    const p = profile.load();
    this.setData({
      company: p.company || "",
      products_desc: p.products_desc || "",
      markets: p.markets || "",
      signer: p.signer || "",
      language: p.language || "英文"
    });
  },

  onCompany(e) {
    this.setData({ company: e.detail.value });
  },
  onProducts(e) {
    this.setData({ products_desc: e.detail.value });
  },
  onMarkets(e) {
    this.setData({ markets: e.detail.value });
  },
  onSigner(e) {
    this.setData({ signer: e.detail.value });
  },
  onLanguage(e) {
    this.setData({ language: e.currentTarget.dataset.v });
  },

  onSave() {
    profile.save({
      company: this.data.company.trim(),
      products_desc: this.data.products_desc.trim(),
      markets: this.data.markets.trim(),
      signer: this.data.signer.trim(),
      language: this.data.language
    });
    wx.showToast({ title: "已保存", icon: "success" });
  }
});
