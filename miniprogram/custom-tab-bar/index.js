Component({
  data: {
    active: 0,
    list: [
      {
        path: "/pages/leads/leads",
        text: "客源",
        icon: "/assets/tab/clients.svg",
        iconOn: "/assets/tab/clients-on.svg"
      },
      {
        path: "/pages/chat/chat",
        text: "对话",
        icon: "/assets/tab/chat.svg",
        iconOn: "/assets/tab/chat-on.svg"
      },
      {
        path: "/pages/products/products",
        text: "产品",
        icon: "/assets/tab/box.svg",
        iconOn: "/assets/tab/box-on.svg"
      },
      {
        path: "/pages/campaign/campaign",
        text: "群发",
        icon: "/assets/tab/mail.svg",
        iconOn: "/assets/tab/mail-on.svg"
      }
    ]
  },
  methods: {
    onTap(e) {
      const path = e.currentTarget.dataset.path;
      wx.switchTab({ url: path });
    }
  }
});
