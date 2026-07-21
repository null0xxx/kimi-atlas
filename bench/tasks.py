"""Benchmark task suite — each task is a small, self-contained coding problem with HIDDEN
acceptance tests and a real edge-case trap. A task is materialised into a throwaway git repo
(the baseline atlas grounds on); the acceptance tests are the ground-truth grader.

Every task is self-validating: ``validate(id)`` confirms the reference solution passes the
tests (the suite is correct + solvable) and the stub fails them (there is real work).
"""
from __future__ import annotations

import subprocess
import pathlib

# id -> {file, brief, stub, ref, test}. `stub` is the committed baseline atlas starts from
# (a NotImplementedError stub, or — for a bugfix task — the buggy code). `ref` is a known-good
# solution used only for validation, never shipped into a task repo.
TASKS: dict[str, dict[str, str]] = {
    "t1-roman": {
        "file": "roman.py",
        "brief": "implement int_to_roman(n) and roman_to_int(s) in roman.py so the acceptance "
                 "tests in test_roman.py pass. n must be 1..3999 (else ValueError); an invalid "
                 "roman numeral must raise ValueError. Verify with python3 -m unittest.",
        "stub": '"""Roman numerals. TODO(atlas): implement per test_roman.py."""\n\n\n'
                'def int_to_roman(n):\n    raise NotImplementedError\n\n\n'
                'def roman_to_int(s):\n    raise NotImplementedError\n',
        "ref": '"""Roman numerals."""\n'
               '_VALS = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"),\n'
               '         (90, "XC"), (50, "L"), (40, "XL"), (10, "X"), (9, "IX"),\n'
               '         (5, "V"), (4, "IV"), (1, "I")]\n'
               '_SYM = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}\n\n\n'
               'def int_to_roman(n):\n'
               '    if not isinstance(n, int) or isinstance(n, bool) or n < 1 or n > 3999:\n'
               '        raise ValueError("n must be an int in 1..3999")\n'
               '    out = []\n'
               '    for v, s in _VALS:\n'
               '        while n >= v:\n'
               '            out.append(s); n -= v\n'
               '    return "".join(out)\n\n\n'
               'def roman_to_int(s):\n'
               '    if not s or any(c not in _SYM for c in s):\n'
               '        raise ValueError("invalid roman numeral")\n'
               '    total = prev = 0\n'
               '    for c in reversed(s):\n'
               '        v = _SYM[c]\n'
               '        total += -v if v < prev else v\n'
               '        prev = v\n'
               '    if int_to_roman(total) != s:\n'
               '        raise ValueError("malformed roman numeral")\n'
               '    return total\n',
        "test": "import unittest\nfrom roman import int_to_roman, roman_to_int\n\n\n"
                "class T(unittest.TestCase):\n"
                "    def test_int_to_roman_basic(self):\n"
                '        self.assertEqual(int_to_roman(4), "IV")\n'
                '        self.assertEqual(int_to_roman(1994), "MCMXCIV")\n'
                '        self.assertEqual(int_to_roman(3999), "MMMCMXCIX")\n\n'
                "    def test_roman_to_int_basic(self):\n"
                '        self.assertEqual(roman_to_int("IV"), 4)\n'
                '        self.assertEqual(roman_to_int("MCMXCIV"), 1994)\n\n'
                "    def test_round_trip(self):\n"
                "        for n in (1, 49, 444, 1000, 2023, 3999):\n"
                "            self.assertEqual(roman_to_int(int_to_roman(n)), n)\n\n"
                "    def test_bounds_raise(self):\n"
                "        for bad in (0, -1, 4000):\n"
                "            with self.assertRaises(ValueError):\n"
                "                int_to_roman(bad)\n\n"
                "    def test_malformed_roman_raises(self):\n"
                '        for bad in ("", "IIII", "ABC", "VV"):\n'
                "            with self.assertRaises(ValueError):\n"
                "                roman_to_int(bad)\n",
    },
    "t2-median-bugfix": {
        "file": "stats.py",
        "brief": "there is a bug in median(nums) in stats.py — the acceptance tests in "
                 "test_stats.py fail. Find and fix it so all tests pass; do not change the "
                 "tests. Verify with python3 -m unittest.",
        "stub": '"""Descriptive stats. NOTE: median() has a bug — the tests reveal it."""\n\n\n'
                'def median(nums):\n    s = sorted(nums)\n    n = len(s)\n'
                '    return s[n // 2]  # bug: wrong on even-length; empty raises IndexError\n',
        "ref": '"""Descriptive stats."""\n\n\n'
               'def median(nums):\n    s = sorted(nums)\n    n = len(s)\n'
               '    if n == 0:\n        raise ValueError("median of an empty sequence")\n'
               '    if n % 2:\n        return float(s[n // 2])\n'
               '    return (s[n // 2 - 1] + s[n // 2]) / 2\n',
        "test": "import unittest\nfrom stats import median\n\n\n"
                "class T(unittest.TestCase):\n"
                "    def test_odd(self):\n        self.assertEqual(median([3, 1, 2]), 2)\n\n"
                "    def test_even_averages(self):\n"
                "        self.assertEqual(median([1, 2, 3, 4]), 2.5)\n"
                "        self.assertEqual(median([7, 1]), 4.0)\n\n"
                "    def test_single(self):\n        self.assertEqual(median([5]), 5)\n\n"
                "    def test_empty_raises(self):\n"
                "        with self.assertRaises(ValueError):\n            median([])\n",
    },
    "t3-csvlite": {
        "file": "csvlite.py",
        "brief": "implement parse_line(line) in csvlite.py: split a single CSV line into fields, "
                 "honoring double-quoted fields that may contain commas and escaped double-quotes "
                 "(two consecutive double-quotes inside a quoted field mean one literal quote). "
                 "The acceptance tests in test_csvlite.py must pass. Verify with python3 -m unittest.",
        "stub": '"""Minimal CSV line parser. TODO(atlas): implement per test_csvlite.py."""\n\n\n'
                'def parse_line(line):\n    raise NotImplementedError\n',
        "ref": '"""Minimal CSV line parser (RFC-4180-ish, single line)."""\n\n\n'
               'def parse_line(line):\n'
               '    out, field, i, n, in_q = [], [], 0, len(line), False\n'
               '    while i < n:\n        c = line[i]\n        if in_q:\n'
               '            if c == \'"\':\n'
               '                if i + 1 < n and line[i + 1] == \'"\':\n'
               '                    field.append(\'"\'); i += 2; continue\n'
               '                in_q = False; i += 1; continue\n'
               '            field.append(c); i += 1\n        else:\n'
               '            if c == \'"\':\n                in_q = True; i += 1\n'
               '            elif c == ",":\n'
               '                out.append("".join(field)); field = []; i += 1\n'
               '            else:\n                field.append(c); i += 1\n'
               '    out.append("".join(field))\n    return out\n',
        "test": "import unittest\nfrom csvlite import parse_line\n\n\n"
                "class T(unittest.TestCase):\n"
                "    def test_plain(self):\n"
                '        self.assertEqual(parse_line("a,b,c"), ["a", "b", "c"])\n\n'
                "    def test_quoted_comma(self):\n"
                "        self.assertEqual(parse_line('\"a,b\",c'), [\"a,b\", \"c\"])\n\n"
                "    def test_escaped_quote(self):\n"
                "        self.assertEqual(parse_line('\"he said \"\"hi\"\"\",x'), ['he said \"hi\"', \"x\"])\n\n"
                "    def test_empty_fields(self):\n"
                '        self.assertEqual(parse_line("a,,c"), ["a", "", "c"])\n'
                '        self.assertEqual(parse_line(""), [""])\n',
    },
    "t4-merge-intervals": {
        "file": "interval.py",
        "brief": "implement merge(intervals) in interval.py: given a list of [start, end] pairs "
                 "(possibly unsorted, touching, or nested), return the minimal list of merged, "
                 "non-overlapping intervals sorted by start. Touching intervals ([1,2],[2,3]) "
                 "merge into [1,3]. The acceptance tests in test_interval.py must pass. Verify "
                 "with python3 -m unittest.",
        "stub": '"""Interval merge. TODO(atlas): implement per test_interval.py."""\n\n\n'
                'def merge(intervals):\n    raise NotImplementedError\n',
        "ref": '"""Interval merge."""\n\n\n'
               'def merge(intervals):\n'
               '    if not intervals:\n        return []\n'
               '    s = sorted(intervals, key=lambda x: (x[0], x[1]))\n'
               '    out = [list(s[0])]\n'
               '    for a, b in s[1:]:\n'
               '        if a <= out[-1][1]:\n'
               '            out[-1][1] = max(out[-1][1], b)\n'
               '        else:\n            out.append([a, b])\n'
               '    return out\n',
        "test": "import unittest\nfrom interval import merge\n\n\n"
                "class T(unittest.TestCase):\n"
                "    def test_basic(self):\n"
                "        self.assertEqual(merge([[1, 3], [2, 6], [8, 10], [15, 18]]),\n"
                "                         [[1, 6], [8, 10], [15, 18]])\n\n"
                "    def test_touching(self):\n"
                "        self.assertEqual(merge([[1, 4], [4, 5]]), [[1, 5]])\n\n"
                "    def test_unsorted(self):\n"
                "        self.assertEqual(merge([[5, 6], [1, 3]]), [[1, 3], [5, 6]])\n\n"
                "    def test_nested(self):\n"
                "        self.assertEqual(merge([[1, 4], [2, 3]]), [[1, 4]])\n\n"
                "    def test_empty(self):\n        self.assertEqual(merge([]), [])\n",
    },
}


