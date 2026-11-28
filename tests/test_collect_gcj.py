"""inputs/data/collect_gcj.py on a hand-made copy of the archive's pages (no network)."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).parent.parent
spec = importlib.util.spec_from_file_location("collect_gcj", ROOT / "inputs/data/collect_gcj.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

INDEX = """<table><tr>
<td width="250"><a href="2021r1a/">Round 1A 2021</a></td>
<td width="90"><a href="2021r1a/problems/">2 problems</a></td>
<td class="info">2021-04-10 01:00 UTC, 2.5 hours, 10028 people</td>
</tr></table>"""

PROBLEMS = """<div class="problem" id="A">
<div class="header"><h2>A. Append Sort</h2><div class="menu"><a href="#A">A</a></div></div>
<div class="statement"><h3>Problem</h3><p>Sort $$$\\mathbf{N}$$$ numbers.</p>
<h3>Sample</h3><div class="sample-header"><div>Sample Input</div><a href="x"><i class="material-icons grey">save_alt</i></a>
<div class="sample-header-copy-popup">Copied!</div></div><pre>2
1 2</pre><div>inner</div></div>
</div>
<div class="problem" id="B">
<div class="header"><h2>B. Prime Time</h2></div>
<div class="statement"><p>Primes.</p></div>
</div>
<div class="problem noprint" id="stats-A"><div class="statistics">
<h3>Test set 1: 7722 correct solutions (77.0% solve rate)</h3>
<h3>Test set 2: 4490 correct solutions (44.8% solve rate)</h3></div></div>
<div class="problem noprint" id="stats-B"><div class="statistics">
<h3>Test set 1: 10 correct solutions (0.1% solve rate)</h3></div></div>
"""


def cell(ok, link=None, lang="py3", t="8:31", b=False):
    cls = ("ok " if ok else "re ") + ("b " if b else "") + "lang-" + lang
    inner = f'<a class="source" href="{link}" data-lang="{lang}"><b>+</b><p>{t}</p></a>' if link else ""
    return f'<td class="{cls}">{inner}</td>'


def row(rank, user, cells):
    return (f'<tr><td class="rank sm">{rank}</td><td><a class="user" href="../profile/{user}">{user}</a></td>'
            f'<td class="lang lang-py">Python</td>{"".join(cells)}<td class="score">1<p>1:00</p></td></tr>')


SCOREBOARD = ("<thead><tr><th>A1<br>12</th><th>A2<br>14</th><th>B1<br>7</th></tr></thead><tbody>"
              + row(1, "full", [cell(True, "solutions/full.1.py3", b=True), cell(True, "solutions/full.0.py3", t="1:02:03"),
                                cell(True, "solutions/cpp.0.cpp", lang="cpp", b=True)])
              + row(2, "half", [cell(True, "solutions/half.0.py3", b=True), cell(False), cell(False, b=True)])
              + row(3, "py2", [cell(True, "solutions/py2.0.py", lang="python", b=True), cell(True, "solutions/py2.0.py", lang="python"),
                               cell(False, b=True)])
              + "</tbody>")


def site(tmp_path, extra=None):
    files = {"index.html": INDEX, "2021r1a/problems/index.html": PROBLEMS, "2021r1a/index.html": SCOREBOARD,
             "2021r1a/solutions/full.0.py3": "print(1)\n", "2021r1a/solutions/full.1.py3": "print(0)\n",
             "2021r1a/solutions/half.0.py3": "print(2)\n", **(extra or {})}
    for k, v in files.items():
        (tmp_path / k).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / k).write_text(v)
    return g.Site(tmp_path, fetch=False)


def test_problems_page():
    p = g.parse_problems(PROBLEMS)
    assert p["A"]["title"] == "Append Sort" and p["A"]["solve_rates"] == [77.0, 44.8]
    assert "Sort $\\mathbf{N}$ numbers." in p["A"]["statement"] and "2\n1 2" in p["A"]["statement"]
    assert "inner" in p["A"]["statement"] and "Primes." not in p["A"]["statement"]
    assert "Sample Input" in p["A"]["statement"] and "save_alt" not in p["A"]["statement"]
    assert "Copied" not in p["A"]["statement"]


def test_scoreboard_keeps_python3_and_the_file_that_passed_the_last_test_set():
    s = {(x["user"], x["letter"]): x for x in g.parse_scoreboard(SCOREBOARD)}
    assert set(s) == {("full", "A"), ("half", "A")}  # cpp and Python 2 left out
    assert s["full", "A"]["link"] == "solutions/full.0.py3" and s["full", "A"]["passed"] == 2
    assert s["full", "A"]["time"] == "1:02:03" and s["half", "A"]["passed"] == 1


def test_collect_prefers_full_solutions_and_dates_them(tmp_path):
    rows = g.collect(site(tmp_path), rounds=["2021r1a"], log=lambda m: None)
    assert [r["problem_id"] for r in rows] == ["GCJ2021R1A-A"]  # B has no Python 3 submission
    r = rows[0]
    assert r["author"] == "full" and r["code"] == "print(1)\n" and r["test_sets_passed"] == "2/2"
    assert r["submitted_utc"] == "2021-04-10 02:02:03" and r["solve_rates"] == "77.0;44.8"
    assert r["python3_accepted"] == 2 and r["solution_link"].endswith("2021r1a/solutions/full.0.py3")


def test_collect_skips_code_that_does_not_parse(tmp_path):
    rows = g.collect(site(tmp_path, {"2021r1a/solutions/full.0.py3": "print 1\n"}), rounds=["2021r1a"],
                     log=lambda m: None)
    assert rows[0]["author"] == "half"


def test_draw_does_not_follow_rank():
    assert g.draw_key("P-A", "x") == g.draw_key("P-A", "x") != g.draw_key("P-B", "x")
    assert g.elapsed("78:33").total_seconds() == 78 * 60 + 33


def test_problem_ids():
    assert g.problem_id("2021r1a", "C") == "GCJ2021R1A-C"
    assert g.problem_id("ks2019_pr", "A") == "KS2019PR-A" and g.problem_id("ks2022h", "D") == "KS2022H-D"
