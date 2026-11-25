"""
Mini Courtroom — run it three ways:

    python app.py --sample rent-deposit        # CLI, sample case
    python app.py --case "Priya paid ..."      # CLI, your own case
    python app.py --serve                      # Web UI on :5000

Web API:  POST /api/hearing {"case": "..."} -> transcript + verdict JSON
          GET  /api/samples                    -> the 3 sample cases
          GET  /health
"""
import argparse
import json
import os
import sys

from courtroom import run_hearing
from samples import SAMPLES


def print_hearing(result: dict) -> None:
    s = result["case_summary"]
    print(f"\nCASE: {s['issue']} — {s['plaintiff']} vs {s['defendant']}")
    if s["amounts"]:
        print(f"Amount: {', '.join(s['amounts'])}")
    print("=" * 70)
    for t in result["transcript"]:
        print(f"\n[Round {t['round_no']} — {t['round_name']}] {t['speaker']} "
              f"({t['role']})")
        print("-" * 70)
        print(t["text"])
    v = result["verdict"]
    print("\n" + "=" * 70)
    print(f"⚖  VERDICT: {v['verdict']}")
    print(f"Scores — Prosecution {v['prosecution_avg']}/10 | "
          f"Defense {v['defense_avg']}/10 | Confidence {v['confidence_pct']}%")
    print(f"Order: {v['order']}")
    print(f"\n{result['disclaimer']}")


def serve():
    try:
        from flask import Flask, jsonify, render_template, request
    except ImportError:
        sys.exit("Flask is not installed — run: pip install -r requirements.txt")
    app = Flask(__name__)

    @app.get("/")
    def index():
        return render_template("index.html", samples=SAMPLES)

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.get("/api/samples")
    def samples():
        return jsonify(SAMPLES)

    @app.post("/api/hearing")
    def hearing():
        data = request.get_json(force=True, silent=True) or {}
        case = (data.get("case") or "").strip()
        if len(case) < 20:
            return jsonify({"error": "Please describe the case in at least "
                                     "a sentence or two (20+ characters)."}), 400
        try:
            return jsonify(run_hearing(case))
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    port = int(os.environ.get("PORT", "5000"))
    print(f"Mini Courtroom running at http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port)


def main():
    p = argparse.ArgumentParser(description="Mini Courtroom — AI agents debate, Judge decides.")
    p.add_argument("--case", help="Problem statement / case facts")
    p.add_argument("--sample", choices=[s["id"] for s in SAMPLES],
                   help="Run a built-in sample case")
    p.add_argument("--serve", action="store_true", help="Start the web UI")
    p.add_argument("--json", action="store_true", help="Print raw JSON (CLI)")
    args = p.parse_args()

    if args.serve:
        serve()
        return
    if args.sample:
        case = next(s["case"] for s in SAMPLES if s["id"] == args.sample)
    elif args.case:
        case = args.case
    else:
        p.print_help()
        sys.exit(1)
    result = run_hearing(case)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print_hearing(result)


if __name__ == "__main__":
    main()
