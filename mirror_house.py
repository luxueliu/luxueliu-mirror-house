#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""镜屋 · Mirror House

三个自指谜题，给 agent 也给人。
单文件、只用标准库、不联网、不执行提交的代码。
"""

import argparse
import json
import os
import random
import re
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")
except AttributeError:  # pragma: no cover - Python < 3.7
    pass

VERSION = "1.0.0"
STATE_ENV = "MIRROR_HOUSE_STATE"
DEFAULT_STATE_DIR = Path(__file__).resolve().parent / ".mirror-house"
JSON_MODE = False

TITLES = {1: "数镜 · 自画像", 2: "文镜 · 倒影", 3: "互镜 · 互相画像"}
BASE_SCORE = {1: 100, 2: 150, 3: 250}
WRONG_PENALTY = 10
HINT_COST = {1: 15, 2: 20, 3: 30}
RANKS = [(500, "镜主"), (450, "镜匠"), (350, "镜客"), (0, "镜童")]

PALINDROME_POOL = [
    "上海自来水来自海上",
    "黄山落叶叶落山黄",
    "雾锁山头山锁雾",
    "天连水尾水连天",
    "雪映江心江映雪",
    "月满江楼江满月",
    "雪落空山空落雪",
]
FORBID_POOL = "月夜风雪江花云舟灯秋山"
SELF_LENGTHS = [4, 5, 7, 8, 9, 10]


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------

def is_cjk(ch):
    return "\u4e00" <= ch <= "\u9fff"


def state_dir():
    override = os.environ.get(STATE_ENV)
    if override:
        return Path(override)
    return DEFAULT_STATE_DIR


def save_path():
    return state_dir() / "save.json"


def load_state():
    p = save_path()
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def save_state(st):
    d = state_dir()
    d.mkdir(parents=True, exist_ok=True)
    save_path().write_text(
        json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def new_state(seed):
    return {
        "version": 1,
        "seed": seed,
        "level": 1,
        "scores": {},
        "attempts": {},
        "hints": {},
        "finished": False,
    }


def current_score(st):
    return sum(st["scores"].values())


def potential_score(st, level):
    attempts = st["attempts"].get(str(level), 0)
    hints = st["hints"].get(str(level), 0)
    return max(0, BASE_SCORE[level] - WRONG_PENALTY * attempts - HINT_COST[level] * hints)


def rank(total):
    for threshold, name in RANKS:
        if total >= threshold:
            return name
    return "镜童"


# ---------------------------------------------------------------------------
# 数学：自描述数与十格描述
# ---------------------------------------------------------------------------

def compositions(total, parts, maxv=9):
    """parts 个非负整数，和为 total，每项不超过 maxv。"""
    def rec(prefix, remaining, slots):
        if slots == 1:
            if 0 <= remaining <= maxv:
                yield prefix + (remaining,)
            return
        lo = max(0, remaining - maxv * (slots - 1))
        hi = min(maxv, remaining)
        for v in range(lo, hi + 1):
            yield from rec(prefix + (v,), remaining - v, slots - 1)

    yield from rec((), total, parts)


_SELF_CACHE = {}


def self_descriptive_numbers(length):
    """所有 length 位自描述数，升序。"""
    if length in _SELF_CACHE:
        return _SELF_CACHE[length]
    out = []
    for ds in compositions(length, length):
        if ds[0] == 0:
            continue
        s = "".join(map(str, ds))
        if all(s.count(str(i)) == ds[i] for i in range(length)):
            out.append(int(s))
    _SELF_CACHE[length] = sorted(out)
    return _SELF_CACHE[length]


def describe10(n):
    """十格描述：数 0..9 各出现几次，把十个计数依次拼起来。"""
    s = str(n)
    return "".join(str(s.count(str(d))) for d in range(10))


# ---------------------------------------------------------------------------
# 题目
# ---------------------------------------------------------------------------

def challenge_for(level, seed):
    if level == 1:
        rng = random.Random(seed * 100 + 1)
        length = rng.choice(SELF_LENGTHS)
        hints = [
            "例：1210 是一个 4 位自描述数。",
            "各位数字之和恰好等于位数；可以只搜计数向量。",
        ]
        if length == 4:
            hints.append("4 位有两个答案。")
        elif length == 10:
            hints.append("10 位那个以 6 开头。")
        else:
            hints.append("这一长度只有一个答案。")
        return {
            "level": 1,
            "kind": "self_descriptive",
            "title": TITLES[1],
            "length": length,
            "base": BASE_SCORE[1],
            "hints_total": 3,
            "prompt": "找出所有 %d 位自描述数。一行一个，从小到大。" % length,
            "hints": hints,
        }

    if level == 2:
        rng = random.Random(seed * 100 + 2)
        witness = rng.choice(PALINDROME_POOL)
        distinct = list(dict.fromkeys(witness))
        require = rng.sample(distinct, 2)
        candidates = [c for c in FORBID_POOL if c not in witness]
        if not candidates:
            candidates = ["夜"]
        forbid = rng.choice(candidates)
        hints = [
            "回文的两端必须相同；先定首尾。",
            "必用字可以各用一次，放在对称的位置上。",
            "参考答案是一条流传的回文，不是生造词。",
        ]
        return {
            "level": 2,
            "kind": "palindrome",
            "title": TITLES[2],
            "length": len(witness),
            "require": require,
            "forbid": forbid,
            "min_distinct": 4,
            "base": BASE_SCORE[2],
            "hints_total": 3,
            "prompt": "写一条 %d 字回文：必须含「%s」「%s」，不得含「%s」，"
                      "至少 4 个不同汉字。只收汉字，一行。"
                      % (len(witness), require[0], require[1], forbid),
            "hints": hints,
        }

    if level == 3:
        hints = [
            "十格描述：数 0..9 各出现几次，把十个计数依次拼起来。",
            "十格的描述映射只有两个循环：一个不动点，一个二循环。",
            "从 2026 开始，反复做十格描述；五步之后你会看到那对数字。",
        ]
        return {
            "level": 3,
            "kind": "mutual",
            "title": TITLES[3],
            "digits": 10,
            "base": BASE_SCORE[3],
            "hints_total": 3,
            "prompt": "找出两个不同的十位数 A、B：A 的十格描述是 B，"
                      "B 的十格描述是 A。两行，顺序不限。",
            "hints": hints,
        }

    raise ValueError("bad level: %r" % (level,))


def public_challenge(ch):
    return {k: v for k, v in ch.items() if k != "hints" and not k.startswith("_")}


def solution_for(ch):
    """参考答案；给 demo 和 selftest 用，不在正常游戏里暴露。"""
    if ch["level"] == 1:
        return "\n".join(str(n) for n in self_descriptive_numbers(ch["length"]))
    if ch["level"] == 2:
        for w in PALINDROME_POOL:
            if verify_level2(w, ch)[0]:
                return w
        raise RuntimeError("internal: no palindrome witness")
    if ch["level"] == 3:
        return "6300000100\n7101001000"
    raise RuntimeError("bad level")


# ---------------------------------------------------------------------------
# 判卷
# ---------------------------------------------------------------------------

def verify_level1(text, ch):
    expected = self_descriptive_numbers(ch["length"])
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return False, "没有读到答案"
    nums = []
    for ln in lines:
        if not re.fullmatch(r"[0-9]+", ln):
            return False, "有一行不是纯数字：%r" % ln[:20]
        if len(ln) > 1 and ln.startswith("0"):
            return False, "有前导零：%s" % ln
        n = int(ln)
        if len(str(n)) != ch["length"]:
            return False, "有一个不是 %d 位数：%s" % (ch["length"], ln)
        nums.append(n)
    if len(nums) != len(set(nums)):
        return False, "有重复的答案"
    got, want = sorted(nums), expected
    if got == want:
        return True, "通过"
    missing = len(set(want) - set(got))
    extra = len(set(got) - set(want))
    return False, "不对：少了 %d 个，多了 %d 个" % (missing, extra)


def verify_level2(text, ch):
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return False, "没有读到答案"
    if len(lines) > 1:
        return False, "只收一行；你现在交了 %d 行" % len(lines)
    s = lines[0]
    if len(s) != ch["length"]:
        return False, "长度不对：要 %d 个字，你交了 %d 个" % (ch["length"], len(s))
    bad = [c for c in s if not is_cjk(c)]
    if bad:
        return False, "只收汉字；发现非汉字：%r" % "".join(bad[:5])
    if s != s[::-1]:
        for i, (a, b) in enumerate(zip(s, s[::-1])):
            if a != b:
                return False, "不是回文：第 %d 个字正读「%s」，倒读「%s」" % (i + 1, a, b)
        return False, "不是回文"
    for c in ch["require"]:
        if c not in s:
            return False, "缺少必用字「%s」" % c
    if ch["forbid"] in s:
        return False, "出现了禁用字「%s」" % ch["forbid"]
    if len(set(s)) < ch["min_distinct"]:
        return False, "不同汉字只有 %d 个，至少要 %d 个" % (
            len(set(s)), ch["min_distinct"]
        )
    return True, "通过"


def verify_level3(text, ch):
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) != 2:
        return False, "要两行，你交了 %d 行" % len(lines)
    for ln in lines:
        if not re.fullmatch(r"[0-9]{10}", ln):
            return False, "不是十位数（或含非数字）：%r" % ln[:20]
        if ln[0] == "0":
            return False, "十位数不能以 0 开头：%s" % ln
    a, b = lines[0], lines[1]
    if a == b:
        return False, "A 和 B 不能相同"
    da, db = describe10(int(a)), describe10(int(b))
    if da != b and db != a:
        return False, "两边都对不上：A 的描述不是 B，B 的描述也不是 A"
    if da != b:
        return False, "A 的描述不是 B"
    if db != a:
        return False, "B 的描述不是 A"
    return True, "通过"


# ---------------------------------------------------------------------------
# 输出
# ---------------------------------------------------------------------------

def emit(obj):
    print(json.dumps(obj, ensure_ascii=True))


def fail(msg):
    if JSON_MODE:
        emit({"ok": False, "error": msg})
    else:
        print("错误：" + msg, file=sys.stderr)
    sys.exit(1)


def require_state():
    st = load_state()
    if st is None:
        fail("还没有开局。先运行：python mirror_house.py start")
    return st


def print_challenge(st, ch):
    lv = ch["level"]
    print("=" * 56)
    print("  镜屋 · Mirror House   第 %d/3 关   seed %s" % (lv, st["seed"]))
    print("  " + ch["title"])
    print("=" * 56)
    print()
    print("题目：")
    print("  " + ch["prompt"])
    print()
    print("基础分 %d | 已错 %d 次 | 已用提示 %d 条 | 当前可得 %d 分" % (
        ch["base"], st["attempts"].get(str(lv), 0),
        st["hints"].get(str(lv), 0), potential_score(st, lv)))
    print()
    print("交卷：python mirror_house.py submit <答案文件>")
    print("提示：python mirror_house.py hint")
    print()


def print_status(st):
    total = current_score(st)
    level = min(st["level"], 3) if not st["finished"] else 3
    print("seed %s | 第 %d/3 关 | 总分 %d | 称号 %s" % (
        st["seed"], level, total, rank(total)))
    for lv in (1, 2, 3):
        if str(lv) in st["scores"]:
            state = "完成 %d 分" % st["scores"][str(lv)]
        elif lv == st["level"] and not st["finished"]:
            state = "进行中"
        else:
            state = "未开始"
        print("  第 %d 关 %s：%s（错 %d 次，提示 %d 条）" % (
            lv, TITLES[lv], state,
            st["attempts"].get(str(lv), 0), st["hints"].get(str(lv), 0)))


# ---------------------------------------------------------------------------
# 命令
# ---------------------------------------------------------------------------

def cmd_start(args):
    existing = load_state()
    if existing is not None and not args.force:
        fail("已有一局。用 reset 重开，或 start --force 覆盖。")
    seed = args.seed if args.seed is not None else random.SystemRandom().randint(1, 10 ** 9)
    st = new_state(seed)
    save_state(st)
    ch = challenge_for(1, seed)
    if JSON_MODE:
        emit({
            "ok": True, "command": "start", "seed": seed, "level": 1,
            "score": 0, "finished": False,
            "challenge": public_challenge(ch), "message": "开局",
        })
    else:
        print_challenge(st, ch)


def cmd_show(args):
    st = require_state()
    if st["finished"]:
        if JSON_MODE:
            emit({"ok": True, "command": "show", "finished": True,
                  "level": 3, "score": current_score(st),
                  "rank": rank(current_score(st))})
        else:
            print("已经通关。")
            print_status(st)
        return
    ch = challenge_for(st["level"], st["seed"])
    if JSON_MODE:
        emit({"ok": True, "command": "show", "level": st["level"],
              "score": current_score(st), "challenge": public_challenge(ch)})
    else:
        print_challenge(st, ch)


def cmd_submit(args):
    st = require_state()
    if st["finished"]:
        fail("已经通关了；用 reset 重开。")
    level = st["level"]
    ch = challenge_for(level, st["seed"])
    try:
        text = Path(args.file).read_text(encoding="utf-8-sig")
    except OSError as e:
        fail("读不到答案文件：%s" % e)

    if level == 1:
        ok, msg = verify_level1(text, ch)
    elif level == 2:
        ok, msg = verify_level2(text, ch)
    else:
        ok, msg = verify_level3(text, ch)

    if not ok:
        st["attempts"][str(level)] = st["attempts"].get(str(level), 0) + 1
        save_state(st)
        if JSON_MODE:
            emit({
                "ok": False, "command": "submit", "level": level,
                "message": msg, "potential_score": potential_score(st, level),
                "challenge": public_challenge(ch),
            })
        else:
            print("判卷：不通过 — %s" % msg)
            print("本题当前可得 %d 分。" % potential_score(st, level))
        return

    score = potential_score(st, level)
    st["scores"][str(level)] = score
    st["level"] = level + 1
    st["finished"] = st["level"] > 3
    save_state(st)

    if JSON_MODE:
        payload = {
            "ok": True, "command": "submit", "level": level,
            "message": "通过", "level_score": score, "score": current_score(st),
            "finished": st["finished"],
        }
        if st["finished"]:
            payload["rank"] = rank(current_score(st))
        else:
            payload["next"] = public_challenge(challenge_for(st["level"], st["seed"]))
        emit(payload)
    else:
        print("判卷：通过")
        print("本题得分 %d 分。总分 %d。" % (score, current_score(st)))
        if st["finished"]:
            print()
            print("通关。总分 %d，称号：%s。" % (
                current_score(st), rank(current_score(st))))
        else:
            print()
            print_challenge(st, challenge_for(st["level"], st["seed"]))


def cmd_hint(args):
    st = require_state()
    if st["finished"]:
        fail("已经通关了。")
    level = st["level"]
    ch = challenge_for(level, st["seed"])
    used = st["hints"].get(str(level), 0)
    if used >= len(ch["hints"]):
        if JSON_MODE:
            emit({"ok": True, "command": "hint", "level": level,
                  "hint": None, "message": "没有更多提示了"})
        else:
            print("没有更多提示了。")
        return
    st["hints"][str(level)] = used + 1
    save_state(st)
    hint = ch["hints"][used]
    if JSON_MODE:
        emit({
            "ok": True, "command": "hint", "level": level, "hint": hint,
            "used": used + 1, "total": len(ch["hints"]),
            "potential_score": potential_score(st, level),
        })
    else:
        print("提示 %d/%d（扣 %d 分）：" % (used + 1, len(ch["hints"]), HINT_COST[level]))
        print("  " + hint)
        print("本题当前可得 %d 分。" % potential_score(st, level))


def cmd_status(args):
    st = require_state()
    total = current_score(st)
    if JSON_MODE:
        levels = []
        for lv in (1, 2, 3):
            done = str(lv) in st["scores"]
            if done:
                status = "done"
            elif lv == st["level"] and not st["finished"]:
                status = "current"
            else:
                status = "pending"
            levels.append({
                "level": lv, "title": TITLES[lv], "status": status,
                "score": st["scores"].get(str(lv)),
                "attempts": st["attempts"].get(str(lv), 0),
                "hints": st["hints"].get(str(lv), 0),
            })
        emit({
            "ok": True, "command": "status", "seed": st["seed"],
            "level": min(st["level"], 3), "finished": st["finished"],
            "score": total, "rank": rank(total), "levels": levels,
        })
    else:
        print_status(st)


def cmd_reset(args):
    p = save_path()
    if p.exists():
        p.unlink()
        msg = "已重置。"
    else:
        msg = "没有存档。"
    if JSON_MODE:
        emit({"ok": True, "command": "reset", "message": msg})
    else:
        print(msg)


# ---------------------------------------------------------------------------
# 参考通关
# ---------------------------------------------------------------------------

def cmd_demo(args):
    print("镜屋 · 参考通关（会剧透；想自己玩就先别看）")
    print()
    with tempfile.TemporaryDirectory() as td:
        env = dict(os.environ)
        env[STATE_ENV] = td

        def run_json(*argv):
            r = subprocess.run(
                [sys.executable, os.path.abspath(__file__)] + list(argv) + ["--json"],
                capture_output=True, text=True, env=env,
                cwd=os.path.dirname(os.path.abspath(__file__)),
            )
            if r.returncode != 0:
                raise RuntimeError("demo command failed: %r\n%s" % (argv, r.stderr))
            return json.loads(r.stdout)

        d = run_json("start", "--seed", "7")
        print("$ python mirror_house.py start --seed 7")
        print("第 %d/3 关  %s" % (d["challenge"]["level"], d["challenge"]["title"]))
        print("题目：%s" % d["challenge"]["prompt"])
        print()
        ch = d["challenge"]
        for lv in (1, 2, 3):
            ans = solution_for(ch)
            p = Path(td) / ("answer-%d.txt" % lv)
            p.write_text(ans + "\n", encoding="utf-8")
            print("$ cat answer-%d.txt" % lv)
            print(ans)
            print()
            d = run_json("submit", str(p))
            print("$ python mirror_house.py submit answer-%d.txt" % lv)
            print("判卷：通过，本题 %d 分，总分 %d" % (d["level_score"], d["score"]))
            if d.get("finished"):
                print("通关。称号：%s" % d["rank"])
                break
            ch = d["next"]
            print()
        print()
        st = run_json("status")
        print("$ python mirror_house.py status")
        print("seed %s | 总分 %d | 称号 %s" % (st["seed"], st["score"], st["rank"]))


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------

def run_selftest(args=None):
    results = []

    def check(name, fn):
        try:
            fn()
            results.append((name, True, ""))
        except Exception as e:  # noqa: BLE001 - selftest wants the message
            results.append((name, False, str(e)))

    def eq(a, b, msg=""):
        if a != b:
            raise AssertionError("%s: %r != %r" % (msg, a, b))

    def t_self():
        eq(self_descriptive_numbers(4), [1210, 2020])
        eq(self_descriptive_numbers(5), [21200])
        eq(self_descriptive_numbers(6), [])
        eq(self_descriptive_numbers(7), [3211000])
        eq(self_descriptive_numbers(8), [42101000])
        eq(self_descriptive_numbers(9), [521001000])
        eq(self_descriptive_numbers(10), [6210001000])

    def t_describe():
        eq(describe10(2026), "1020001000")
        eq(describe10(6300000100), "7101001000")
        eq(describe10(7101001000), "6300000100")

    def t_l1():
        ch = {"level": 1, "length": 4}
        eq(verify_level1("1210\n2020\n", ch)[0], True)
        eq(verify_level1("2020\n1210\n", ch)[0], True)
        eq(verify_level1("1210\n", ch)[0], False)
        eq(verify_level1("1210\n2020\n21200\n", ch)[0], False)
        eq(verify_level1("0121\n", ch)[0], False)
        eq(verify_level1("abc\n", ch)[0], False)

    def t_l2():
        for w in PALINDROME_POOL:
            distinct = list(dict.fromkeys(w))
            ch = {
                "level": 2, "length": len(w),
                "require": distinct[:2],
                "forbid": next(c for c in FORBID_POOL if c not in w),
                "min_distinct": 4,
            }
            eq(verify_level2(w, ch)[0], True, w)
        ch = {"level": 2, "length": 7, "require": ["雪", "江"],
              "forbid": "月", "min_distinct": 4}
        eq(verify_level2("雪映江心江映雪", ch)[0], True)
        eq(verify_level2("雪映江心江映月", ch)[0], False)
        eq(verify_level2("雪雪雪雪雪雪雪", ch)[0], False)
        eq(verify_level2("雪映江心江映雪\n多一行", ch)[0], False)

    def t_l3():
        ch = {"level": 3}
        eq(verify_level3("6300000100\n7101001000\n", ch)[0], True)
        eq(verify_level3("7101001000\n6300000100\n", ch)[0], True)
        eq(verify_level3("6300000100\n6300000100\n", ch)[0], False)
        eq(verify_level3("6300000100\n7101001001\n", ch)[0], False)
        eq(verify_level3("630000010\n7101001000\n", ch)[0], False)
        eq(verify_level3("06300000100\n7101001000\n", ch)[0], False)

    def t_state():
        with tempfile.TemporaryDirectory() as td:
            env = dict(os.environ)
            env[STATE_ENV] = td

            def run_json(*argv):
                r = subprocess.run(
                    [sys.executable, os.path.abspath(__file__)] + list(argv) + ["--json"],
                    capture_output=True, text=True, env=env,
                    cwd=os.path.dirname(os.path.abspath(__file__)),
                )
                if r.returncode != 0:
                    raise AssertionError("rc=%d stderr=%s" % (r.returncode, r.stderr[:200]))
                return json.loads(r.stdout)

            d = run_json("start", "--seed", "7")
            eq(d["ok"], True)
            eq(d["level"], 1)
            ch = d["challenge"]
            for lv in (1, 2, 3):
                ans = solution_for(ch)
                p = Path(td) / ("ans-%d.txt" % lv)
                p.write_text(ans + "\n", encoding="utf-8")
                d = run_json("submit", str(p))
                eq(d["ok"], True, "level %d: %r" % (lv, d))
                if lv < 3:
                    ch = d["next"]
            eq(d["finished"], True)
            eq(d["score"], 500)
            eq(d["rank"], "镜主")

            s = run_json("status")
            eq(s["score"], 500)
            eq(s["finished"], True)
            eq(len(s["levels"]), 3)

            r = run_json("reset")
            eq(r["ok"], True)
            eq((Path(td) / "save.json").exists(), False)

    def t_hint():
        with tempfile.TemporaryDirectory() as td:
            env = dict(os.environ)
            env[STATE_ENV] = td

            def run_json(*argv):
                r = subprocess.run(
                    [sys.executable, os.path.abspath(__file__)] + list(argv) + ["--json"],
                    capture_output=True, text=True, env=env,
                    cwd=os.path.dirname(os.path.abspath(__file__)),
                )
                if r.returncode != 0:
                    raise AssertionError("rc=%d stderr=%s" % (r.returncode, r.stderr[:200]))
                return json.loads(r.stdout)

            run_json("start", "--seed", "7")
            h1 = run_json("hint")
            eq(h1["ok"], True)
            eq(h1["used"], 1)
            eq(h1["potential_score"], 85)
            h2 = run_json("hint")
            eq(h2["used"], 2)
            h3 = run_json("hint")
            eq(h3["used"], 3)
            h4 = run_json("hint")
            eq(h4["hint"], None)

    check("自描述数 4..10", t_self)
    check("十格描述与二循环", t_describe)
    check("第一关判卷", t_l1)
    check("第二关判卷", t_l2)
    check("第三关判卷", t_l3)
    check("提示扣分", t_hint)
    check("存档状态机", t_state)

    passed = sum(1 for _, ok, _ in results if ok)
    failed = len(results) - passed
    if JSON_MODE:
        emit({
            "ok": failed == 0,
            "passed": passed,
            "failed": failed,
            "tests": [{"name": n, "ok": ok, "error": e} for n, ok, e in results],
        })
    else:
        print("镜屋 · selftest")
        for n, ok, e in results:
            print(("  PASS  " if ok else "  FAIL  ") + n + (("  " + e) if e else ""))
        print()
        print("%d passed, %d failed" % (passed, failed))
    sys.exit(0 if failed == 0 else 1)


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(
        prog="mirror_house.py",
        description="镜屋 · Mirror House：三个自指谜题，给 agent 也给人。",
    )
    p.add_argument("--version", action="version", version="mirror-house " + VERSION)
    sub = p.add_subparsers(dest="cmd")

    s = sub.add_parser("start", help="开一局")
    s.add_argument("--seed", type=int, default=None, help="固定题目")
    s.add_argument("--force", action="store_true", help="覆盖已有存档")
    s.set_defaults(func=cmd_start)

    s = sub.add_parser("show", help="看当前这关")
    s.set_defaults(func=cmd_show)

    s = sub.add_parser("submit", help="交卷")
    s.add_argument("file", help="答案文件（UTF-8）")
    s.set_defaults(func=cmd_submit)

    s = sub.add_parser("hint", help="要一条提示（扣分）")
    s.set_defaults(func=cmd_hint)

    s = sub.add_parser("status", help="看进度与分数")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("reset", help="重开")
    s.set_defaults(func=cmd_reset)

    s = sub.add_parser("demo", help="参考通关（会剧透）")
    s.set_defaults(func=cmd_demo)

    s = sub.add_parser("selftest", help="验收判卷逻辑")
    s.set_defaults(func=run_selftest)

    return p


def main(argv=None):
    global JSON_MODE
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--json" in argv:
        JSON_MODE = True
        argv = [a for a in argv if a != "--json"]

    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "cmd", None):
        parser.print_help()
        return 0
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
