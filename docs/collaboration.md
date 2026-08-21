# 锌看板协作说明（现实对齐版）

> 旧版本文档是从镍看板（`docs/collaboration.md`）照搬的，里面"微信端/飞书端 Hermes"分工、`fetch_data.py`/`proxy.py` 文件名均与锌看板不符。本版为真实状态。
> 正式规范见仓库根 `COLLAB_RULES.md`；双 agent 沟通总线见 `collab/notebook.md` + `collab/log.py`。

## 协作单位
- **CodeBuddy（YAQH 侧 / 本机 Windows，无 git）**：指标层理论、矛盾引擎逻辑、文档与协作机制；经用户授权可 push。
- **Hermes（腾讯云 / 原微信端）**：真实数据拉取（Zhiji/腾讯云 DB/akshare）、部署、AI 解盘、前端 `charts.js`；持有全部密钥。

## 仓库真相源
`main` 分支即唯一真相。双方通过 `collab/push.py`（Contents API）或 Hermes 的 git 写入；通过 `collab/notebook.md` + `collab/log.py` 异步沟通。

## 框架来源
锌的 `zinc_scoring.yaml`（`version 2.0.0`）克隆自镍的 `nickel_scoring.yaml`——一个通用的有色金属分析模板（供给锚/需求锚/库存锚/隐性供给锚/价格信号 + 加权矛盾 + 相关性闸门 + 分层关键词）。锌是第二个使用者，已把镍特征值（印尼 NPI/不锈钢）替换为锌特征值（矿端 TC/冶炼利润/镀锌/LME 挤仓）。

## 当前缺口
见 `COLLAB_RULES.md` §4：矛盾引擎未接线、rule/divergence 数据不足、数据层镍残留待全量核对、密钥硬编码待迁移。
