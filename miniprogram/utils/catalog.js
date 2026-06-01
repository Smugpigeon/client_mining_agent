// 本地客户清单(客源)的统一读写 + 去重并入。leads 页与对话页共用,保证去重口径一致。
const STORAGE_KEY = "leads_catalog";

function load() {
  return wx.getStorageSync(STORAGE_KEY) || [];
}

function save(raws) {
  wx.setStorageSync(STORAGE_KEY, raws);
}

function keyOf(lead) {
  const name = (lead.company_name || "").trim().toLowerCase();
  const id = (lead.website || lead.email || "").trim().toLowerCase();
  return name + "|" + id;
}

// 并入新客户,去重,返回实际新增数量
function addLeads(incoming) {
  const before = load();
  const existing = new Set(before.map(keyOf));
  const fresh = (incoming || []).filter((l) => l && l.company_name && !existing.has(keyOf(l)));
  if (fresh.length) save(before.concat(fresh));
  return fresh.length;
}

module.exports = { load, save, keyOf, addLeads };
