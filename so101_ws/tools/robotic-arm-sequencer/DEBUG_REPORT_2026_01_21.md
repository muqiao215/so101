# 🕵️‍♂️ Electron 黑屏故障排查全记录：从“虚无之黑”到“霓虹之光”

**时间**：2026-01-21  
**项目**：Robotic Arm Sequencer  
**问题**：Electron 应用启动后显示纯黑屏，且控制台几乎无报错。  
**结论**：Webpack 配置中的 `target: 'electron-renderer'` 与现代 Electron 安全策略（`contextIsolation: true`）不兼容，导致 bundle 中出现 `Uncaught ReferenceError: global is not defined` 错误，中断了脚本执行。

---

## 1. 故障现象

- **表现**：运行 `npm run electron:dev` 后，Electron 窗口弹出但内容全黑。
- **诡异点**：
  - 即使在浏览器中访问 `http://localhost:8080`，也是黑屏。
  - **DevTools 控制台为空**：没有报错，没有日志，仿佛代码根本没有加载。
  - DOM 结构中只有空的 `<div id="root"></div>`，React 未挂载。
- **初步怀疑**：
  - Preload 脚本未加载？
  - 端口冲突？
  - 依赖包编译问题？

## 2. 排查时间线 (Timeline)

### 🔴 阶段一：Preload 脚本迷踪
- **发现**：主进程 `main.ts` 加载的 preload 路径似乎指向了旧文件。
- **操作**：修正路径，添加大量 `console.log` 到 preload 脚本。
- **结果**：无效。虽然 preload 脚本加载了，但渲染进程依然黑屏。更重要的是，我们添加的日志在渲染进程控制台 **完全不可见**。

### 🟡 阶段二：浏览器环境模拟 (Browser Subagent 介入)
- **思路**：既然 Electron 调试困难，不如直接用浏览器访问 Dev Server (`localhost:8080`)。
- **Web 调试发现**：
  - `renderer.js` 被成功下载（200 OK）。
  - Bundle 文件中 **包含** 了我们写的调试日志 `"=== RENDERER INDEX.TSX STARTED ==="`。
  - **核心矛盾**：代码下载了，代码里有日志，但控制台却 **一片空白**。
  - **推断**：脚本在执行 **第一行代码之前** 就挂了，或者在 Webpack 的模块初始化阶段就崩了。

### 🟡 阶段三：防御性编程失效
- **尝试**：怀疑是 `window.electronAPI` 未定义导致 Crash。
- **操作**：在 `ipc-client.ts` 中添加 Mock API 和防御性检查。
- **结果**：依然黑屏。说明错误发生得比业务逻辑更早。

### 🟢 阶段四：捕捉幽灵报错 (Root Cause Found)
- **突破口**：在修正了 `package.json` 中的环境变量 `NODE_ENV=development` 并重启 Dev Server 后，Electron 的 DevTools 终于吐出了关键报错：
  ```
  Uncaught ReferenceError: global is not defined
      at jsonp chunk loading:42:1
  ```
- **分析**：
  - `global` 是 Node.js 的全局对象，浏览器里叫 `window`。
  - 为什么浏览器环境的代码里会有 `global`？
  - **罪魁祸首**：`webpack.renderer.config.js` 设置了 `target: 'electron-renderer'`。
  - **机制**：这个设置告诉 Webpack：“现在的环境是 Electron 渲染进程，可以使用 Node.js API”。于是 Webpack 在注入运行时代码时，使用了 `global` 对象。
  - **冲突**：但是，我们的 Electron 开启了 `contextIsolation: true`（这是默认的安全设置）。在这种模式下，渲染进程 **没有** Node.js 环境，也就没有 `global` 对象。

## 3. 解决方案

修改 `webpack.renderer.config.js`，将构建目标改为通用 Web 环境，并手动 Polyfill 缺失的变量。

```javascript
module.exports = {
  // 1. 将 target 改为 'web'，不再依赖 Electron 特有环境
  target: 'web', 
  
  resolve: {
    // 2. 屏蔽 Node.js 核心模块的自动 Polyfill
    fallback: {
      "path": false,
      "fs": false,
      "os": false,
    }
  },
  
  plugins: [
    // 3. 手动定义 global 指向 window，骗过依赖包
    new webpack.DefinePlugin({
      'global': 'window',
    }),
  ],
};
```

## 4. 经验总结

1.  **黑屏且无报错** 通常意味着 **构建配置层面的错误**，导致 JS 引擎在解析阶段或模块加载阶段就崩了。
2.  **`target: 'electron-renderer'` 是个陷阱**。在现代 Electron 开发中，推荐将渲染进程视为纯 Web 页面 (`target: 'web'`)，所有 Node.js 能力都通过 `ContextBridge` 暴露，而不是直接在渲染进程混用 Node 代码。
3.  **Dev Server 很重要**：确保 `NODE_ENV=development` 正确设置，否则 Electron 不会加载 localhost URL，也就无法利用 HMR 进行快速调试。

---
*Created by Antigravity Agent*
