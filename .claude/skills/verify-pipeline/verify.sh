#!/usr/bin/env bash
# Verification harness for the llm-detector pipeline: a disposable copy of this checkout, cut to a few Problems.
# Usage (from anywhere):
#   verify.sh launch [N]                 copy the working tree, keep N Problems (default 3), rebuild Prompt files; prints BASE
#   verify.sh doctor BASE                read-only: is this copy worth driving?
#   verify.sh stage  BASE LABEL CODE     run notebook-style Python (cfg and every stage function are in scope)
#   verify.sh cli    BASE LABEL MODULE   run python -m MODULE, as a teammate would
#   verify.sh cleanup BASE               delete BASE/app; BASE/evidence is kept
set -euo pipefail

REPO=$(cd "$(dirname "$0")/../../.." && pwd)
PY="$REPO/.venv/bin/python"
PREAMBLE='from modules.common import load_config, results_dir
from modules.generate import generate
from modules.humanize import humanize
from modules.formatcheck import format_copies
from modules.score import score
from modules.metrics import metrics
cfg = load_config()'

need_base() {
  [[ -n "${1:-}" && -d "$1/app" && "$(basename "$1")" == verify-pipeline.* ]] || { echo "not a verify-pipeline BASE with an app/: ${1:-<none>}" >&2; exit 2; }
}

# Run a command in BASE/app, log command + output + exit code, snapshot results/verify, keep the exit code.
record() {
  local base=$1 label=$2; shift 2
  local log="$base/evidence/$label.log" rc=0
  { echo "\$ $*"; echo; } > "$log"
  (cd "$base/app" && "$@") >> "$log" 2>&1 || rc=$?
  echo "exit: $rc" >> "$log"
  rm -rf "$base/evidence/$label.results"
  [[ -d "$base/app/results/verify" ]] && cp -r "$base/app/results/verify" "$base/evidence/$label.results"
  cat "$log"
  return $rc
}

case "${1:-}" in
launch)
  n=${2:-3}
  base=$(mktemp -d "${TMPDIR:-/tmp}/verify-pipeline.XXXXXX")
  mkdir -p "$base/app" "$base/evidence"
  # The working tree as it is now (tracked and untracked files), without secrets, old Results or agent worktrees.
  (cd "$REPO" && git ls-files -z -co --exclude-standard -- . ':(exclude).env' ':(exclude)results' ':(exclude).claude') |
    while IFS= read -r -d '' f; do
      [[ -e "$REPO/$f" ]] && (cd "$REPO" && cp --parents -- "$f" "$base/app/")
    done
  (cd "$base/app" && "$PY" - "$n" <<'EOF'
import re, sys
from pathlib import Path
from modules.common import load_config, read_csv, ROOT
n = int(sys.argv[1])
cfg = load_config()
path = ROOT / cfg["problems"]
problems = read_csv(path)
keep = sorted(problems["problem_id"].unique())[:n]
problems[problems["problem_id"].isin(keep)].to_csv(path, index=False)
conf = Path("config.toml")
text = re.sub(r'(?m)^experiment = "[^"]*"', 'experiment = "verify"', conf.read_text())
text = re.sub(r'(?m)^prompts = \[[^\]]*\]', 'prompts = ["direct", "style"]', text)
conf.write_text(text)
print(f"kept Problems {keep}; experiment = verify; prompts = direct, style")
EOF
  )
  (cd "$base/app" && "$PY" -m modules.prompts)
  echo "READY BASE=$base"
  ;;
doctor)
  base=${2:-}; need_base "$base"
  (cd "$base/app" && "$PY" - <<'EOF'
import os, black
import modules.generate, modules.humanize, modules.score, modules.metrics
from modules.common import ROOT, load_config, read_csv
from modules.formatcheck import BLACK_VERSION
cfg = load_config()
ok = True
def check(cond, msg):
    global ok
    ok &= bool(cond)
    print(("ok   " if cond else "FAIL ") + msg)
check(ROOT == __import__("pathlib").Path.cwd(), f"code runs from the copy: ROOT = {ROOT}")
check(cfg["experiment"] == "verify", f"experiment = {cfg['experiment']}")
check(black.__version__ == BLACK_VERSION, f"black {black.__version__} (pinned {BLACK_VERSION})")
n = read_csv(ROOT / cfg["problems"])["problem_id"].nunique()
for name in cfg["prompts"]:
    p = ROOT / "inputs/templates" / f"{name}.jsonl"
    lines = len(p.read_text(encoding="utf-8").splitlines()) if p.exists() else -1
    check(lines == n, f"{p.name}: {lines} Prompts for {n} Problems")
calls = n * len(cfg["generators"]) * len(cfg["prompts"])
print(f"info generate would make up to {calls} OpenRouter calls ({n} Problems x {len(cfg['generators'])} Generators x {len(cfg['prompts'])} Prompt files)")
print(f"info OPENROUTER_API_KEY is {'set' if os.environ.get('OPENROUTER_API_KEY') else 'NOT set (generate journeys will fail)'}")
print(f"info Detectors: {list(cfg.get('detectors', {}))}")
raise SystemExit(0 if ok else 1)
EOF
  )
  ;;
stage)
  base=${2:-}; need_base "$base"; label=${3:?label}; code=${4:?python code}
  record "$base" "$label" "$PY" -c "$PREAMBLE
$code"
  ;;
cli)
  base=${2:-}; need_base "$base"; label=${3:?label}; module=${4:?module}
  record "$base" "$label" "$PY" -m "$module"
  ;;
cleanup)
  base=${2:-}; need_base "$base"
  rm -rf "$base/app"
  echo "removed $base/app; evidence kept in $base/evidence"
  ;;
*)
  sed -n '2,8p' "$0"; exit 2
  ;;
esac
