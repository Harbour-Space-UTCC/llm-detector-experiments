"""Build inputs/data/datasets.csv from the GCJ Archive (https://zibada.guru/gcj/), ADR 0004 and #48.

One row per Code Jam (2018-2022) or Kick Start (2019-2022) Problem that has at least one accepted
Python 3 submission. Rerun from the repo root:

    python inputs/data/collect_gcj.py --cache <dir> [--oedingen Unformatted_Balanced.jsonl]

Pages are read from <dir>/<path under /gcj/> when present and fetched from the site (then saved
there) when not. --oedingen points at the xgb_tfidf training jsonl (see detectors/xgb_tfidf.py);
with it, a Problem is dropped when its chosen solution is close to any jsonl row that prints
"Case #" (Code Jam's output format).

Selection rule for the one Human Sample per Problem (also in README.md):
  1. Only submissions in Python 3 (the archive's `py3` or `pypy3` language) are candidates.
  2. A candidate must be accepted on Test Set 1 (scoreboard cell marked correct).
  3. Its code must decode as UTF-8, be non-empty and parse with Python 3's `ast`.
  4. Keep the candidates that passed the most Test Sets of the Problem (full solutions first).
  5. Among those, take the one with the smallest sha256("<problem_id>/<username>"): a fixed,
     reproducible draw that does not favour top-ranked contestants.
  If the drawn file fails rule 3, the next one in the same order is tried.
"""
import argparse, ast, csv, datetime as dt, difflib, hashlib, html, json, re, sys, time, urllib.request
from html.parser import HTMLParser
from pathlib import Path

BASE = "https://zibada.guru/gcj/"
CUTOFF = dt.datetime(2022, 11, 30, tzinfo=dt.timezone.utc)
PY3 = ("py3", "pypy3")
LICENSE = "code: MIT (Google Coding Competitions Terms); statement: Apache-2.0 (google/coding-competitions-archive)"

GCJ_ROUNDS = ["iow", "qr", "r1a", "r1b", "r1c", "r2", "r3", "wf"]
ROUNDS = (["2018" + r for r in ["iow", "pr"] + GCJ_ROUNDS[1:]]
          + [f"{y}{r}" for y in (2019, 2020, 2021, 2022) for r in GCJ_ROUNDS]
          + ["ks2019_pr"] + [f"ks{y}{r}" for y in (2019, 2020, 2021, 2022) for r in "abcdefgh"])

COLUMNS = ["problem_id", "contest", "year", "round", "round_name", "problem_letter", "problem_title",
           "statement", "difficulty", "test_sets", "solve_rates", "round_participants",
           "code", "code_lines", "code_parses", "language", "test_sets_passed", "python3_accepted",
           "round_start_utc", "submitted_utc", "author", "author_link", "solution_link", "problem_link",
           "source_problem_id", "license"]


class Site:
    def __init__(self, cache, fetch=True):
        self.cache, self.fetch = Path(cache), fetch

    def get(self, path):
        f = self.cache / (path + "index.html" if path == "" or path.endswith("/") else path)
        if f.exists():
            return f.read_bytes()
        if not self.fetch:
            raise FileNotFoundError(f)
        for i in range(4):
            try:
                with urllib.request.urlopen(BASE + path, timeout=60) as r:
                    data = r.read()
                break
            except OSError:
                if i == 3:
                    raise
                time.sleep(2 ** i)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(data)
        return data

    def text(self, path):
        return self.get(path).decode("utf-8")


# ---------- index: round names and start times ----------

def parse_index(page):
    """{round_key: (name, start datetime UTC, participants)} from the archive's front page."""
    out = {}
    for key, name, info in re.findall(
            r'<td[^>]*><a href="([^"/]+)/">([^<]+)</a></td>\s*<td[^>]*><a[^>]*>[^<]*</a></td>\s*'
            r'<td class="info">([^<]+)</td>', page):
        m = re.match(r"(\d{4}-\d\d-\d\d \d\d:\d\d) UTC.*?(\d+) (?:people|teams)", info)
        if m:
            start = dt.datetime.strptime(m[1], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc)
            out[key] = (html.unescape(name), start, int(m[2]))
    return out


# ---------- problems page: statement and solve rates ----------

