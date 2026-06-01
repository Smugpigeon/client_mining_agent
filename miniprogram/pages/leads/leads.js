const api = require("../../utils/api");
const catalog = require("../../utils/catalog");
const app = getApp();

// 国家/类型/优先级 中文映射(治"中英混排")
const COUNTRY = {
  "United Arab Emirates": "阿联酋", "Saudi Arabia": "沙特", "Nigeria": "尼日利亚",
  "India": "印度", "Pakistan": "巴基斯坦", "United States of America": "美国",
  "France": "法国", "Türkiye": "土耳其", "China": "中国", "Kenya": "肯尼亚",
  "Uganda": "乌干达", "Tanzania": "坦桑尼亚", "Angola": "安哥拉", "Mauritius": "毛里求斯",
  "Ghana": "加纳", "Egypt": "埃及", "Morocco": "摩洛哥", "South Africa": "南非",
  "United Kingdom": "英国", "Italy": "意大利", "Lebanon": "黎巴嫩", "Cameroon": "喀麦隆",
  "Syria": "叙利亚", "Ukraine": "乌克兰", "Qatar": "卡塔尔", "Thailand": "泰国"
};
const TYPE = {
  distributor: "经销/进口商", retailer: "零售商", manufacturer: "品牌/制造商", unknown: "类型待定"
};
const PRI = {
  high: { label: "高", cls: "pri-high" },
  medium: { label: "中", cls: "pri-mid" },
  low: { label: "低", cls: "pri-low" }
};

function decorate(lead, i) {
  const p = PRI[lead.priority] || PRI.low;
  return {
    i: i,
    raw: lead,
    name: lead.company_name,
    country: COUNTRY[lead.country] || lead.country || "—",
    type: TYPE[lead.lead_type] || "类型待定",
    email: lead.email || "",
    hasEmail: !!lead.email,
    priLabel: p.label,
    priCls: p.cls,
    isHigh: lead.priority === "high",
    saved: !!lead.saved,
    sel: false
  };
}

