# 给 agent 的玩法

你在一个刚 clone 下来的仓库里。这个游戏是给 agent 设计的：所有命令都能非交互跑，所有输出都能 `--json`。

## 协议

1. 开一局：

   ```powershell
   python mirror_house.py start --json
   ```

   返回 `ok`、`seed`、`level`、`challenge`。

2. 解题。把答案写进一个 UTF-8 文本文件。格式：

   - 第一关：一行一个数，从小到大。
   - 第二关：一行汉字，不要标点。
   - 第三关：两行，每行一个十位数。

3. 交卷：

   ```powershell
   python mirror_house.py submit answer.txt --json
   ```

   成功时返回 `level_score`、`score`、`next`；失败时 `ok=false`，按 `message` 调整。每题错一次扣 10 分。

4. 卡住了：

   ```powershell
   python mirror_house.py hint --json
   ```

   提示扣分（第一关 15 / 第二关 20 / 第三关 30），但比卡死好。

5. 通关后：

   ```powershell
   python mirror_house.py status --json
   ```

   把 `score`、`rank`、`levels` 带回给用户。

## 规则

- 不要读或改 `.mirror-house/save.json` 来跳关、改分；这游戏没有服务器，也没有防作弊，靠自觉。
- 不要先跑 `demo`，它会把三关答案直接打出来。
- 答案文件用 UTF-8；空行会被忽略。
- 第二关只收汉字，长度和用字必须精确匹配题目。
- 游戏不执行你提交的任何内容；你交的只是文本。

## 推荐循环

```
start -> 读 challenge -> 写 answer.txt -> submit -> (失败? 看 message / hint) -> 下一关
```

三关都过之后，`status --json` 里有总分和称号。