class _Text(HTMLParser):
    """Statement HTML -> plain text. Math stays as LaTeX between $ signs."""
    BLOCK = {"p", "div", "h1", "h2", "h3", "h4", "h5", "pre", "table", "tr", "ul", "ol", "br"}

    VOID = {"br", "img", "hr", "input", "meta", "link", "wbr", "col", "source"}
    # Page widgets, not statement text: icon ligatures ("save_alt"), copy popups, test-data notes.
    SKIP_CLASSES = ("material-icons", "sample-header-copy-popup", "test-data-download-wrapper")

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.pre, self.stack = [], 0, []  # stack: (tag, skipped) of open non-void tags

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        skipped = (bool(self.stack) and self.stack[-1][1]) or tag in ("script", "style") or any(
            c in (a.get("class") or "") for c in self.SKIP_CLASSES)
        if tag not in self.VOID:
            self.stack.append((tag, skipped))
        if skipped:
            return
        if tag in self.BLOCK:
            self.out.append("\n")
        if tag in ("h3", "h4"):
            self.out.append("\n")
        if tag == "pre":
            self.pre += 1
        if tag == "li":
            self.out.append("\n- ")
        if tag in ("td", "th"):
            self.out.append(" | ")
        if tag == "img":
            self.out.append(f"[image: {a.get('alt') or a.get('src', '')}]")

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        skipped = False
        while self.stack:
            t, skipped = self.stack.pop()
            if t == tag:
                break
        if skipped:
            return
        if tag == "pre":
            self.pre -= 1
        if tag in self.BLOCK or tag == "li":
            self.out.append("\n")

    def handle_data(self, data):
        if self.stack and self.stack[-1][1]:
            return
        self.out.append(data if self.pre else re.sub(r"\s+", " ", data))