Page({
  data: {
    all: [], view: [], loading: false, filter: "all",
    selectedCount: 0, allSelectedSaved: false, allViewSelected: false
  },

  onShow() {
    if (typeof this.getTabBar === "function" && this.getTabBar()) {
      this.getTabBar().setData({ active: 0 });
    }
    // 别处(对话页)新增了客户 → 刷新清单,保留已选
    const cat = catalog.load();
    if (cat.length !== this.data.all.length) {
      this._setLeads(cat, true);
    }
  },

  onLoad() {
    const cat = catalog.load();
    if (cat.length) {
      this._setLeads(cat, false); // 秒开:直接读本地清单
    } else {
      this._seeding = true; // 首次为空:静默拉一次后端铺底
      this._runJob();
    }
  },

  onReady() {
    // canvas 画一层点阵纹理铺在横幅上(贴图)
    wx.createSelectorQuery()
      .select("#tex")
      .fields({ node: true, size: true })
      .exec((res) => {
        const item = res && res[0];
        if (!item || !item.node) return;
        const canvas = item.node;
        const ctx = canvas.getContext("2d");
        const dpr = (wx.getWindowInfo && wx.getWindowInfo().pixelRatio) || 2;
        canvas.width = item.width * dpr;
        canvas.height = item.height * dpr;
        ctx.scale(dpr, dpr);
        ctx.fillStyle = "rgba(255,255,255,0.10)";
        for (let y = 16; y < item.height; y += 28) {
          for (let x = 16; x < item.width; x += 28) {
            ctx.beginPath();
            ctx.arc(x, y, 2.2, 0, 6.2832);
            ctx.fill();
          }
        }
      });
  },

  // 「找新客户」→ 去「对话」页用自然语言搜索
  onSearch() {
    wx.switchTab({ url: "/pages/chat/chat" });
  },

  _runJob() {
    this.setData({ loading: true });
    api
      .startJob({ source: "beauty_west_africa" })
      .then((job) => this._poll(job.job_id))
      .catch(() => this._fail("启动失败，检查后端"));
  },

  _poll(jobId) {
    api
      .getJob(jobId)
      .then((job) => {
        if (job.status === "done") {
          catalog.addLeads(job.leads || []);
          this._setLeads(catalog.load(), true);
          this._seeding = false;
          this.setData({ loading: false });
        } else if (job.status === "error") {
          this._fail("搜索出错");
        } else {
          setTimeout(() => this._poll(jobId), 2000);
        }
      })
      .catch(() => this._fail("查询失败"));
  },

  _setLeads(raws, preserveSelection) {
    const selectedKeys = preserveSelection
      ? new Set(this.data.all.filter((x) => x.sel).map((x) => catalog.keyOf(x.raw)))
      : new Set();
    const all = raws.map((lead, i) => {
      const d = decorate(lead, i);
      d.sel = selectedKeys.has(catalog.keyOf(lead));
      return d;
    });
    this._refreshList(all);
  },

  // 统一刷新:重算 view / 已选数 / 各按钮态,并把选中态共享给「群发」页
  _refreshList(all) {
    app.globalData.leads = all;
    const view = this._viewFor(all, this.data.filter);
    const count = all.reduce((n, x) => n + (x.sel ? 1 : 0), 0);
    this.setData({
      all: all,
      view: view,
      loading: false,
      selectedCount: count,
      allSelectedSaved: this._allSelSaved(all),
      allViewSelected: view.length > 0 && view.every((x) => x.sel)
    });
  },

  _viewFor(all, filter) {
    if (filter === "saved") return all.filter((x) => x.saved);
    if (filter === "high") return all.filter((x) => x.isHigh);
    if (filter === "email") return all.filter((x) => x.hasEmail);
    return all;
  },

  _allSelSaved(all) {
    const sel = all.filter((x) => x.sel);
    return sel.length > 0 && sel.every((x) => x.saved);
  },

  _fail(msg) {
    const wasSeeding = this._seeding;
    this._seeding = false;
    this.setData({ loading: false });
    if (!wasSeeding) wx.showToast({ title: msg, icon: "none" }); // 铺底失败就静默显示空态
  },

  onFilter(e) {
    this.setData({ filter: e.detail.value });
    this._refreshList(this.data.all);
  },

  onToggle(e) {
    const i = e.currentTarget.dataset.i;
    const all = this.data.all;
    all[i].sel = !all[i].sel;
    this._refreshList(all);
  },

  // 全选 / 取消全选(作用于当前筛选下可见的客户)
  onToggleAll() {
    const all = this.data.all;
    const view = this._viewFor(all, this.data.filter);
    const target = !(view.length > 0 && view.every((x) => x.sel));
    view.forEach((x) => {
      x.sel = target;
    });
    this._refreshList(all);
  },

  // 保存 / 取消保存所选
  onSaveSelected() {
    const all = this.data.all;
    const selected = all.filter((x) => x.sel);
    if (!selected.length) {
      wx.showToast({ title: "请先勾选客户", icon: "none" });
      return;
    }
    const makeSaved = !selected.every((x) => x.saved);
    selected.forEach((x) => {
      x.saved = makeSaved;
      x.raw.saved = makeSaved;
    });
    catalog.save(all.map((x) => x.raw));
    this._refreshList(all);
    wx.showToast({ title: makeSaved ? `已保存 ${selected.length} 家` : "已取消保存", icon: "success" });
  },

  // 一键保存所有高价值(高优先级)客户
  onSaveHighValue() {
    const all = this.data.all;
    const high = all.filter((x) => x.isHigh);
    if (!high.length) {
      wx.showToast({ title: "暂无高价值客户", icon: "none" });
      return;
    }
    high.forEach((x) => {
      x.saved = true;
      x.raw.saved = true;
    });
    catalog.save(all.map((x) => x.raw));
    this._refreshList(all);
    wx.showToast({ title: `已保存 ${high.length} 家高价值`, icon: "success" });
  }
});
