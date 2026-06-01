const api = require("../../utils/api");
const catalog = require("../../utils/catalog");

const TYPE = { distributor: "经销/进口", retailer: "零售", manufacturer: "品牌", unknown: "类型待定" };

Page({
  data: { messages: [], input: "", sending: false, scrollId: "" },

  onShow() {
    if (typeof this.getTabBar === "function" && this.getTabBar()) {
      this.getTabBar().setData({ active: 1 });
    }
  },

  onInput(e) {
    this.setData({ input: e.detail.value });
  },

  onEg(e) {
    this.setData({ input: e.currentTarget.dataset.t }, () => this.onSend());
  },

  onSend() {
    const text = (this.data.input || "").trim();
    if (!text || this.data.sending) return;
    const userMsg = { id: this._nextId(), role: "user", content: text, leads: [] };
    const messages = this.data.messages.concat([userMsg]);
    this.setData({ messages: messages, input: "", sending: true });
    this._scrollToEnd();

    const history = messages.map((m) => ({ role: m.role, content: m.content }));
    api
      .chatSend(history)
      .then((res) => {
        const leads = (res.leads || []).map((l) => ({
          ...l,
          typeCn: TYPE[l.lead_type] || "类型待定"
        }));
        const reply = { id: this._nextId(), role: "assistant", content: res.reply || "(无回复)", leads: leads };
        this.setData({ messages: this.data.messages.concat([reply]), sending: false });
        this._scrollToEnd();
      })
      .catch((err) => {
        this.setData({ sending: false });
        const detail = err && err.data && err.data.detail;
        wx.showToast({ title: detail || "对话失败，检查后端 / LLM", icon: "none" });
      });
  },

  _nextId() {
    this._seq = (this._seq || 0) + 1;
    return "m" + this._seq;
  },

  _scrollToEnd() {
    this.setData({ scrollId: "msg-" + (this.data.messages.length - 1) });
  },

  onSaveLead(e) {
    const m = e.currentTarget.dataset.m;
    const i = e.currentTarget.dataset.i;
    const lead = this.data.messages[m].leads[i];
    const n = catalog.addLeads([lead]);
    wx.showToast({ title: n ? "已存入客源" : "客源中已存在", icon: "none" });
  },

  onSaveAll(e) {
    const m = e.currentTarget.dataset.m;
    const leads = this.data.messages[m].leads || [];
    const n = catalog.addLeads(leads);
    wx.showToast({ title: n ? `已存入 ${n} 家` : "都已在客源中", icon: "success" });
  }
});
