# ANOLISA - AI 助手（Omarchy 实验版）

[English](README.md)

Omarchy 原生顶栏下拉窗，提供 cosh 工作终端和受 AW 管理的 Qoder 入口。
安全检查与词元看板读取组件的公共命令接口，不另造统计数据库。

## 安装 0.1.2

在 Omarchy x86_64 桌面打开终端，用当前桌面用户在克隆的仓库根目录运行。

```bash
cd distribution/omarchy
bash ./install
```

脚本从 GitHub Release 的 `omarchy-v0.1.2` 下载归档，按本目录的 `SHA256SUMS`
校验后运行安装器。手里已有安装包时，可以给同一个脚本加上
`--archive /path/to/anolisa-omarchy-0.1.2.tar.gz`。

用当前登录桌面的普通用户解压候选包，执行 `./install`。
安装器部署随包程序、启用原生顶栏插件，并通过一次 sudo 安装系统级安全服务。
安全守护进程从 root 管理的目录运行；笔记本不需要编译。
安装后在顶栏分别设置 cosh 和 Qoder。两项都可以稍后完成。
Qoder 是可选组件。缺失时，向导提供推荐版本 1.1.84（默认）、官方最新版和稍后设置三个选项。
可以在 Qoder CLI 里登录，也可以在 ANOLISA 向导里用隐藏输入填写 Qoder PAT。
面板右下角的「帮助」列出常用命令。

包内包含 cosh、AW、两个 AW Provider、sec-core 代码检查运行时、Tokenless
。Qoder CLI 由用户单独从官方渠道下载，遵循其自身使用条款。保存令牌只表示本地已配置，
不表示已成功调用模型。cosh 使用自己的 `/auth` 配置模型。

`anolisa-omarchy setup` 打开向导。`--component cosh` 或 `--component qoder`
只设置一项。`help` 介绍组件用途，`status` 查看当前状态，`doctor` 显示排障提示。
`status --json` 和 `doctor --json` 继续提供机器可读输出。

- [使用和验收](USER_GUIDE_zh.md)
- [源码构建与打包](BUILDING.md)

## 移除顶栏插件

```bash
omarchy plugin remove community.anolisa
```

如果还要停用系统安全服务并取消开机启动，运行
`sudo systemctl disable --now anolisa-omarchy-security.service`。
这两步会保留已安装程序、账户配置和统计，方便重装。

## 界面语言

当前源码和原生包候选版默认使用英文，中文桌面也不改变这一默认值。
打开 **Settings → Language / 语言**，选择 **English** 或 **简体中文**。
选择按当前用户保存，新打开的配置终端和 cosh 会跟随切换；已有会话继续运行。
Qoder 保留自己的界面语言。终端中也可运行 `anolisa-omarchy language en-US`
或 `anolisa-omarchy language zh-CN`。这些功能需要从当前源码生成的候选包；
请使用匹配的 0.1.2 候选包或 Release 归档。

## 开发边界

本目录负责发行集成，复用仓库中的组件和 Provider，不复制它们的业务逻辑。
在 Linux 的 Python 3.11.6 环境运行 `python -m pytest distribution/omarchy/tests`。
提交前遵守根目录的贡献与文档规范。

本地视觉检查可在开发环境安装 `PySide6-Essentials==6.10.1`，运行
`python distribution/omarchy/tests/check_panel.py --output /tmp/anolisa-panel-check`。
它渲染实际 QML、检查鼠标动作与无数据状态并导出 PNG，不连接虚拟机，
不能替代 Quickshell 原生弹窗宿主验收。PySide6 不是笔记本运行插件所需的依赖。

下拉窗负责入口和展示；Qoder 入口通过配置文件调用 `aw run`。
增强仅覆盖已配置的原生工具接点，不等于操作系统沙箱。
cosh 不会自动将自然语言任务路由到这个 Qoder 进程。
本版关闭终端会结束前台会话，不提供后台任务恢复承诺。

面板采用固定的深灰与薄荷绿配色，避免桌面主题改变主按钮层次。
`AssistantPanel.qml` 为可独立渲染的实际视图，`Widget.qml` 负责原生顶栏与运行时接线。
`AssistantPopup.qml` 改编自 Omarchy 的 `shell/Ui/PopupCard.qml`，保留定位、焦点和外部
点击关闭的行为，按 MIT 许可使用；声明保存在 `plugin/OMARCHY-LICENSE`。

许可：[Apache-2.0](../../LICENSE)，上述 Omarchy 代码使用 MIT；随包组件保留各自许可。

## 按需安装 Qoder

打开 **设置 → Qoder 版本**，可以安装或切换版本。默认推荐固定的 1.1.84。
选择 **最新版** 时，安装器读取官方版本清单并校验 SHA-256；将来尚未验证的构建会明确标注。
受管程序不会静默更新；需要更新或切回推荐版时，再使用同一入口。

```bash
anolisa-omarchy qoder-install --channel recommended
anolisa-omarchy qoder-install --channel latest
```

程序保存在 `$XDG_DATA_HOME/anolisa-omarchy/qoder`；未设置时为
`~/.local/share/anolisa-omarchy/qoder`。账户仍保存在原有的私有配置目录，切换版本
和升级插件均会保留。下载需要访问 Qoder 官方 HTTPS 服务，终端会显示进度。
安装器会核对归档校验值和程序实际报告的版本。

原生 Arch 候选包的安装命令为：

```bash
sudo pacman -U ./anolisa-omarchy-0.1.2-1-x86_64.pkg.tar.zst
anolisa-omarchy enable
```

卸载原生包前先执行 `anolisa-omarchy disable`，再执行
`sudo pacman -R anolisa-omarchy`。单独下载的 Qoder、账户配置和统计会保留。
归档安装和原生系统包是两种安装方式，切换前先移除原有方式。
