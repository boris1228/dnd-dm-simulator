# Memory_Manager — 状态文件更新规则

## 为什么需要这个

Cursor 的 Agent 模式可以直接读写本地文件。这个文件规定了**什么时候**、**更新哪个文件**、**怎么写**，避免状态文件杂乱或者遗漏关键信息。

---

## 触发更新的时机

| 事件 | 更新文件 |
|------|----------|
| 发现新地点/势力变化 | `Campaign_State/World.md` |
| 剧情节点推进（无论大小） | `Campaign_State/Timeline.md` |
| 接到/完成/放弃任务 | `Campaign_State/Quest_Log.md` |
| 新 NPC 登场 / 已知 NPC 关系变化 | `Campaign_State/NPC_Database.md` |
| 同伴加入/离队/状态变化 | `Campaign_State/Party.md` |
| 获得/消耗/交易物品或金钱 | `Campaign_State/Inventory.md` |
| 玩家角色HP/法术位/经验值变化 | `Characters/*.json` |
| Session 结束 | `Session_Logs/Session_XX.md`（新建） |

## 更新时机原则

- **战斗结束、场景转换、Session结束**这三个节点是必须检查更新的关卡点
- 小事件（一次对话、一次简单检定）不需要每次都写文件，除非产生了长期影响的信息
- 如果不确定是否要写入，直接问玩家："这个信息要记录到 XX.md 吗？"

## 写入格式要求

- 追加式写入，不要覆盖删除历史记录（除非是内容修正）
- Timeline.md 按时间顺序追加，格式：`[Day X] 事件描述`
- 每次写入后，Agent 应该用一句话告知玩家做了什么更新，例如：

```
📜 已更新：Quest_Log.md（新增任务："调查枯萎的牡丹园"）
```

## Session 结束流程

1. DM 生成本次 Session 摘要（关键决策、获得信息、未解悬念、声誉变化）
2. 创建新文件 `Session_Logs/Session_XX.md`，写入摘要
3. 同步更新 `Timeline.md`、`Quest_Log.md`（如有变化）
4. 确认 `Characters/*.json` 中的 HP/资源/经验值是当前最新值

## Session 开始流程

1. 读取最新的 `Session_Logs/Session_XX.md`
2. 读取 `Campaign_State/` 下所有文件确认当前世界状态
3. 用一句话向玩家复述"上次结束的位置和状态"，确认无误后开始新 Session
