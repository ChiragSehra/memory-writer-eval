from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import load_config
from .judge import refresh_score_summary, score_synthetic
from .runner import export_blind_sheet, run_models
from .runner import configured_writers
from .scoring import merge_human_scores
from .blind_judge import score_blind_sheet
from .write_metrics import export_write_sheet, report_write_support
from .checkpoint_review import export_checkpoint_sheet, score_checkpoint_sheet, report_checkpoint_scores
from .failure_types import classify_write_failures, report_failure_types
from .real_tracing import export_trace_sheet, score_trace_sheet, report_traces
from .beam import import_beam_chat, answer_beam_probes, score_beam_pilot
from .snapshot import create_snapshot, verify_snapshot
from .synthetic import generate
from .writer import MemoryWriter


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate local and OpenRouter LLM memory writers.")
    parser.add_argument("--config", default="config.yaml")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("preflight", help="List local models and make a tiny call to each configured OpenRouter model.")
    commands.add_parser("generate-synthetic", help="Generate synthetic test threads and ground truth.")
    run = commands.add_parser("run", help="Run every configured model over transcripts.")
    run.add_argument("--input", default="data/transcripts")
    run.add_argument("--threads", type=int)
    run.add_argument("--sessions", type=int, help="Limit sessions per thread; use 2 for the smoke test.")
    run.add_argument("--output-root", default="runs")
    run.add_argument("--resume", help="Resume an interrupted run directory without re-calling completed sessions.")
    run.add_argument("--models", help="Comma-separated target labels to run; useful with --resume and --retry-errors.")
    run.add_argument("--retry-errors", action="store_true", help="Re-run existing records with a transport or schema error.")
    run.add_argument("--max-output-tokens", type=int, help="Override the writer output limit for this run.")
    run.add_argument("--reasoning-effort", choices=["low", "medium", "high"], help="Optional reasoning effort for compatible endpoints.")
    run.add_argument("--request-timeout-s", type=int, help="Override the per-call timeout for this run.")
    blind = commands.add_parser("export-blind", help="Create a shuffled human-scoring sheet from a run.")
    blind.add_argument("run_dir")
    blind.add_argument("--output", default="scoring/blind_sheet.csv")
    blind.add_argument("--input", default="data/synthetic", help="Original session directory used for the run, to include full evidence.")
    blind_judge = commands.add_parser("score-blind", help="Score a blinded export with a second model judge, without revealing model identities.")
    blind_judge.add_argument("sheet")
    blind_judge.add_argument("--judge", required=True, help="Configured OpenRouter model name, distinct from judge.name.")
    blind_judge.add_argument("--output", default="scoring/second_judge_scores.csv")
    writes = commands.add_parser("export-writes", help="Blind all applied add/update operations for per-write scoring.")
    writes.add_argument("run_dir")
    writes.add_argument("--input", default="data/synthetic")
    writes.add_argument("--output", default="scoring/write_sheet.csv")
    write_report = commands.add_parser("report-writes", help="Report unsupported writes over all applied writes by model.")
    write_report.add_argument("sheet")
    write_report.add_argument("key")
    write_report.add_argument("scores")
    write_report.add_argument("--output", default="scoring/write_support_report.md")
    checkpoints = commands.add_parser("export-checkpoints", help="Blind every complete synthetic memory-store checkpoint.")
    checkpoints.add_argument("run_dir")
    checkpoints.add_argument("--input", default="data/synthetic")
    checkpoints.add_argument("--output", default="scoring/checkpoint_sheet.csv")
    checkpoint_judge = commands.add_parser("score-checkpoints", help="Score all blinded checkpoints with an independent model judge.")
    checkpoint_judge.add_argument("sheet")
    checkpoint_judge.add_argument("--judge", required=True)
    checkpoint_judge.add_argument("--output", default="scoring/checkpoint_judge_scores.csv")
    checkpoint_report = commands.add_parser("report-checkpoints", help="Summarize blinded checkpoint scores by model.")
    checkpoint_report.add_argument("sheet")
    checkpoint_report.add_argument("key")
    checkpoint_report.add_argument("scores")
    checkpoint_report.add_argument("--output", default="scoring/checkpoint_report.md")
    classify = commands.add_parser("classify-writes", help="Classify unsupported writes by primary failure type.")
    classify.add_argument("sheet")
    classify.add_argument("scores")
    classify.add_argument("--judge", required=True)
    classify.add_argument("--output", default="scoring/write_failure_types.csv")
    type_report = commands.add_parser("report-write-types", help="Summarize failure types by writer model.")
    type_report.add_argument("key")
    type_report.add_argument("classifications")
    type_report.add_argument("--output", default="scoring/write_failure_type_report.md")
    trace_export = commands.add_parser("export-traces", help="Attach structured message histories to a blind write sheet.")
    trace_export.add_argument("write_sheet")
    trace_export.add_argument("key")
    trace_export.add_argument("--input", default="data/transcripts")
    trace_export.add_argument("--output", default="scoring/trace_sheet.csv")
    trace_score = commands.add_parser("score-traces", help="Trace each write to exact user-message quotes and IDs.")
    trace_score.add_argument("sheet")
    trace_score.add_argument("--judge", required=True)
    trace_score.add_argument("--output", default="scoring/trace_scores.csv")
    trace_report = commands.add_parser("report-traces", help="Summarize message-level provenance coverage.")
    trace_report.add_argument("sheet")
    trace_report.add_argument("key")
    trace_report.add_argument("scores")
    trace_report.add_argument("--output", default="scoring/real_trace_report.md")
    beam = commands.add_parser("import-beam", help="Convert one official BEAM chat to ordered writer sessions.")
    beam.add_argument("chat_json")
    beam.add_argument("--chat-id", required=True)
    beam.add_argument("--output", default="data/beam_sessions")
    beam_answer = commands.add_parser("answer-beam", help="Answer official BEAM probes from a writer's final memory store.")
    beam_answer.add_argument("run_dir")
    beam_answer.add_argument("questions_json")
    beam_answer.add_argument("--writer", required=True)
    beam_answer.add_argument("--reader", required=True)
    beam_answer.add_argument("--expected-sessions", type=int)
    beam_answer.add_argument("--output", default="scoring/beam_answers.json")
    beam_score = commands.add_parser("score-beam-pilot", help="Exploratory rubric scoring of memory-only BEAM answers.")
    beam_score.add_argument("answers_json")
    beam_score.add_argument("questions_json")
    beam_score.add_argument("--judge", required=True)
    beam_score.add_argument("--output", default="scoring/beam_pilot_scores.json")
    snapshot = commands.add_parser("snapshot", help="Freeze a complete synthetic run and its reports in a dated directory.")
    snapshot.add_argument("run_dir")
    snapshot.add_argument("--output", required=True)
    snapshot.add_argument("--artifact", action="append", default=[], help="Extra NAME=PATH artifact to include; repeat for each report or score file.")
    snapshot_verify = commands.add_parser("verify-snapshot", help="Check snapshot artifact and source hashes.")
    snapshot_verify.add_argument("snapshot_dir")
    snapshot_verify.add_argument("--check-workspace", action="store_true", help="Also require the current source tree to match the frozen snapshot.")
    merge = commands.add_parser("merge-scores", help="Restore model identities after human scoring.")
    merge.add_argument("sheet")
    merge.add_argument("key")
    merge.add_argument("output")
    score = commands.add_parser("score-synthetic", help="Judge every synthetic memory checkpoint with the configured OpenRouter judge.")
    score.add_argument("run_dir")
    score.add_argument("--retry-errors", action="store_true", help="Keep successful scores and retry only failed or missing judge verdicts.")
    refresh = commands.add_parser("refresh-score-summary", help="Rebuild synthetic score summary without API calls.")
    refresh.add_argument("run_dir")
    args = parser.parse_args()
    config = load_config(args.config)
    if args.command == "generate-synthetic":
        generate()
        print("Generated synthetic threads in data/synthetic/")
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
        config["runtime"] = dict(config["runtime"])
        if args.max_output_tokens is not None:
            config["runtime"]["max_output_tokens"] = args.max_output_tokens
        if args.reasoning_effort:
            config["runtime"]["reasoning_effort"] = args.reasoning_effort
        if args.request_timeout_s is not None:
            config["runtime"]["request_timeout_s"] = args.request_timeout_s
        destination = run_models(config, args.input, args.threads, args.sessions, args.output_root, args.resume, model_names, args.retry_errors)
        print(destination)
    elif args.command == "export-blind":
        sheet, key = export_blind_sheet(args.run_dir, args.output, args.input)
        print(f"sheet={sheet} key={key}")
    elif args.command == "score-blind":
        print(score_blind_sheet(args.sheet, args.output, config, args.judge))
    elif args.command == "export-writes":
        sheet, key = export_write_sheet(args.run_dir, args.input, args.output)
        print(f"sheet={sheet} key={key}")
    elif args.command == "report-writes":
        print(report_write_support(args.sheet, args.key, args.scores, args.output))
    elif args.command == "export-checkpoints":
        sheet, key = export_checkpoint_sheet(args.run_dir, args.input, args.output)
        print(f"sheet={sheet} key={key}")
    elif args.command == "score-checkpoints":
        print(score_checkpoint_sheet(args.sheet, args.output, config, args.judge))
    elif args.command == "report-checkpoints":
        print(report_checkpoint_scores(args.sheet, args.key, args.scores, args.output))
    elif args.command == "classify-writes":
        print(classify_write_failures(args.sheet, args.scores, args.output, config, args.judge))
    elif args.command == "report-write-types":
        print(report_failure_types(args.key, args.classifications, args.output))
    elif args.command == "export-traces":
        print(export_trace_sheet(args.write_sheet, args.key, args.input, args.output))
    elif args.command == "score-traces":
        print(score_trace_sheet(args.sheet, args.output, config, args.judge))
    elif args.command == "report-traces":
        print(report_traces(args.sheet, args.key, args.scores, args.output))
    elif args.command == "import-beam":
        print(import_beam_chat(args.chat_json, args.output, args.chat_id))
    elif args.command == "answer-beam":
        print(answer_beam_probes(args.run_dir, args.questions_json, config, args.writer, args.reader, args.output, args.expected_sessions))
    elif args.command == "score-beam-pilot":
        print(score_beam_pilot(args.answers_json, args.questions_json, config, args.judge, args.output))
    elif args.command == "snapshot":
        artifacts = dict(item.split("=", 1) for item in args.artifact)
        print(create_snapshot(args.run_dir, args.output, config, artifacts))
    elif args.command == "verify-snapshot":
        manifest = verify_snapshot(args.snapshot_dir, check_workspace=args.check_workspace)
        print(f"verified {len(manifest['artifact_hashes'])} artifacts and {len(manifest['source_hashes'])} source files")
    elif args.command == "score-synthetic":
        print(score_synthetic(args.run_dir, config, retry_errors=args.retry_errors))
    elif args.command == "refresh-score-summary":
        refresh_score_summary(args.run_dir)
        print(Path(args.run_dir) / "report.md")
    else:
        print(merge_human_scores(args.sheet, args.key, args.output))


if __name__ == "__main__":
    main()
