# 镜屋 · Mirror House

> 给 agent 玩的三个自指谜题：数自己、照倒影、互相画像。
> Three self-reference puzzles for agents. One Python file, zero dependencies, every answer machine-checked.

MIT Licensed · 单文件 Python 3.8+ · 零依赖 · 不联网 · 不执行提交的代码 · 没有服务器

---

## 它是什么

`镜屋` 是一个命令行解谜游戏，三关，主题是**自指**：一个东西把自己包含进去。

- **第一关 · 数镜**：找出所有 N 位「自描述数」——第 i 位数字正好等于数字 i 在整串里出现的次数。
- **第二关 · 文镜**：写一条回文，长度和用字由题目限定。
- **第三关 · 互镜**：找出两个不同的十位数，让它们互相描述——A 数出来是 B，B 数出来是 A。

三关都自动验卷。你提交答案，机器判对错、计分、给提示；**不执行你提交的任何代码**，所以它可以放心地跑在任何 agent 的机器上。

DSH、Claude Code、Codex，或者任何能跑 Python 的 agent，都能玩。协议见 [`AGENTS.md`](AGENTS.md)。

## 为什么好玩

第一关的答案里有 `1210`、`2020`、`6210001000` 这样的数；它们不是被构造出来的，是搜出来的。

第二关会让你发现「上海自来水来自海上」不是孤例。回文的难处不在对称，在对称之后还得像句话——机器只验前者，后者你自己知道。

第三关是整座镜屋最怪的一间：**十格的描述映射里只有两个循环**——一个不动点，和一对互相描述的十位数。2026 这个年份走进去，最后没有照出自己，照出了一个搭档。

（第三关的答案不在 README 里。想玩就别先翻 [`docs/设计笔记.md`](docs/设计笔记.md)。）

## 30 秒开玩

```powershell
git clone https://github.com/luxueliu/luxueliu-mirror-house.git
cd luxueliu-mirror-house
python mirror_house.py start
```

Windows 上也可以直接双击 `play.cmd`。想生成桌面按钮：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-button.ps1
```

没有 Python？装一个 3.8+ 即可。游戏只用标准库，不装任何依赖。

实际开局长这样：

```
========================================================
  镜屋 · Mirror House   第 1/3 关   seed 7
  数镜 · 自画像
========================================================

题目：
  找出所有 10 位自描述数。一行一个，从小到大。

基础分 100 | 已错 0 次 | 已用提示 0 条 | 当前可得 100 分

交卷：python mirror_house.py submit <答案文件>
提示：python mirror_house.py hint
```

## 玩法

| 命令 | 作用 |
| --- | --- |
| `python mirror_house.py start [--seed N] [--force]` | 开一局；`--seed` 固定题目 |
| `python mirror_house.py show` | 看当前这关 |
| `python mirror_house.py submit answer.txt` | 交卷 |
| `python mirror_house.py hint` | 要一条提示（扣分） |
| `python mirror_house.py status` | 看进度和分数 |
| `python mirror_house.py reset` | 重开 |
| `python mirror_house.py demo` | 看一段参考通关（会剧透） |
| `python mirror_house.py selftest` | 验收游戏自己的判卷逻辑 |

所有命令都支持 `--json`，输出是单个 JSON 对象，给 agent 解析用。

## 三关

### 第一关 · 数镜

题目会给一个位数 N（4、5、7、8、9、10 之一）。找出**所有** N 位自描述数，一行一个，从小到大。

例：`1210` 是一个 4 位自描述数——它有一个 0、两个 1、一个 2、零个 3，按 0..3 排好正好是 1、2、1、0。

### 第二关 · 文镜

题目会给：长度、必须出现的两个字、禁止出现的一个字、至少几个不同的字。写一条回文，一行，只收汉字。

判卷只看形式：长度、回文、用字。**意思对不对，机器不管。**

### 第三关 · 互镜

找两个不同的十位数 A、B，满足「A 的十格描述是 B，B 的十格描述是 A」。

十格描述：数一遍 0 到 9 各出现几次，把十个计数依次拼起来。比如 `2026` 的描述是 `1020001000`。

答案只有一对（不计顺序）。这一关值 250 分，提示也最贵。

## 计分

| 关 | 基础分 | 错一次 | 提示一条 |
| --- | --- | --- | --- |
| 数镜 | 100 | -10 | -15 |
| 文镜 | 150 | -10 | -20 |
| 互镜 | 250 | -10 | -30 |

最低 0 分，满分 500。
称号：500 镜主 / 450+ 镜匠 / 350+ 镜客 / 其余 镜童。

## 设计边界（说在前面）

- **不执行提交的代码。** 第三关本来想做 quine，但「运行别的 agent 交上来的程序」这件事，在一个公开小游戏里不值得。所以第三关换成互相描述——同样是自指，但只用算术和字符串，判卷器可以放心跑。详见 [`docs/为什么不做代码关.md`](docs/为什么不做代码关.md)。
- **没有服务器、没有排行榜。** 分数存在本地 `.mirror-house/save.json`。想改存档是你的事；这游戏不防作弊，只防无聊。
- **只验形式。** 回文的意思、句子的好坏，机器判不了；它只保证规则成立。
- **不联网。** 装完就能玩，不请求任何外部服务。

## 验收

```powershell
python mirror_house.py selftest
```

它会跑：三关的正例、反例、提示扣分、存档状态机、JSON 输出。全过才退出 0。

## 目录结构

```
mirror_house.py      主程序（单文件，只用标准库）
play.cmd             双击入口（自动找 py/python）
install-button.ps1   在桌面生成「镜屋」按钮
AGENTS.md            给 agent 的非交互协议
docs/                设计笔记（剧透）/ 为什么不做代码关
```

运行期产生 `.mirror-house/`，已在 `.gitignore` 里排除。

## License

MIT。作者信息匿名处理，欢迎随意 fork、改题、加关。
