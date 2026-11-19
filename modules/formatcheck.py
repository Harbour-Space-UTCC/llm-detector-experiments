"""Stage 1c: black-formatted copy of every Sample -> results/<experiment>/formatted.csv.

Checks whether a Detector reacts only to spacing. Every Category is formatted, Human included, so neat
formatting is never a clue by itself. Copies have sample_id `<sample_id>:fmt` and formatted = "True".
Terms: GLOSSARY.md (Sample, Category). Decisions: issue #21.
"""
import black

from .common import FORMATTED_FILE, SAMPLE_COLUMNS, append_csv, combine, done_ids, read_csv, results_dir

BLACK_VERSION = "26.10.1"  # also pinned in colab.ipynb; a different version formats differently


def format_copies(cfg, force=False):
    if black.__version__ != BLACK_VERSION:
        raise RuntimeError(f"black {BLACK_VERSION} is pinned for this check, found {black.__version__}")
    d = results_dir(cfg)
    out = d / FORMATTED_FILE
    if force:
        out.unlink(missing_ok=True)
        for f in (d / "scores").glob("*.csv"):  # redone copies reuse sample_ids, so old Scores would attach to new code
            s = read_csv(f)
            s[~s["sample_id"].str.endswith(":fmt")].to_csv(f, index=False)
    done = done_ids(out)
    combine(d)  # samples.csv may predate the formatted column
    samples = read_csv(d / "samples.csv")
    originals = samples[(samples["formatted"] == "False") & (samples["code"].str.strip() != "")]
    rows, failed = [], 0
    for r in originals.to_dict("records"):
        sid = f"{r['sample_id']}:fmt"
        if sid in done:
            continue
        try:
            code, status = black.format_str(r["code"], mode=black.Mode()), "kept"
        except Exception as e:  # black raises InvalidInput on code it cannot parse; the row records why
            code, status = "", f"failed: {type(e).__name__}: {e}"
            failed += 1
            print(f"  {r['sample_id']} not formatted: {status}")
        rows.append({**{c: r[c] for c in SAMPLE_COLUMNS}, "sample_id": sid, "source_id": r["sample_id"],
                     "formatted": "True", "code": code, "status": status, "black_version": black.__version__})
    if rows:
        append_csv(rows, out)
    combine(d)
    all_failed = read_csv(out)["status"].str.startswith("failed").sum() if out.exists() else 0
    print(f"formatted: {len(rows) - failed} new copies, {failed} new Samples and {all_failed} in total "
          f"could not be formatted (see status column)")
