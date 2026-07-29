# Campaign — 使用说明

这是一个可以在 Cursor 中直接运行的 D&D 5e 单人 Campaign 引擎，以文件系统作为持久记忆。

## 文件结构

```
Campaign/
├── .cursor/rules/dm-core.mdc   ← Cursor 自动加载，无需手动 @ 引用
├── Rules/                       ← DM 行为规则（相对静态）
├── Campaign_State/              ← 世界当前状态（持续更新）
├── Session_Logs/                ← 历史 Session 摘要（只增不改）
└── Characters/                  ← 玩家角色 JSON 数据
```

## 开始之前

1. 打开 `Characters/player_character.json`，填入你的角色（种族/职业/属性等）
   - 也可以直接让 Cursor Agent 帮你按 5e 规则随机 roll 并填写
2. 确认 `Campaign_State/World.md` 里的设定是否需要调整（当前是白鸦镇边境小镇开局）

## 每次开始一个新 Session

在 Cursor Agent 里直接说：

```
请读取 Campaign_State/ 下所有文件和最新的 Session_Logs/，
确认当前进度后开始新的 Session。
```

## Session 结束时

```
请结束本次 Session，生成摘要写入新的 Session_Logs 文件，
并同步更新 Campaign_State/ 中所有需要变动的文件。
```

## 关于 .cursor/rules

`dm-core.mdc` 设置了 `alwaysApply: true`，意味着每次对话 Cursor 都会自动把 DM 核心规则当作背景注入，不需要手动 @ 提及 `Rules/DM_Core.md`。但涉及具体系统（战斗、NPC、小队变动）时，仍建议明确 @ 对应文件，确保 Agent 完整读取细节规则。