def _run_unittest(cwd: pathlib.Path) -> bool:
    r = subprocess.run(["python3", "-m", "unittest", "-q"], cwd=str(cwd),
                       capture_output=True, text=True)
    return r.returncode == 0


def _git(cwd: pathlib.Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, check=False)


def materialize(task_id: str, dest: pathlib.Path, *, as_git: bool = True) -> pathlib.Path:
    """Write the task's stub + hidden test into ``dest`` and (optionally) commit a baseline.

    Returns ``dest``. The reference solution is NEVER written here — only the stub the
    solver starts from and the acceptance tests that grade it.
    """
    t = TASKS[task_id]
    dest.mkdir(parents=True, exist_ok=True)
    (dest / t["file"]).write_text(t["stub"], encoding="utf-8")
    (dest / ("test_" + t["file"])).write_text(t["test"], encoding="utf-8")
    (dest / "TASK.txt").write_text(t["brief"] + "\n", encoding="utf-8")
    if as_git:
        _git(dest, "init", "-q")
        _git(dest, "config", "user.email", "bench@local")
        _git(dest, "config", "user.name", "bench")
        _git(dest, "add", "-A")
        _git(dest, "commit", "-qm", f"bench baseline: {task_id}")
    return dest


def validate(task_id: str, workdir: pathlib.Path) -> dict:
    """Self-check a task: reference solution PASSES the tests, stub FAILS them.

    Returns ``{"ref_pass", "stub_fail", "valid"}``. A benchmark task is only sound when
    both hold — otherwise the grader is wrong or the task is unsolvable/already-solved.
    """
    t = TASKS[task_id]
    d = workdir / task_id
    materialize(task_id, d, as_git=False)
    (d / t["file"]).write_text(t["ref"], encoding="utf-8")
    ref_pass = _run_unittest(d)
    (d / t["file"]).write_text(t["stub"], encoding="utf-8")
    stub_fail = not _run_unittest(d)
    return {"ref_pass": ref_pass, "stub_fail": stub_fail, "valid": ref_pass and stub_fail}
