# ANOLISA - AI 助手

[English](USER_GUIDE.md)

在 Omarchy 顶栏打开 cosh 和 Qoder，在各自的终端工作。在面板中查看 Qoder Bash 安全检查和 Tokenless 处理记录。

## 安装

使用原生 Omarchy 的 Linux x86_64 桌面及 Python 3.11 或以上版本。解压候选包，在图形会话的普通用户终端执行：

```bash
./install
~/.local/bin/anolisa-omarchy status
```

安装器校验候选程序，检查动态库，必要时通过 sudo 补齐能从本机 pacman 文件索引唯一确认的包。它使用 sudo 安装系统安全服务，然后启用顶栏插件。若索引中找不到缺库对应的包，终端会给出缺库名称，确认目标系统的仓库后重试。

`./install --non-interactive` 在 sudo 无法无交互运行时退出。`./install --no-enable` 部署用户文件，跳过系统依赖安装、系统服务和桌面激活。模型认证在安装之后完成。

## 第一次打开

点击顶栏 **ANOLISA**，再点 **开始设置**。配置向导在 Omarchy 默认终端运行。两项可独立跳过。选择 **稍后** 会记住你的选择，之后可从面板的 **设置** 继续。

1. **cosh**。输入 `1` 后先阅读说明，再按 Enter 打开 cosh。在 cosh 中输入 `/auth` 配置模型，用 `/status` 查看状态，输入 `exit` 回到向导。直接按 Enter 可以跳过。
2. **Qoder**。输入 `1` 继续，或按 Enter 跳过。向导自动选用已通过兼容检查的 Qoder CLI 1.1.84。缺失时会询问是否安装固定版本。选 **在 Qoder CLI 中配置** 会打开 Qoder，按提示用浏览器或 PAT 认证。选 **直接输入 Qoder PAT** 时在向导里隐藏输入。选 **稍后设置** 时可以从 **设置 → 设置 Qoder** 继续。升级保留已有的登录方式和凭证。
3. **可选连接检查**。向导可打开一个终端会话。完成一条真实问答后返回向导，可手工记录结果和时间。

## 提问和任务

从面板打开工作终端。**单独输入 `/agent` 并回车**，在 `◆` 输入框输入问题，再按 Enter 发送。第一次可以问“请用中文解释 pwd 的作用，不要执行命令”。Esc 回到普通提示符，`exit` 退出 cosh。

从面板打开 Qoder，在一次性项目目录测试。让 Qoder 通过 Bash 读取一个文本文件，写出 `RESULT.md`，核对文件和组件记录。安全服务不可用时，增强入口停止启动并提示运行检查。

点面板右下角的 **插件说明** 查看常用命令和组件用途。

```bash
~/.local/bin/anolisa-omarchy setup
~/.local/bin/anolisa-omarchy setup --component cosh
~/.local/bin/anolisa-omarchy setup --component qoder
~/.local/bin/anolisa-omarchy auth
~/.local/bin/anolisa-omarchy help
~/.local/bin/anolisa-omarchy status
~/.local/bin/anolisa-omarchy doctor
```

从终端启动同一增强入口时，用 `--` 分隔 Qoder 参数。用 `--native-settings` 传递需要合并的原生设置文件。

```bash
~/.local/bin/anolisa-omarchy qoder
~/.local/bin/anolisa-omarchy qoder --native-settings ./qoder.settings.json -- --version
```

## 看板

- **sec-core** 展示最近最多 200 条服务扫描记录及风险提示。执行阻断需要独立证据，未获得时显示 `—`。
- **Tokenless** 展示当前用户受管存储最近最多 200 条记录的处理前后数量及估算减少量。范围是工具内容。合法零值显示为 `0`，缺数据时显示 `—`。

## 升级和排障

从 demo.2 升级时，直接用新包执行 `./install`。安装器识别旧的受管配置，将原版保存为 `aw.demo2.json`，保留认证文件和组件统计。遇到人工修改的 `aw.json` 时停止切换，并输出候选配置的位置供比较。

一般安装失败会尝试恢复原插件、程序引用、受管配置和系统服务。查看终端提示及当前用户状态目录下的 `anolisa-omarchy/installation.json`，确认失败阶段和恢复结果。系统依赖安装由 pacman 独立记录。若安装中途断电或被强制终止，检查收据和系统服务待恢复记录，再决定重试。
`help` 介绍组件用途和入口，`status` 查看安装与当前状态，`doctor` 查看排障提示。
插件和自动化可以使用 `status --json` 或 `doctor --json`。连接结果由实际问答验证。
