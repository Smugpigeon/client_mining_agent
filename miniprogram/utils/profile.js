// 用户自己的身份档案(本地存储),喂给 agent 做个性化。
const KEY = "user_profile";

function load() {
  return wx.getStorageSync(KEY) || {};
}

function save(p) {
  wx.setStorageSync(KEY, p);
}

module.exports = { load, save };
