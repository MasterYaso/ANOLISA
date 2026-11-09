import QtQuick
import QtQuick.Layouts

// Shared by the native popup and the local renderer; previews use this exact view.
Rectangle {
    id: panel
    objectName: "assistantPanel"
    property real unit: 1
    property string typeface: "Sans Serif"
    property string page: "home"
    property var report: ({})
    property bool busy: false
    property string failure: ""
    readonly property var setupState: report.setup || ({})
    readonly property var coshState: report.cosh || ({})
    readonly property var qoderState: report.qoder || ({})
    signal actionRequested(string action)
    signal navigateRequested(string page)
    signal closeRequested()
    signal refreshRequested()
    implicitWidth: 400 * unit
    implicitHeight: 58 * unit + body.implicitHeight + 18 * unit + 40 * unit
    color: "#21262c"
    radius: 16 * unit
    border.color: "#3a4145"
    border.width: 1

    function count(value) {
        return value.toLocaleString(Qt.locale("en_US"), "f", 0)
    }
    function metric(component, field) {
        var data = report[component] || ({})
        return data.available && typeof data[field] === "number" ? count(data[field]) : "—"
    }
    function componentStatus(component) {
        if (!report.ok) return "状态未知"
        var data = report[component] || ({})
        if (data.state === "empty" || (data.available && data.checked === 0)) return "暂无记录"
        return data.available ? "有记录" : "不可用"
    }
    function choiceLabel(value) {
        if (value.verification && value.verification.checked_at)
            return (value.verification.result === "passed" ? "用户确认收到回答" : "用户报告连接失败")
                + " · " + value.verification.checked_at
        if (value.reported_configured) return "已手动确认，连接待验证"
        if (value.choice === "skipped") return "已跳过，可补配"
        if (value.choice === "configure") return "已处理，连接待验证"
        return "待设置"
    }

    component Label: Text {
        color: "#eef1ed"
        font.family: panel.typeface
        font.pixelSize: 13 * panel.unit
        wrapMode: Text.Wrap
        textFormat: Text.PlainText
        lineHeight: 1.45
    }
    component ComponentRow: Rectangle {
        id: row
        property string name: ""
        property string description: ""
        property string symbol: ""
        property string destination: ""
        width: parent.width
        height: 62 * panel.unit
        color: hover.containsMouse ? "#29312f" : "transparent"
        radius: 7 * panel.unit
        Accessible.role: Accessible.Button
        Accessible.name: name + "，" + description
        Accessible.onPressAction: panel.navigateRequested(destination)
        activeFocusOnTab: true
        Keys.onReturnPressed: panel.navigateRequested(destination)
        Keys.onSpacePressed: panel.navigateRequested(destination)
        Label {
            x: 6 * panel.unit
            anchors.verticalCenter: parent.verticalCenter
            text: row.symbol
            color: "#b7d9be"
            font.pixelSize: 20 * panel.unit
        }
        Column {
            x: 38 * panel.unit
            anchors.verticalCenter: parent.verticalCenter
            spacing: 2 * panel.unit
            Label { text: row.name; font.pixelSize: 14 * panel.unit; font.weight: Font.DemiBold }
            Label { text: row.description; color: "#a3ada8"; font.pixelSize: 12 * panel.unit }
        }
        Label {
            anchors.right: parent.right
            anchors.rightMargin: 10 * panel.unit
            anchors.verticalCenter: parent.verticalCenter
            text: panel.componentStatus(row.destination) + "  ›"
            color: "#a3b7a9"
            font.pixelSize: 12 * panel.unit
        }
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: "#30373b" }
        MouseArea {
            id: hover
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: panel.navigateRequested(row.destination)
        }
    }

    RowLayout {
        x: 18 * panel.unit
        y: 13 * panel.unit
        width: parent.width - 36 * panel.unit
        spacing: 8 * panel.unit
        Label { text: "✦"; color: "#b7d9be"; font.pixelSize: 23 * panel.unit }
        Label {
            objectName: "productTitle"
            text: "ANOLISA - AI 助手"
            font.pixelSize: 16 * panel.unit
            font.weight: Font.DemiBold
            fontSizeMode: Text.HorizontalFit
            minimumPixelSize: 12 * panel.unit
            wrapMode: Text.NoWrap
            elide: Text.ElideRight
            Layout.minimumWidth: 0
            Layout.fillWidth: true
        }
        ActionButton {
            objectName: "settingsButton"
            text: panel.page === "home" ? "⚙" : "‹ 返回"
            textSize: panel.page === "home" ? 18 : 12
            quiet: true; unit: panel.unit; typeface: panel.typeface
            onClicked: panel.navigateRequested(panel.page === "home" ? "settings" : "home")
        }
        ActionButton {
            objectName: "closeButton"
            text: "×"; quiet: true; unit: panel.unit; typeface: panel.typeface
            textSize: 20
            onClicked: panel.closeRequested()
        }
    }
    Flickable {
        id: viewport
        objectName: "panelViewport"
        x: 18 * panel.unit
        y: 58 * panel.unit
        width: parent.width - 36 * panel.unit
        height: Math.max(0, parent.height - y - 48 * panel.unit)
        contentWidth: width
        contentHeight: body.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        onHeightChanged: contentY = Math.min(contentY, Math.max(0, contentHeight - height))
        Connections { target: panel; function onPageChanged() { viewport.contentY = 0 } }
        Column {
            id: body
            width: viewport.width
            spacing: 12 * panel.unit
            Label { visible: panel.failure !== ""; width: parent.width; text: panel.failure; color: "#efd199" }
            Column {
                visible: panel.page === "home" && panel.setupState.needs_prompt === true
                width: parent.width
                spacing: 8 * panel.unit
                Label { width: parent.width; text: "第一次使用"; font.bold: true }
                Label { width: parent.width; text: "cosh 和 Qoder 分别设置，两项都可以稍后完成。"; color: "#a3ada8" }
                RowLayout {
                    width: parent.width
                    ActionButton {
                        objectName: "setupButton"
                        text: "开始设置"; unit: panel.unit; typeface: panel.typeface
                        enabled: !panel.setupState.running
                        onClicked: panel.actionRequested("setup")
                    }
                    ActionButton {
                        objectName: "deferButton"
                        text: "稍后"; quiet: true; unit: panel.unit; typeface: panel.typeface
                        enabled: !panel.setupState.running
                        onClicked: panel.actionRequested("defer")
                    }
                }
            }
            Column {
                visible: panel.page === "home" && panel.setupState.needs_prompt !== true
                width: parent.width
                spacing: 12 * panel.unit
                Label { width: parent.width; text: "开始 AI 工作，查看任务和增强效果。"; color: "#a3ada8" }
                Rectangle {
                    width: parent.width
                    implicitHeight: work.implicitHeight + 28 * panel.unit
                    height: implicitHeight
                    radius: 10 * panel.unit
                    color: "#262c31"
                    border.color: "#363e42"
                    Column {
                        id: work
                        x: 14 * panel.unit; y: 14 * panel.unit
                        width: parent.width - 28 * panel.unit
                        spacing: 9 * panel.unit
                        Label { text: "开始工作"; color: "#a3b7a9"; font.pixelSize: 11 * panel.unit }
                        Label { text: "打开工作终端"; font.pixelSize: 18 * panel.unit; font.weight: Font.DemiBold }
                        Label { width: parent.width; text: "cosh · " + panel.choiceLabel(panel.coshState); color: "#a3ada8" }
                        ActionButton {
                            objectName: "coshButton"
                            width: parent.width
                            text: "打开工作终端 →"
                            primary: true; unit: panel.unit; typeface: panel.typeface
                            onClicked: panel.actionRequested("cosh")
                        }
                    }
                }
                ActionButton {
                    objectName: "qoderButton"
                    width: parent.width
                    quiet: true; unit: panel.unit; typeface: panel.typeface
                    text: panel.qoderState.installation !== "compatible" || panel.qoderState.configuration === "missing"
                        ? "设置 Qoder →" : panel.qoderState.enhancement === "unavailable"
                        ? "检查 Qoder →" : "用 Qoder 开始任务 →"
                    onClicked: {
                        if (panel.qoderState.installation !== "compatible" || panel.qoderState.configuration === "missing")
                            panel.actionRequested("setup-qoder")
                        else if (panel.qoderState.enhancement === "unavailable")
                            panel.navigateRequested("settings")
                        else
                            panel.actionRequested("qoder")
                    }
                }
                Label {
                    width: parent.width
                    text: "Qoder 的任务与确认在终端查看，增强效果在下方查看。"
                    color: "#a3ada8"; font.pixelSize: 11 * panel.unit
                }
                RowLayout {
                    width: parent.width
                    Label { text: "组件与看板"; color: "#a3ada8"; font.pixelSize: 12 * panel.unit; Layout.fillWidth: true }
                    ActionButton { text: "设置"; quiet: true; unit: panel.unit; typeface: panel.typeface; onClicked: panel.navigateRequested("settings") }
                }
                Column {
                    width: parent.width
                    ComponentRow { objectName: "securityRow"; name: "sec-core"; description: "安全检查"; symbol: "◇"; destination: "security" }
                    ComponentRow { objectName: "tokenlessRow"; name: "Tokenless"; description: "降低词元开销"; symbol: "≋"; destination: "tokenless" }
                }
            }
            Column {
                visible: panel.page === "settings"
                width: parent.width
                spacing: 10 * panel.unit
                Label { text: "设置"; font.pixelSize: 18 * panel.unit; font.bold: true }
                Label {
                    width: parent.width
                    text: "cosh · " + panel.choiceLabel(panel.coshState) + "\nQoder · "
                        + panel.choiceLabel(panel.qoderState)
                        + (panel.qoderState.version ? " · " + panel.qoderState.version : "")
                        + (panel.qoderState.choice === "configure"
                            ? (panel.qoderState.auth_mode === "pat" ? " · 插件保存 PAT" : " · 在 Qoder CLI 中配置")
                            : "")
                    color: "#a3ada8"
                }
                Label {
                    width: parent.width
                    visible: panel.qoderState.enhancement === "unavailable"
                    text: "安全检查或安装配置不可用。运行检查查看原因。"
                    color: "#efd199"
                }
                ActionButton { objectName: "setupCoshButton"; text: "设置 cosh"; width: parent.width; unit: panel.unit; typeface: panel.typeface; onClicked: panel.actionRequested("setup-cosh") }
                ActionButton { objectName: "setupQoderButton"; text: "设置 Qoder"; width: parent.width; unit: panel.unit; typeface: panel.typeface; onClicked: panel.actionRequested("setup-qoder") }
                ActionButton { objectName: "doctorButton"; text: "运行检查"; width: parent.width; unit: panel.unit; typeface: panel.typeface; onClicked: panel.actionRequested("doctor") }
                Label { visible: panel.setupState.running === true; width: parent.width; text: "已有设置操作，请返回原终端。"; color: "#a3ada8" }
            }
            Column {
                visible: panel.page === "security" || panel.page === "tokenless"
                width: parent.width
                spacing: 14 * panel.unit
                Label {
                    width: parent.width
                    text: panel.page === "security" ? "sec-core · 安全检查" : "Tokenless · 降低词元开销"
                    font.pixelSize: 18 * panel.unit; font.weight: Font.DemiBold
                }
                Rectangle {
                    width: parent.width
                    height: metrics.implicitHeight + 28 * panel.unit
                    color: "#262c31"; radius: 10 * panel.unit; border.color: "#363e42"
                    Column {
                        id: metrics
                        x: 14 * panel.unit; y: 14 * panel.unit
                        width: parent.width - 28 * panel.unit
                        spacing: 9 * panel.unit
                        Label { text: panel.page === "security" ? "近期扫描记录" : "工具内容估算减少"; color: "#a3ada8" }
                        Label {
                            objectName: "metricValue"
                            width: parent.width
                            text: panel.page === "security" ? panel.metric("security", "checked") + " 条" : panel.metric("tokenless", "saved") + " 词元"
                            color: "#b7d9be"; font.pixelSize: 28 * panel.unit; font.weight: Font.DemiBold
                        }
                        Label {
                            width: parent.width
                            text: panel.page === "security" ? "发现风险 " + panel.metric("security", "risks") + " 次\n执行阻断 " + panel.metric("security", "blocked")
                                : "处理前 " + panel.metric("tokenless", "before") + " → 处理后 " + panel.metric("tokenless", "after") + "\n记录 " + panel.metric("tokenless", "records") + " 条"
                            color: "#a3ada8"
                        }
                    }
                }
                Label {
                    width: parent.width
                    text: panel.page === "security"
                        ? (((panel.report.security || ({})).recent_risks || []).map(function(item) {
                            return (item.timestamp || "时间未知") + " · " + (item.verdict === "deny" ? "拒绝建议" : "风险提示")
                        }).join("\n") || (panel.componentStatus("security") === "不可用" ? "暂时无法读取扫描记录。" : "暂无风险详情。"))
                        : "估算的是交给模型的工具内容，不是模型总消耗，也不代表账单节省。"
                    color: "#a3ada8"
                }
                Label {
                    width: parent.width
                    text: panel.page === "security"
                        ? "最近最多 200 条服务扫描记录。当前接入 Qoder 的 Bash 工具。执行阻断需要独立证据。"
                        : "当前用户最近最多 200 条记录。估算值用于比较工具内容。"
                    color: "#a3ada8"; font.pixelSize: 12 * panel.unit
                }
                Label {
                    width: parent.width
                    text: panel.componentStatus(panel.page) + " · " + ((panel.report[panel.page] || ({})).sampled_at || "更新时间未知")
                    color: "#a3ada8"; font.pixelSize: 11 * panel.unit
                }
                ActionButton { width: parent.width; text: "刷新"; quiet: true; unit: panel.unit; typeface: panel.typeface; onClicked: panel.refreshRequested() }
                ActionButton {
                    objectName: "detailsButton"
                    width: parent.width; text: "在终端查看完整详情 →"; unit: panel.unit; typeface: panel.typeface
                    onClicked: panel.actionRequested(panel.page === "security" ? "security" : "tokens")
                }
            }
            Column {
                visible: panel.page === "help"
                width: parent.width
                spacing: 12 * panel.unit
                Label { text: "插件说明"; font.pixelSize: 18 * panel.unit; font.weight: Font.DemiBold }
                Label { text: "在终端运行"; font.weight: Font.DemiBold }
                Label { objectName: "helpCommands"; width: parent.width; text: "anolisa-omarchy help\n查看组件用途和使用入口。\n\nanolisa-omarchy status\n查看组件是否安装、配置和运行。\n\nanolisa-omarchy doctor\n查看安装和运行问题。" }
                Label { text: "组件能做什么"; font.weight: Font.DemiBold }
                Label { width: parent.width; text: "Qoder · 帮你读文件、执行命令和改代码。" }
                Label { width: parent.width; text: "cosh · 带 AI 的工作终端。用 /auth 配模型，单独输入 /agent 后提问。" }
                Label { width: parent.width; text: "Tokenless · 精简 Qoder 的部分工具输出，减少发给模型的词元。" }
                Label { width: parent.width; text: "sec-core · 检查 Qoder 准备执行的 Bash 命令，记录发现的风险。" }
            }
        }
    }
    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width
        height: 40 * panel.unit
        color: "transparent"
        Rectangle { width: parent.width - 2; x: 1; height: 1; color: "#30373b" }
        Label {
            x: 18 * panel.unit; anchors.verticalCenter: parent.verticalCenter
            text: panel.busy ? "正在更新…" : "ANOLISA · 本机数据"
            color: "#81978a"; font.pixelSize: 10 * panel.unit
        }
        ActionButton {
            objectName: "helpButton"
            anchors.right: parent.right; anchors.rightMargin: 12 * panel.unit
            anchors.verticalCenter: parent.verticalCenter
            text: "插件说明"; quiet: true; unit: panel.unit; typeface: panel.typeface
            onClicked: panel.navigateRequested("help")
        }
    }
}
