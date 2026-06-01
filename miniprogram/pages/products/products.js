const STORAGE_KEY = "products";

function load() {
  return wx.getStorageSync(STORAGE_KEY) || [];
}
function save(list) {
  wx.setStorageSync(STORAGE_KEY, list);
}
function emptyForm() {
  return { id: "", name: "", intro: "", highlightsText: "", price: "" };
}

Page({
  data: {
    list: [],
    showForm: false,
    form: emptyForm()
  },

  onShow() {
    if (typeof this.getTabBar === "function" && this.getTabBar()) {
      this.getTabBar().setData({ active: 2 });
    }
    this.setData({ list: load() });
  },

  onAdd() {
    this.setData({ showForm: true, form: emptyForm() });
  },

  onEdit(e) {
    const item = this.data.list[e.currentTarget.dataset.i];
    this.setData({
      showForm: true,
      form: {
        id: item.id,
        name: item.name,
        intro: item.intro || "",
        highlightsText: (item.highlights || []).join("\n"),
        price: item.price || ""
      }
    });
  },

  onCancel() {
    this.setData({ showForm: false });
  },

  onName(e) {
    this.setData({ "form.name": e.detail.value });
  },
  onIntro(e) {
    this.setData({ "form.intro": e.detail.value });
  },
  onHighlights(e) {
    this.setData({ "form.highlightsText": e.detail.value });
  },
  onPrice(e) {
    this.setData({ "form.price": e.detail.value });
  },

  onSave() {
    const f = this.data.form;
    if (!f.name.trim()) {
      wx.showToast({ title: "请填产品名称", icon: "none" });
      return;
    }
    const product = {
      id: f.id || String(Date.now()),
      name: f.name.trim(),
      intro: f.intro.trim(),
      highlights: f.highlightsText
        .split("\n")
        .map((s) => s.trim())
        .filter(Boolean),
      price: f.price.trim()
    };
    const list = this.data.list.slice();
    const idx = list.findIndex((x) => x.id === product.id);
    if (idx >= 0) {
      list[idx] = product;
    } else {
      list.push(product);
    }
    save(list);
    this.setData({ list: list, showForm: false });
    wx.showToast({ title: "已保存", icon: "success" });
  },

  onDelete(e) {
    const i = e.currentTarget.dataset.i;
    const name = this.data.list[i].name;
    wx.showModal({
      title: "删除产品",
      content: `确定删除「${name}」？`,
      success: (r) => {
        if (!r.confirm) return;
        const list = this.data.list.slice();
        list.splice(i, 1);
        save(list);
        this.setData({ list: list });
      }
    });
  }
});
