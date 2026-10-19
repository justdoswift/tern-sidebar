# Tern Sidebar

Tern 原生侧栏插件，当前发布版本 **0.3.0**。会话折叠与倒序功能已在 macOS 的 Tern **0.9.4（b9ef74c）** 上验证；无需 Node.js、后台服务或额外 OMP 扩展。

## 功能

- 垂直侧栏底部的 `Filter tabs` 右侧放置小号原生 **新建 tab（+）** 图标；在当前 session 内创建 tab，继承当前 pane 的工作目录。不再占用单独一行，顶部也不重复显示加号。
- **Ctrl + Option + N**（其他平台为 Ctrl + Alt + N）仍用于新建并切换 session，继承当前 pane 的工作目录；没有可用目录时由 Tern 使用默认目录。也可在命令面板搜索 `新建会话 / New session`。
- 会话按 Tern 保存顺序**倒序**显示，新建会话排在最上面；点击、切换会话不再改变位置。不改 session 名称、ID、tab 顺序或服务端数据；多 host 时保留 host 分组，各组内倒序排列。
- 默认只显示最新 **3 个 session**，第 4 个起收进搜索框上方的 **“较早会话（数量） / Older”** 入口；再次点击可收起。数量按 session 计算，不是 tab 数；多 host 时每个 host 保留最新 3 个。通过快捷键／会话切换器进入较早会话时自动展开该区域。展开状态只在当前窗口的插件内存中保留，重载后重新按默认规则显示；不会关闭会话或清除未读绿点。
- `Tern ▾` 这类 session 分组标题使用 14px 半粗体、主文字色和细分隔线，保持紧凑的 32px 标题行，不添加整块底色或加重下方 tab 的选中态。展开／折叠箭头保持可见；长分组名省略显示，为箭头与原生计数留出空间。
- 移除会话条目左侧的程序图标，保留标题和快捷键。任务工作时，**右侧原颜色圆点的位置**显示旋转缺口圆环；后台任务结束后变成绿色未读圆点，点击进入对应条目即清除。当前正在看的条目完成不留绿点；同一 session 内的其他 tab 也按后台条目处理。等待输入不算完成，新一轮工作会重新显示 loading。
- 顶部 **Switch session** 右侧增加侧栏展开／折叠图标。点击在“固定展开”和 Tern 原生“自动隐藏”之间切换；折叠后图标与会话切换入口仍留在顶部，终端可用宽度随之增加。鼠标移至左边缘可临时展开，再点图标可固定展开。操作不切换会话、不清除未读绿点。
- Tiles / Float 的头像、当前会话从窗口左侧开始排列，保留 macOS 窗口按钮空间。较长的顶部会话名省略显示，完整名称仍在原生提示中；Rail / Studio 展开时保留原生标题栏位置，折叠时保留可操作的顶部入口。
- 继承 Tern 主题；支持侧栏自动隐藏、状态栏开关和系统减少动态效果设置。

水平标签栏仍在顶部显示原生 `+`；按钮始终是 **新建 tab**，不会改成新建 session。

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

需要调整快捷键时，在 Tern 的快捷键设置中绑定动作 `plugin.tern-sidebar.new_session`、`plugin.tern-sidebar.toggle_sidebar` 或 `plugin.tern-sidebar.toggle_older_sessions`。侧栏开关可从命令面板搜索 `展开／折叠侧栏 / Toggle sidebar`；较早会话入口可搜索 `展开／收起较早会话 / Show or hide older sessions`。这两个开关没有额外占用默认快捷键；插件默认绑定不会覆盖 Tern 已有的系统/预设快捷键。

## 兼容边界

受测的 Tern SDK 尚未提供 sidebar/titlebar 挂载点、原生分组折叠设置、session 创建时间或 session ID 的 DOM 属性。本插件只使用公开 Luau API 和已核对的原生 CSS 结构：

