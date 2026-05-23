# clozAi iOS App UI Kit

Figma 文件已创建，但当前 Figma MCP 在 Starter 方案下返回调用额度限制，暂时无法继续用 API 直接写入画布。

- Figma 文件：<https://www.figma.com/design/pzELrAOqY7Y2QwLZOHfwu4>
- 可导入 Figma 的设计板：`design/clozai-ios-ui-kit.figma-import.svg`
- 浏览器预览：`design/clozai-ios-ui-kit.preview.html`

## 页面范围

1. 启动页
2. 登录欢迎
3. 风格建档
4. 照片上传
5. 特征报告
6. 首页推荐
7. 灵感社区
8. 我的衣橱
9. 单品详情
10. 搭配详情
11. 购买清单
12. AI 试穿
13. 收藏日历
14. 我的设置

## iOS 设计 Token

- Background: `#F7F5F2`
- Surface: `#FFFFFF`
- Pearl: `#FAF9F6`
- Ink: `#111116`
- Muted: `#72727D`
- Divider: `#E8E5E0`
- Primary Lavender: `#8A78FF`
- Lavender Soft: `#EFECFF`
- Denim Accent: `#DDE9F0`
- Linen Accent: `#E9E0D3`
- Corner radius: cards `16-24`, phone `44`, CTA `26`
- Typography: SF Pro / PingFang SC, title 24-28, section 15-17, body 12-14, caption 10-11

## Figma 导入建议

将 `design/clozai-ios-ui-kit.figma-import.svg` 拖进 Figma 文件即可得到完整设计板。额度恢复后，建议再用 Figma API 重建为 native frame/component：

- 建立 `Colors`, `Typography`, `Spacing`, `Radius`, `Shadow` 变量集合
- 抽出 `Button / Chip / Card / Phone Frame / Product Row / Bottom Tab` 组件
- 将 14 个 screen frame 按 iOS 390 x 844 拆分并命名
- 为 iOS 客户端保留每屏主要状态：empty/loading/filled/error
