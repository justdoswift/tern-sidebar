# tern-sidebar

Tern 原生侧栏插件。已在 macOS 的 Tern **0.8.4（6b4535f）** 上验证；无需 Node.js、后台服务或额外 OMP 扩展。

## 功能

- 侧栏底部常驻 **新建会话**。一键新建并切换，继承当前 pane 的工作目录；没有可用目录时由 Tern 使用默认目录。
- **Ctrl + Option + N**（其他平台为 Ctrl + Alt + N）执行同一个动作。也可在命令面板搜索 `新建会话 / New session`。
- 完整会话列表按 Tern 保存的 session 顺序显示，不再把刚选中的 session 提到最上方。新会话排在已有会话后；不改 session 名称、ID、tab 顺序或服务端数据。
- 任务工作时，条目**右侧原颜色圆点的位置**显示旋转缺口圆环。左侧程序图标、标题和快捷键保留；等待输入或空闲后恢复 Tern 原有标记。后台 session 中的任务也会显示。
- 垂直侧栏的 Tiles / Float 布局中，头像、当前会话、加号从窗口左侧开始排列，保留 Tern 对 macOS 窗口按钮的原有避让。Rail / Studio 不改原生标题栏布局。
- 继承 Tern 主题；支持侧栏自动隐藏、状态栏开关和系统减少动态效果设置。

顶部 `+` 仍是 **新建 tab**，不会把原有动作偷偷改成新建 session。

## 安装

在 Tern 中从 GitHub 安装：

```sh
tern plugin install https://github.com/justdoswift/tern-sidebar
tern plugin list
```

卸载安装的副本：

```sh
tern plugin remove tern-sidebar
```

开发时可克隆仓库并链接源码目录：

```sh
git clone https://github.com/justdoswift/tern-sidebar.git
tern plugin link "$PWD/tern-sidebar"
```

安装副本与源码链接二选一；切换方式前先移除当前副本或解除链接。链接保留源码位置，修改后执行 `tern plugin reload` 即可更新。也可以在设置的 Plugins 页面管理它。关闭插件不结束会话、不删除数据、不修改颜色标签。

解除源码链接：

```sh
tern plugin unlink tern-sidebar
```

需要调整快捷键时，在 Tern 的快捷键设置中绑定动作 `plugin.tern-sidebar.new_session`。插件默认绑定不会覆盖 Tern 已有的系统/预设快捷键。

## 兼容边界

Tern 0.8.4 尚未提供 sidebar 挂载点、session 排序设置或 session ID 的 DOM 属性。本插件只使用公开 Luau API 和已核对的原生 CSS 结构：

- `window.luau` 注册新建动作，读取 session/host 元数据并更新布局样式。生命周期事件后合并更新；每秒补查其他窗口或 daemon 带来的变化。它不读取聊天、终端输出或模型内容。
- `order.luau` 将原生“当前 session 优先”的绘制顺序映射回稳定顺序，保留 host 分组。搜索筛掉部分 session 后，位置索引不能可靠识别每个 session，因此**筛选结果保留 Tern 原生顺序**；清空筛选后恢复固定顺序，避免把位置错误地套到另一个 session 上。
- `sidebar.css` 使用原生 `aria-label` 的 ` · working` 后缀判断工作状态，重用 `.tn-tc` 圆点。圆点原本表示颜色标签，不等于工作状态。运行中的普通 shell 命令同样遵循 Tern 的工作状态；不把仅仅启动了 OMP 进程等同于生成中。
- 新建按钮由原生可点击 status segment 提供，通过 CSS 放到侧栏底部。即使状态栏关闭也可点击；不强制开启或改写用户的状态栏、主题、侧栏偏好。

适用于原生桌面窗口；Web 客户端不运行 window 插件，不在支持范围内。原生 CSS 类名和可访问性文案不是稳定 SDK：升级 Tern 后应重新运行 smoke，而不是假定版本兼容。未验证 Windows/Linux 实机。

## 验证

插件没有构建步骤。原生集成 smoke 需要 `python3`、PATH 中的 `tern` 和已登录的桌面 Tern：

```sh
python3 test/smoke.py --native
```

**这条命令会短暂打开独立测试窗口。** 它建立自己的临时配置、daemon、socket 和会话，只停止自己启动的进程，不连接日常会话；输出截图和日志到 Git 忽略的 `artifacts/smoke/`。

覆盖：按钮与快捷键创建、工作目录继承、点击切换后位置不变、插件重载、筛选恢复、OMP 工作/等待/空闲转换、后台 session 的转圈、左侧标题栏、状态栏和侧栏自动隐藏，以及亮色/暗色短窗口。OMP 状态来自 `test/omp-progress.jsonl` 的合成 OSC/TSP 回放；不发起模型请求，不使用真实会话内容。

排序的端到端验证使用真实原生窗口。`tern serve` 固定时钟及事件驱动行为不同，不能用一次 headless 截图代替原生切换验证。

## SDK 参考

- [插件 API 与双上下文](https://docs.stencil.so/tern/)
- [Chrome 与样式](https://docs.stencil.so/tern/guides/chrome.md)
- [支持的 CSS 子集](https://docs.stencil.so/tern/styles/css.md)
- [原生脚本与截图](https://docs.stencil.so/tern/scripts/index.md)

## 许可证

[MIT](LICENSE) © 2026 Ge Peng。允许使用、修改及再分发；保留许可证与版权声明。