def html_to_text(fragment):
    p = _Text()
    p.feed(fragment.replace("$$$", "$"))
    lines = [ln.strip() if not ln.startswith("    ") else ln.rstrip() for ln in "".join(p.out).split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def _div_body(page, start):
    """Inner HTML of the <div> whose opening tag ends at `start`, honouring nested divs."""
    depth, i = 1, start
    for m in re.compile(r"<(/?)div\b[^>]*>").finditer(page, start):
        depth += -1 if m[1] else 1
        if depth == 0:
            return page[start:m.start()]
    raise ValueError("unbalanced div")


def parse_problems(page):
    """{letter: {"title", "statement", "solve_rates": [float percent per Test Set]}}."""
    out = {}
    for m in re.finditer(r'<div class="problem" id="([A-Z])">\s*<div class="header">\s*<h2>[A-Z]\. ([^<]*)</h2>', page):
        s = re.compile(r'<div class="statement">').search(page, m.end())
        out[m[1]] = {"title": html.unescape(m[2]).strip(), "statement": html_to_text(_div_body(page, s.end())),
                     "solve_rates": []}
    for m in re.finditer(r'<div class="problem noprint" id="stats-([A-Z])">', page):
        body = _div_body(page, m.end())
        rates = re.findall(r"Test set (\d+): (\d+) correct solutions? \(([\d.]+)% solve rate\)", body)
        out[m[1]]["solve_rates"] = [float(r[2]) for r in sorted(rates, key=lambda r: int(r[0]))]
    return out


# ---------- scoreboard: Python 3 submissions ----------

def parse_scoreboard(page):
    """Yield one dict per (user, problem) that has a Python 3 submission.

    Test-set columns come from the header (A1, A2, B1, ...). A cell is accepted when its class has `ok`.
    Pages may be cut to the rows with Python 3 links; the header is all this needs besides those rows."""
    cols = re.findall(r"<th[^>]*>([A-Z])(\d+)<br>", page)
    body = page[page.index("<tbody>"):]
    for row in re.split(r"<tr[\s>]", body)[1:]:
        if not re.search(r'data-lang="(?:py3|pypy3)"', row):
            continue
        rank = re.search(r'<td class="rank[^"]*">(\d+)</td>', row)
        user = re.search(r'<a class="user[^"]*" href="[^"]*/profile/([^"]+)">([^<]*)</a>', row)
        cells = re.findall(r"<td( class=\"[^\"]*\")?>(.*?)</td>", row, re.S)
        cells = [c for c in cells if 'class="rank' not in c[0] and 'class="lang ' not in c[0]
                 and 'class="score"' not in c[0] and "/profile/" not in c[1]]
        if not (rank and user) or len(cells) < len(cols):
            continue
        per = {}
        for (letter, ts), (cls, inner) in zip(cols, cells):
            link = re.search(r'href="([^"]+)" data-lang="([^"]+)"', inner)
            t = re.search(r"<p>([\d:]+)</p>", inner)
            d = per.setdefault(letter, {"passed": 0, "ts1": False, "link": None, "lang": None, "time": None})
            d.setdefault("n", 0)
            d["n"] += 1
            if "ok" in cls.split('"')[1].split() if cls else False:
                d["passed"] += 1
                d["ts1"] |= ts == "1"
                if link:
                    d["link"], d["lang"] = link[1], link[2]
                    d["time"] = t[1] if t else d["time"]
        for letter, d in per.items():
            if d["link"] and d["lang"] in PY3:
                yield {"letter": letter, "rank": int(rank[1]), "user": html.unescape(user[1]),
                       "display": html.unescape(user[2]), "link": html.unescape(d["link"]), "lang": d["lang"],
                       "time": d["time"], "passed": d["passed"], "test_sets": d["n"], "ts1": d["ts1"]}


def elapsed(t):
    """Time since round start, 'mm:ss' or 'h:mm:ss' (e.g. '8:31', '25:13:02') -> timedelta."""
    secs = 0
    for p in t.split(":"):
        secs = secs * 60 + int(p)
    return dt.timedelta(seconds=secs)


def draw_key(problem_id, user):
    return hashlib.sha256(f"{problem_id}/{user}".encode()).hexdigest()


def parses(code):
    try:
        ast.parse(code)
        return True
    except (SyntaxError, ValueError):
        return False


def problem_id(rk, letter):
    return ("KS" + rk[2:].replace("_pr", "PR").upper() if rk.startswith("ks") else "GCJ" + rk.upper()) + "-" + letter


# ---------- xgb_tfidf training-data check ----------

def case_rows(jsonl):
    rows = [json.loads(line) for line in open(jsonl, encoding="utf-8")]
    return [r for r in rows if "Case #" in r["code"]]


def too_close(code, rows, threshold=0.8):
    norm = lambda s: re.sub(r"\s+", " ", s).strip()  # noqa: E731
    c = norm(code)
    return [r["id"] for r in rows if difflib.SequenceMatcher(None, c, norm(r["code"])).ratio() >= threshold]


# ---------- main ----------

def collect(site, rounds=ROUNDS, oedingen=None, log=print):
    index = parse_index(site.text(""))
    jsonl = case_rows(oedingen) if oedingen else None
    if jsonl is not None:
        log(f"xgb_tfidf jsonl: {len(jsonl)} rows print 'Case #' ({len({r['id'] for r in jsonl})} problem ids)")
    out = []
    for rk in rounds:
        name, start, people = index[rk]
        probs = parse_problems(site.text(rk + "/problems/"))
        first = site.text(rk + "/")
        pages = [int(n) for n in re.findall(r"index\.(\d+)\.html", first)]
        subs = list(parse_scoreboard(first))
        for n in range(2, max(pages, default=1) + 1):
            subs += parse_scoreboard(site.text(f"{rk}/index.{n}.html"))
        for letter, p in sorted(probs.items()):
            pid = problem_id(rk, letter)
            cand = [s for s in subs if s["letter"] == letter and s["ts1"]]
            if not cand:
                log(f"{pid}: no accepted Python 3 submission, skipped")
                continue
            pick = None
            for s in sorted(cand, key=lambda s: (-s["passed"], draw_key(pid, s["user"]))):
                path = s["link"].split("/gcj/", 1)[1] if "/gcj/" in s["link"] else rk + "/" + s["link"].lstrip("./")
                try:
                    code = site.get(path).decode("utf-8")
                except UnicodeDecodeError:
                    log(f"{pid}: {s['user']} not UTF-8, next")
                    continue
                if not code.strip() or not parses(code):
                    log(f"{pid}: {s['user']} does not parse, next")
                    continue
                pick, s["path"] = (s, code), path
                break
            if pick is None:
                log(f"{pid}: no parsing Python 3 submission, skipped")
                continue
            s, code = pick
            submitted = start + elapsed(s["time"]) if s["time"] else None
            if submitted is None or submitted >= CUTOFF:
                log(f"{pid}: submission time unknown or after cutoff, skipped")
                continue
            if jsonl is not None:
                close = too_close(code, jsonl)
                if close:
                    log(f"{pid}: close to xgb_tfidf rows {close}, dropped")
                    continue
            rates = p["solve_rates"]
            out.append({
                "problem_id": pid,
                "contest": "Kick Start" if rk.startswith("ks") else "Code Jam",
                "year": start.year, "round": rk, "round_name": name, "problem_letter": letter,
                "problem_title": p["title"], "statement": p["statement"],
                "difficulty": f"{rates[-1]:.1f}" if rates else "",
                "test_sets": len(rates) or s["test_sets"],
                "solve_rates": ";".join(f"{r:.1f}" for r in rates),
                "round_participants": people,
                "code": code, "code_lines": len(code.splitlines()), "code_parses": True,
                "language": s["lang"], "test_sets_passed": f"{s['passed']}/{s['test_sets']}",
                "python3_accepted": len(cand),
                "round_start_utc": start.strftime("%Y-%m-%d %H:%M:%S"),
                "submitted_utc": submitted.strftime("%Y-%m-%d %H:%M:%S"),
                "author": s["user"], "author_link": f"{BASE}profile/{s['user']}",
                "solution_link": BASE + s["path"], "problem_link": f"{BASE}{rk}/problems/#{letter}",
                "source_problem_id": f"{rk}/{letter}", "license": LICENSE,
            })
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--oedingen")
    ap.add_argument("--offline", action="store_true", help="fail instead of fetching a page missing from the cache")
    ap.add_argument("--out", default=str(Path(__file__).with_name("datasets.csv")))
    a = ap.parse_args(argv)
    rows = collect(Site(a.cache, fetch=not a.offline), oedingen=a.oedingen, log=lambda m: print(m, file=sys.stderr))
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLUMNS)
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} Problems written to {a.out}")


if __name__ == "__main__":
    main()
