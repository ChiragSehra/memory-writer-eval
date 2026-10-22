from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import load_config
from .judge import refresh_score_summary, score_synthetic
from .runner import export_blind_sheet, run_models
from .runner import configured_writers
from .scoring import merge_human_scores
from .synthetic import generate
from .writer import MemoryWriter


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate local and OpenRouter LLM memory writers.")
    parser.add_argument("--config", default="config.yaml")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("preflight", help="List local models and make a tiny call to each configured OpenRouter model.")
    commands.add_parser("generate-synthetic", help="Generate three synthetic test threads and ground truth.")
    run = commands.add_parser("run", help="Run every configured model over transcripts.")
    run.add_argument("--input", default="data/transcripts")
    run.add_argument("--threads", type=int)
    run.add_argument("--sessions", type=int, help="Limit sessions per thread; use 2 for the smoke test.")
    run.add_argument("--output-root", default="runs")
    run.add_argument("--resume", help="Resume an interrupted run directory without re-calling completed sessions.")
    run.add_argument("--models", help="Comma-separated target labels to run; useful with --resume and --retry-errors.")
    run.add_argument("--retry-errors", action="store_true", help="Re-run existing records with a transport or schema error.")
    blind = commands.add_parser("export-blind", help="Create a shuffled human-scoring sheet from a run.")
    blind.add_argument("run_dir")
    blind.add_argument("--output", default="scoring/blind_sheet.csv")
    merge = commands.add_parser("merge-scores", help="Restore model identities after human scoring.")
    merge.add_argument("sheet")
    merge.add_argument("key")
    merge.add_argument("output")
    score = commands.add_parser("score-synthetic", help="Judge every synthetic memory checkpoint with the configured OpenRouter judge.")
    score.add_argument("run_dir")
    refresh = commands.add_parser("refresh-score-summary", help="Rebuild synthetic score summary without API calls.")
    refresh.add_argument("run_dir")
    args = parser.parse_args()
    config = load_config(args.config)
    if args.command == "generate-synthetic":
        generate()
        print("Generated 3 synthetic threads in data/synthetic/")
    elif args.command == "preflight":
        local = MemoryWriter("local", config["local"], config["runtime"])
        print("LM Studio models:", json.dumps(local.list_models(), indent=2))
        for name, settings in configured_writers(config):
            if name == "local":
                continue
            remote = MemoryWriter(name, settings, config["runtime"])
            result = remote.tiny_test()
            print(f"{name} test output:", result.raw_content)
    elif args.command == "run":
        model_names = set(args.models.split(",")) if args.models else None
        destination = run_models(config, args.input, args.threads, args.sessions, args.output_root, args.resume, model_names, args.retry_errors)
        print(destination)
    elif args.command == "export-blind":
        sheet, key = export_blind_sheet(args.run_dir, args.output)
        print(f"sheet={sheet} key={key}")
    elif args.command == "score-synthetic":
        print(score_synthetic(args.run_dir, config))
    elif args.command == "refresh-score-summary":
        refresh_score_summary(args.run_dir)
        print(Path(args.run_dir) / "report.md")
    else:
        print(merge_human_scores(args.sheet, args.key, args.output))


if __name__ == "__main__":
    main()
