# 安卓 App（APK）构建与部署

面试官小P 的手机形态：**Capacitor 把 Vue3 前端打包进 APK 本地运行，后端 API/语音
WebSocket 连远程服务器**。文字聊天、题库、模拟面试全部可用；语音输入/在线合成依赖
服务器侧的阿里云 DashScope 密钥（欠费时自动降级：TTS 走 edge-tts，ASR 不可用）。

## 架构要点

- `frontend/android/` 是 Capacitor 生成的安卓壳工程（已入库，构建产物由其自带
  `.gitignore` 排除）；`appId=com.xiaop.interview`，应用名"面试官小P"。
- 服务器地址三级来源（`frontend/src/api/server.js`）：
  1. 登录页"服务器地址"输入框（仅 APK 内显示，存 localStorage，改后即时生效）；
  2. 构建期 `VITE_SERVER_BASE` 环境变量（烘焙进包里的默认值）；
  3. 都为空 → 相对路径（Web 版同源行为，APK 内不可用，必须配置其一）。
- APK 内路由为 hash 模式、WS/REST 地址由服务器地址派生；Web 版行为完全不变。
- 后端已放行 Capacitor WebView 的跨域来源（`config.CORS_ORIGINS`，默认含
  `https://localhost` / `capacitor://localhost`，可用环境变量追加）。

## 获取 APK

### 方式一：GitHub Actions（推荐，本机无需 Java/Android SDK）

- **手动构建**：仓库 Actions → "Android APK" → Run workflow，可填内置服务器地址；
  完成后在该次运行页面下载 `android-apk` artifact。
- **发版构建**：推送 `v*` 标签（如 `git tag v1.0.0 && git push origin v1.0.0`），
  APK 自动附到对应 GitHub Release。

### 方式二：本地构建

1. 安装 JDK 17 与 Android Studio（含 Android SDK）。
2. `cd frontend && npm install && npm run build && npx cap sync android`
3. 打开 `frontend/android` 于 Android Studio 直接 Run/Build APK，或命令行
   `./gradlew assembleDebug`，产物在 `android/app/build/outputs/apk/debug/app-debug.apk`。

### 前端改动后刷新 APK

```bash
cd frontend
npm run build        # 必须：APK 打包的是 dist 产物
npx cap sync android # 必须：把 dist 拷进安卓工程
# 再走上面任一构建方式
```

## 注意事项

- **明文 HTTP 仅限测试**：`AndroidManifest.xml` 已开 `usesCleartextTraffic=true`
  以便连 HTTP 服务器调试；正式分发务必上 HTTPS（同时语音 WS 自动变 wss），
  并考虑关掉明文开关。
- **麦克风权限**：首次进入语音页时系统弹窗请求（Capacitor WebView 自动处理），
  拒绝后语音输入不可用，需在系统设置中手动开启。
- debug 包可直接安装（需允许"安装未知来源应用"）；上架商店需另做 release
  签名（`gradlew assembleRelease` + keystore），当前未配置。

## 云服务器部署清单

后端复用 `deploy/`（多阶段 Dockerfile + docker-compose，数据卷持久化 SQLite）：

1. 服务器安装 Docker 与 Docker Compose，拉取代码。
2. 配置环境变量（compose 已透传）：`DEEPSEEK_API_KEY`（必需）、
   `DASHSCOPE_API_KEY`（语音 ASR/CosyVoice，欠费则语音降级）、
   可选 `CORS_ORIGINS` 追加自有网页域名。
3. `cd deploy && docker compose up -d --build`，服务监听 8765。
4. 手机与服务器连通性验证：浏览器访问 `http://<服务器IP>:8765/health`。
5. APK 登录页填服务器地址 `http://<服务器IP>:8765` 即可使用。
6. 正式环境建议：Nginx/Caddy 反代 + 域名 + Let's Encrypt 证书（HTTPS/WSS），
   安全组只放行 80/443；此时 APK 内地址填 `https://你的域名`。
