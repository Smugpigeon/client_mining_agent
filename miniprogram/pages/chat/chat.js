const api = require("../../utils/api");
const catalog = require("../../utils/catalog");
const userProfile = require("../../utils/profile");

const TYPE = { distributor: "经销/进口", retailer: "零售", manufacturer: "品牌", unknown: "类型待定" };

Page({
  data: { messages: [], input: "", sending: false, scrollId: "", pageStyle: "" },

  onShow() {
    if (typeof this.getTabBar === "function" && this.getTabBar()) {
      this.getTabBar().setData({ active: 1 });
    }
    this._fit(0);
  },

  onReady() {
    this._fit(0);
  },

  // 真机适配:量出自定义 tab 栏的真实顶边,把页面高度卡到它正上方;首帧未渲染好就重试
  _fit(tries) {
    const tb = typeof this.getTabBar === "function" ? this.getTabBar() : null;
    if (!tb || !tb.createSelectorQuery) return;
    tb.createSelectorQuery()
      .select(".tabbar")
      .boundingClientRect((rect) => {
        if (rect && rect.top > 0) {
          this.setData({ pageStyle: "height:" + rect.top + "px" });
        } else if (tries < 6) {
          setTimeout(() => this._fit(tries + 1), 120);
        }
      })
      .exec();
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
      .chatSend(history, userProfile.load())
      .then((c) => this._pollChat(c.chat_id))
      .catch((err) => this._chatFail(err));
  },

  // 异步:轮询后端拿对话结果(避开 callContainer 的同步超时)
  _pollChat(id) {
    api
      .getChat(id)
      .then((c) => {
        if (c.status === "done") {
          this._renderReply(c.reply, c.leads);
        } else if (c.status === "error") {
          this.setData({ sending: false });
          wx.showToast({ title: c.error || "对话失败", icon: "none" });
        } else {
          setTimeout(() => this._pollChat(id), 1500);
        }
      })
      .catch((err) => this._chatFail(err));
  },

  _renderReply(rawReply, rawLeads) {
    const existing = new Set(catalog.load().map(catalog.keyOf));
    const leads = (rawLeads || []).map((l) => ({
      ...l,
      typeCn: TYPE[l.lead_type] || "类型待定",
      inLib: existing.has(catalog.keyOf(l)) // 已在客源里 → 按钮直接显示已保存
    }));
    // 去掉推理模型(MiniMax-M3 等)输出的 <think>...</think> 思考块
    const text = (rawReply || "").replace(/<think>[\s\S]*?<\/think>\s*/g, "").trim();
    const reply = { id: this._nextId(), role: "assistant", content: text || "(无回复)", leads: leads };
    this.setData({ messages: this.data.messages.concat([reply]), sending: false });
    this._scrollToEnd();
  },

  _chatFail(err) {
    this.setData({ sending: false });
    console.error("chat 失败:", err); // DevTools 控制台(底部)看完整错误
    const detail = (err && err.data && err.data.detail) || (err && err.errMsg);
    wx.showToast({ title: detail || "对话失败，检查后端 / LLM", icon: "none" });
  },

  _nextId() {
    this._seq = (this._seq || 0) + 1;
    return "m" + this._seq;
  },

  _scrollToEnd() {
    this.setData({ scrollId: "msg-" + (this.data.messages.length - 1) });
  },

  _clean(lead) {
    const c = Object.assign({}, lead);
    delete c.typeCn; // 剥掉 UI 字段,别写进客源清单
    delete c.inLib;
    return c;
  },

  onSaveLead(e) {
    const m = e.currentTarget.dataset.m;
    const i = e.currentTarget.dataset.i;
    if (this.data.messages[m].leads[i].inLib) return; // 已存入,忽略
    catalog.addLeads([this._clean(this.data.messages[m].leads[i])]);
    this.setData({ [`messages[${m}].leads[${i}].inLib`]: true });
    wx.showToast({ title: "已存入客源", icon: "success" });
  },

  onSaveAll(e) {
    const m = e.currentTarget.dataset.m;
    const leads = this.data.messages[m].leads || [];
    const n = catalog.addLeads(leads.map((l) => this._clean(l)));
    const patch = {};
    leads.forEach((l, i) => {
      patch[`messages[${m}].leads[${i}].inLib`] = true;
    });
    this.setData(patch);
    wx.showToast({ title: n ? `已存入 ${n} 家` : "都已在客源中", icon: "success" });
  }
});
