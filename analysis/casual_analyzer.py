# analysis/causal_analyzer.py

def analyze_failure_mechanism(model, topology, failure_mode, traces):
    """
    Why does (model, topology) exhibit this failure mode?
    """
    
    examples = [
        t for t in traces
        if t["model"] == model
        and t["topology"] == topology
        and failure_mode in t["mast_labels"]["failure_modes"]
    ]
    
    # Hypothesis generation based on topology
    if topology == "Star" and failure_mode == "FM-3.1":
        mechanism = {
            "root_cause": "Supervisor bottleneck: can't see specialist progress",
            "evidence": f"{len(examples)} traces show supervisor terminating without feedback",
            "model_specific": {
                "gpt_4o": "More likely to terminate early (impatient)",
                "claude_3_7": "More cautious, less likely FM-3.1",
                "gemini_2_0": "Similar to Claude"
            },
            "example_trace_ids": [e["id"] for e in examples[:3]]
        }
    
    elif topology == "Sequential" and failure_mode == "FM-1.3":
        mechanism = {
            "root_cause": "No backward info flow: Stage N doesn't know Stage N-1 output",
            "evidence": f"{len(examples)} traces show repeated work",
            "model_specific": {
                "gpt_4o": "Better short-term memory, less FM-1.3",
                "claude_3_7": "Higher FM-1.3 rate (context loss?)",
                "gemini_2_0": "Middle ground"
            },
            "example_trace_ids": [e["id"] for e in examples[:3]]
        }
    
    return mechanism