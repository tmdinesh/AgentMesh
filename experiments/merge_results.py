"""
AgentMesh Results Merger & Deduplicator
Unifies multi-agent topology experiment results from partitioned runs and distributed teammates.
Deduplicates runs, sorts observations canonically, merges traces, and regenerates publication artifacts.
"""

import csv
import json
import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("ResultsMerger")

ROOT_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT_DIR / "results"
PARTITIONS_DIR = RESULTS_DIR / "partitions"
FIGURES_DIR = RESULTS_DIR / "figures"
DATASET_FILE = ROOT_DIR / "datasets" / "dataset.json"

CANONICAL_HEADERS = [
    "timestamp", "prompt_id", "prompt_family", "failure_category", "topology",
    "model", "replicate_id", "success", "failure_mode", "total_messages",
    "input_tokens", "output_tokens", "total_tokens", "cost_usd", "latency_sec",
    "graph_density", "coordinator_betweenness", "reciprocity",
    "dissent_ratio", "clarification_rate", "lexical_decay_rate",
    "step_repetition_index", "early_termination_index", "coordinator_dominance", "participation_entropy",
    "failure_diagnosis", "final_answer_snippet"
]

TOPOLOGY_ORDER = {
    "STAR": 0,
    "CHAIN": 1,
    "TREE": 2,
    "MESH": 3,
    "EMERGENT": 4
}