- `window.luau` 注册新建动作，读取 session/host/tab/pane 元数据并更新样式。原生标题格式化回调的 busy 变化触发刷新，但返回 `nil`，不修改标题；生命周期事件后合并更新，每秒补查其他窗口或 daemon 带来的变化。它不读取聊天、终端输出或模型内容。
- 未读状态按 tab ID 保存在当前窗口的插件内存中。只有实际观察到 busy → idle 的后台转换才留绿点；绿点表示“工作已结束、尚未查看”，不保证命令成功。进入对应 tab 后清除，关闭 tab 时移除，重载插件或重启窗口后不保留历史标记。
- `order.luau` 将原生“当前 session 优先”的绘制顺序映射为保存顺序的倒序，保留 host 分组；较早会话通过有完整数量校验的位置选择器隐藏，不反转原生分组的展开／折叠状态。搜索筛掉部分 session 或 tab 后，位置索引不能可靠识别条目：**缩减后的 session 结果保留 Tern 原生顺序并展示匹配组，无法安全定位的未读圆点暂不绘制**。清空筛选后恢复倒序、折叠与未读圆点；筛选不清除未读状态，也不把位置或圆点错误地套到另一个条目上。若搜索仍包含全部分组，仍可用“较早会话”入口查看其余匹配项。
- Tern 0.9.4 关闭 session 后可能保留旧导航 DOM；无插件的独立窗口也已复现。列表结构与 API 数量不一致时，本插件暂停位置排序／隐藏规则，避免把别的会话误收起；不声称修复 Tern 本身的关闭后刷新问题。
- `sidebar.css` 使用原生 `aria-label` 的 ` · working` 后缀判断工作状态，重用 `.tn-tc` 圆点。侧栏中的原颜色标签让位给 loading/未读状态，但不修改保存的 tab 颜色；已读空闲条目不留颜色圆点。运行中的普通 shell 命令同样遵循 Tern 的工作状态，不把仅仅启动了 OMP 进程等同于生成中。
- 新建 tab 按钮直接复用原生 `.tb-add`，只在垂直侧栏模式下通过 CSS 移到搜索框右侧；跟随侧栏自动隐藏。无需 status segment，也不强制开启或改写用户的状态栏、主题、侧栏偏好。
- 顶部侧栏开关及底部“较早会话”入口使用独立的可点击原生 status segment，通过 CSS 定位；状态栏关闭时仍可操作，不开启状态栏或展示其他插件的隐藏状态项。控件保留中英双语可访问名称，水平标签栏模式不显示，底部入口随侧栏自动隐藏。只有点击顶部开关才通过 `cx.settings` 更新 `tabs_autohide`，由 Tern 持久保存；插件载入不强制改变已有偏好。

适用于原生桌面窗口；Web 客户端不运行 window 插件，不在支持范围内。原生 CSS 类名和可访问性文案不是稳定 SDK：升级 Tern 后应重新运行 smoke，而不是假定版本兼容。未验证 Windows/Linux 实机。

## 验证

插件没有构建步骤。原生集成 smoke 需要 `python3`、PATH 中的 `tern` 和已登录的桌面 Tern：

```sh
python3 test/smoke.py --native
```

**这条命令会短暂打开独立测试窗口。** 它使用临时插件副本、配置、daemon、socket 和会话，只停止自己启动的进程，不连接日常会话。截图和日志输出到 Git 忽略的 `artifacts/smoke/`，不会因写入源码目录而重载受测插件。

覆盖：底部加号创建 tab、快捷键创建 session、工作目录继承、新会话排在顶部、点击切换后位置不变、3／4／5 个 session 的折叠边界、按 session 而非 tab 数折叠、鼠标与命令面板展开／收起、进入隐藏会话时展开、重载后恢复默认折叠、收起期间后台完成仍保留未读绿点、筛选较早会话、计数减少后移除入口、列表数量不一致时不误隐藏现存会话，以及原有 OMP 工作/等待/空闲转换、跨 session 与同 session 后台 tab 的已读状态、四种布局、顶部侧栏开关、状态栏开关、自动隐藏、搜索框与加号对齐、水平标签栏和亮色/暗色短窗口检查。OMP 状态来自 `test/omp-progress.jsonl` 的合成 OSC/TSP 回放；不发起模型请求，不使用真实会话内容。

排序的端到端验证使用真实原生窗口。`tern serve` 固定时钟及事件驱动行为不同，不能用一次 headless 截图代替原生切换验证。

## SDK 参考

- [插件 API 与双上下文](https://docs.stencil.so/tern/)
- [Chrome 与样式](https://docs.stencil.so/tern/guides/chrome.md)
- [支持的 CSS 子集](https://docs.stencil.so/tern/styles/css.md)
- [原生脚本与截图](https://docs.stencil.so/tern/scripts/index.md)

## 许可证

[MIT](LICENSE) © 2026 Ge Peng。允许使用、修改及再分发；保留许可证与版权声明。
