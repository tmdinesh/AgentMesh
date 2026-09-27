"""
AgentMesh Transcript Exporter
Converts results/traces.jsonl into publication-ready Markdown transcripts and case studies.
Ideal for paper appendices, qualitative failure mode analysis, and reviewer validation.
"""

import json
from pathlib import Path
from typing import Dict, Any

ROOT_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT_DIR / "results"
TRACES_FILE = RESULTS_DIR / "traces.jsonl"
OUTPUT_DIR = RESULTS_DIR / "transcripts"


def export_transcripts_to_markdown():
    if not TRACES_FILE.exists():
        print(f"[-] Traces file not found at {TRACES_FILE}")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    count = 0

    with open(TRACES_FILE, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                run = json.loads(line)
            except Exception as e:
                print(f"[!] Error parsing line {idx}: {e}")
                continue

            p_id = run.get("prompt_id", "UnknownPrompt")
            topo = run.get("topology", "UnknownTopo")
            model = run.get("model", "UnknownModel")
            rep = run.get("replicate_id", 1)
            success = run.get("success", 0)
            fm = run.get("failure_mode", "None")

            filename = f"{p_id}_{topo}_{model}_rep{rep}.md"
            filepath = OUTPUT_DIR / filename

            status_str = "SUCCESS" if success == 1 else f"FAILED ({fm})"

            md = []
            md.append(f"# Multi-Agent Deliberation Transcript: {p_id}")
            md.append(f"**Topology:** `{topo}` | **Model Condition:** `{model}` | **Replicate:** `#{rep}` | **Outcome:** **{status_str}**")
            md.append(f"- **Timestamp:** {run.get('timestamp')}")
            md.append(f"- **Tokens:** {run.get('total_tokens', 0):,} (Input: {run.get('input_tokens', 0):,}, Output: {run.get('output_tokens', 0):,})")
            md.append(f"- **Cost:** ${run.get('cost_usd', 0):.5f} | **Latency:** {run.get('latency_sec', 0)}s")
            md.append(f"- **Failure Mode Diagnosis:** {run.get('failure_diagnosis', 'None')}")
            md.append("\n---\n")

            prompt_text = run.get("prompt_text")
            if prompt_text:
                md.append("## Original Problem & Specifications")
                md.append(f"```text\n{prompt_text}\n```\n")

            md.append("## Multi-Agent Communication Dialogue")
            transcript = run.get("transcript", [])
            if not transcript:
                md.append("*No message history recorded.*")
            else:
                for msg in transcript:
                    turn = msg.get("turn", "?")
                    s_role = msg.get("sender_role", "Agent")
                    s_model = msg.get("sender_model", "")
                    r_role = msg.get("receiver_role", "Agent")
                    content = msg.get("content", "").strip()

                    md.append(f"### [Turn {turn}] {s_role} ({s_model}) -> {r_role}")
                    md.append(f"{content}\n")

            final_answer = run.get("final_answer") or run.get("final_answer_snippet")
            if final_answer:
                md.append("\n---\n")
                md.append("## Synthesized Final Team Output")
                md.append(f"{final_answer}\n")

            eval1 = run.get("eval1_output")
            if eval1:
                md.append("\n---\n")
                md.append("## Academic Judge Evaluation (Stage 1)")
                md.append(f"{eval1}\n")

            eval2 = run.get("eval2_output")
            if eval2:
                md.append("\n---\n")
                md.append("## Academic Judge Failure Mode Classification (Stage 2)")
                md.append(f"{eval2}\n")

            with open(filepath, "w", encoding="utf-8") as out_f:
                out_f.write("\n".join(md))

            count += 1

    print(f"[+] Successfully exported {count} publication transcripts to {OUTPUT_DIR}/")


if __name__ == "__main__":
    export_transcripts_to_markdown()