def load_dataset_prompts(dataset_path: Path) -> List[str]:
    """Loads prompt IDs in their original order from dataset.json."""
    if not dataset_path.exists():
        return []
    try:
        with open(dataset_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [p["prompt_id"] for p in data.get("prompts", []) if "prompt_id" in p]
    except Exception as e:
        logger.warning(f"Could not read dataset file {dataset_path}: {e}")
        return []


def score_record(row: Dict[str, Any]) -> float:
    """Computes a quality score for conflict resolution between duplicate runs."""
    score = 0.0
    # Prefer successful runs over failed runs if same prompt/topo/rep
    try:
        if str(row.get("success", "0")).strip() in ("1", "true", "True"):
            score += 100.0
    except Exception:
        pass

    # Prefer runs with valid non-zero token metrics
    try:
        tokens = float(row.get("total_tokens", 0) or 0)
        if tokens > 0:
            score += 10.0
    except Exception:
        pass

    # Tie-breaker: latest timestamp
    ts_str = str(row.get("timestamp", ""))
    if ts_str:
        try:
            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            score += dt.timestamp() / 1e11
        except Exception:
            pass

    return score


def find_candidate_csv_files() -> List[Path]:
    """Locates all CSV result files in results/ and results/partitions/."""
    candidates: Set[Path] = set()
    main_csv = RESULTS_DIR / "experiment_results.csv"
    if main_csv.exists() and main_csv.stat().st_size > 0:
        candidates.add(main_csv.resolve())

    if PARTITIONS_DIR.exists():
        for f in PARTITIONS_DIR.glob("*.csv"):
            if f.stat().st_size > 0:
                candidates.add(f.resolve())

    # Any other csv files in results/ matching pattern (e.g. friend_*.csv, part_*.csv)
    for f in RESULTS_DIR.glob("*results*.csv"):
        if f.resolve() != main_csv.resolve() and f.stat().st_size > 0:
            candidates.add(f.resolve())

    return sorted(list(candidates))


def find_candidate_trace_files() -> List[Path]:
    """Locates all JSONL trace files in results/ and results/partitions/."""
    candidates: Set[Path] = set()
    main_trace = RESULTS_DIR / "traces.jsonl"
    if main_trace.exists() and main_trace.stat().st_size > 0:
        candidates.add(main_trace.resolve())

    if PARTITIONS_DIR.exists():
        for f in PARTITIONS_DIR.glob("*.jsonl"):
            if f.stat().st_size > 0:
                candidates.add(f.resolve())

    for f in RESULTS_DIR.glob("*trace*.jsonl"):
        if f.resolve() != main_trace.resolve() and f.stat().st_size > 0:
            candidates.add(f.resolve())

    return sorted(list(candidates))


def merge_csv_records(csv_files: List[Path], prompt_order: List[str], output_csv: Path) -> Dict[str, Any]:
    """Reads all candidate CSV files, deduplicates by experiment key, and writes unified CSV."""
    prompt_order_map = {pid: idx for idx, pid in enumerate(prompt_order)}
    records_by_key: Dict[Tuple[str, str, str, str], Tuple[float, Dict[str, Any]]] = {}
    total_raw_rows = 0
    duplicate_count = 0

    for file_path in csv_files:
        logger.info(f"Reading CSV observations from {file_path.name}...")
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    total_raw_rows += 1
                    p_id = str(row.get("prompt_id", "")).strip()
                    topo = str(row.get("topology", "")).strip().upper()
                    model = str(row.get("model", "")).strip()
                    rep = str(row.get("replicate_id", "1")).strip()

                    if not p_id or not topo:
                        continue

                    key = (p_id, topo, model, rep)
                    score = score_record(row)

                    if key in records_by_key:
                        duplicate_count += 1
                        existing_score, _ = records_by_key[key]
                        if score > existing_score:
                            records_by_key[key] = (score, row)
                    else:
                        records_by_key[key] = (score, row)
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")

    # Sort merged rows canonically
    def sort_key(item: Tuple[Tuple[str, str, str, str], Tuple[float, Dict[str, Any]]]):
        (p_id, topo, model, rep), _ = item
        p_idx = prompt_order_map.get(p_id, 999999)
        t_idx = TOPOLOGY_ORDER.get(topo, 99)
        try:
            r_idx = int(rep)
        except ValueError:
            r_idx = 999
        return (p_idx, p_id, t_idx, model, r_idx)

    sorted_records = sorted(records_by_key.items(), key=sort_key)

    # Determine all headers
    all_headers = list(CANONICAL_HEADERS)
    for _, (_, row) in sorted_records:
        for k in row.keys():
            if k and k not in all_headers:
                all_headers.append(k)

    # Write atomic output
    temp_output = output_csv.with_suffix(".csv.tmp")
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(temp_output, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(all_headers)
        for _, (_, row) in sorted_records:
            writer.writerow([row.get(h, "") for h in all_headers])

    # Replace target file
    shutil.move(str(temp_output), str(output_csv))
    logger.info(f"Unified CSV successfully written: {output_csv} ({len(sorted_records)} unique runs)")

    unique_prompts = set(key[0] for key in records_by_key.keys())
    return {
        "raw_rows": total_raw_rows,
        "unique_runs": len(sorted_records),
        "duplicates_resolved": duplicate_count,
        "unique_prompts": unique_prompts
    }


def merge_traces_files(trace_files: List[Path], output_trace: Path) -> int:
    """Deduplicates and merges JSONL traces into unified file."""
    traces_by_key: Dict[Tuple[str, str, str, str], Tuple[float, str]] = {}

    for file_path in trace_files:
        logger.info(f"Reading traces from {file_path.name}...")
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        p_id = str(record.get("prompt_id", "")).strip()
                        topo = str(record.get("topology", "")).strip().upper()
                        model = str(record.get("model", "")).strip()
                        rep = str(record.get("replicate_id", "1")).strip()
                        if not p_id or not topo:
                            continue
                        key = (p_id, topo, model, rep)
                        score = score_record(record)
                        if key in traces_by_key:
                            existing_score, _ = traces_by_key[key]
                            if score > existing_score:
                                traces_by_key[key] = (score, line)
                        else:
                            traces_by_key[key] = (score, line)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"Error reading trace file {file_path}: {e}")

    temp_trace = output_trace.with_suffix(".jsonl.tmp")
    output_trace.parent.mkdir(parents=True, exist_ok=True)
    with open(temp_trace, "w", encoding="utf-8") as f:
        for _, (_, line_content) in traces_by_key.items():
            f.write(line_content + "\n")

    shutil.move(str(temp_trace), str(output_trace))
    logger.info(f"Unified Traces JSONL written: {output_trace} ({len(traces_by_key)} records)")
    return len(traces_by_key)


def print_status_dashboard(stats: Dict[str, Any], prompt_order: List[str]):
    """Prints a friendly terminal dashboard of overall benchmark progress."""
    total_prompts = len(prompt_order) or 65
    completed_prompts: Set[str] = stats.get("unique_prompts", set())
    num_completed = len(completed_prompts)
    pct = (num_completed / max(1, total_prompts)) * 100.0

    print("\n" + "=" * 78)
    print("           AgentMesh MAST Topology Benchmark - Unified Progress            ")
    print("=" * 78)
    print(f"Total Observations Scanned : {stats.get('raw_rows', 0)}")
    print(f"Deduplicated Unique Runs   : {stats.get('unique_runs', 0)}")
    print(f"Duplicates / Collisions    : {stats.get('duplicates_resolved', 0)} automatically resolved")
    print(f"Prompt Coverage            : {num_completed} / {total_prompts} prompts ({pct:.1f}%)")
    print("-" * 78)

    # Calculate pending prompt ranges
    pending_indices = []
    completed_indices = []
    for idx, pid in enumerate(prompt_order, 1):
        if pid in completed_prompts:
            completed_indices.append(idx)
        else:
            pending_indices.append(idx)

    if completed_indices:
        print(f"[+] Completed Prompt Numbers : {format_ranges(completed_indices)}")
    if pending_indices:
        print(f"[!] Remaining Pending Numbers : {format_ranges(pending_indices)}")
        print("\nSuggested Team Prompt Distribution for Friends:")
        # Divide pending prompts into 3 chunks
        chunks = chunk_list(pending_indices, 3)
        labels = ["Teammate 1", "Teammate 2", "Teammate 3"]
        for lbl, ch in zip(labels, chunks):
            if ch:
                print(f"    - {lbl:12}: Prompts {ch[0]} to {ch[-1]}  (run_experiments.bat {ch[0]} {ch[-1]})")
    else:
        print("\n[SUCCESS] ALL 65 PROMPTS FULLY COMPLETED ACROSS ALL CONDITIONS!")
    print("=" * 78 + "\n")


def format_ranges(numbers: List[int]) -> str:
    """Formats a list of integers into human-friendly ranges: 1-15, 20-35."""
    if not numbers:
        return "None"
    ranges = []
    start = numbers[0]
    prev = numbers[0]
    for n in numbers[1:]:
        if n == prev + 1:
            prev = n
        else:
            ranges.append(f"#{start}-#{prev}" if start != prev else f"#{start}")
            start = n
            prev = n
    ranges.append(f"#{start}-#{prev}" if start != prev else f"#{start}")
    return ", ".join(ranges)


def chunk_list(lst: List[int], n: int) -> List[List[int]]:
    """Splits a list into n approximately equal parts."""
    if not lst:
        return []
    k, m = divmod(len(lst), n)
    return [lst[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n)]


def merge_all_results():
    """Main entrypoint for merging results, traces, and regenerating artifacts."""
    prompt_order = load_dataset_prompts(DATASET_FILE)
    csv_files = find_candidate_csv_files()
    trace_files = find_candidate_trace_files()

    if not csv_files:
        print("[-] No experiment results found to merge.")
        return

    print(f"[*] Found {len(csv_files)} CSV file(s) and {len(trace_files)} trace file(s) across results/ and results/partitions/.")

    output_csv = RESULTS_DIR / "experiment_results.csv"
    output_traces = RESULTS_DIR / "traces.jsonl"

    stats = merge_csv_records(csv_files, prompt_order, output_csv)
    if trace_files:
        merge_traces_files(trace_files, output_traces)

    # Regenerate all artifacts
    print("[*] Recomputing statistical analysis, publication figures, and LaTeX tables...")
    try:
        # Add root and backend to sys.path
        if str(ROOT_DIR) not in sys.path:
            sys.path.insert(0, str(ROOT_DIR))
        from analysis.generate_paper_artifacts import generate_all_artifacts
        generate_all_artifacts(output_csv, RESULTS_DIR, FIGURES_DIR)
        print("[+] Figures and statistical summary updated in results/figures/ and results/")
    except Exception as e:
        logger.error(f"Error updating paper artifacts: {e}")

    try:
        from analysis.export_transcripts import export_transcripts_to_markdown
        export_transcripts_to_markdown()
        print("[+] Deliberation transcripts updated in results/transcripts/")
    except Exception as e:
        logger.error(f"Error exporting transcripts: {e}")

    print_status_dashboard(stats, prompt_order)


if __name__ == "__main__":
    merge_all_results()
