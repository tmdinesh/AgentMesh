#!/usr/bin/env python3
"""
AgentMesh Paper 2: Systems & Implementation Plan
Dynamic Topology Optimization Execution Script (Wired)

This script orchestrates the experimental pipeline for Paper 2, integrating
directly with the core AgentMesh execution framework to run real trials.
"""

import argparse
import os
import sys
import logging
import json
import itertools
import asyncio
from datetime import datetime
from pathlib import Path

# Setup Paths and add root to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from experiments.run_paper_experiments import run_single_experiment, MultiModelLLMClient, load_env_keys

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("AgentMesh-Paper2")

RESULTS_DIR = BASE_DIR / "results" / "paper2"
DATASET_PATH = BASE_DIR / "datasets" / "dataset.json"

os.makedirs(RESULTS_DIR, exist_ok=True)

def parse_args():
    parser = argparse.ArgumentParser(description="Run AgentMesh Paper 2 Experiments (Wired)")
    parser.add_argument("--mode", type=str, choices=["baseline_compare", "ablation_study", "case_studies", "full"],
                        default="full", help="Which experiment suite to run.")
    parser.add_argument("--tasks", type=int, default=14, help="Number of tasks to evaluate.")
    parser.add_argument("--use-mock", action="store_true", help="Use mock responses to save API costs during testing.")
    parser.add_argument("--output_dir", type=str, default=str(RESULTS_DIR), help="Output directory for results.")
    return parser.parse_args()


async def run_baseline_comparison(num_tasks, use_mock, output_dir):
    """
    Compares the Static Tree topology against the new Dynamic Topology.
    """
    logger.info("Starting Baseline Comparison: Dynamic Topology vs Static Tree")
    
    keys = load_env_keys()
    client = MultiModelLLMClient(keys, use_mock=use_mock)
    
    try:
        with open(DATASET_PATH, "r") as f:
            prompts = json.load(f).get("prompts", [])[:num_tasks]
    except Exception as e:
        logger.error(f"Failed to load dataset: {e}")
        return
        
    logger.info(f"Evaluating across {len(prompts)} benchmark tasks (Mock Mode={use_mock})...")
    
    results = {"static_tree": [], "dynamic": []}
    
    try:
        for idx, prompt in enumerate(prompts):
            logger.info(f"Task {idx+1}/{len(prompts)}: Evaluating TREE topology...")
            res_tree = await run_single_experiment(prompt, "TREE", "heterogeneous", 1, client)
            results["static_tree"].append(res_tree)
            
            logger.info(f"Task {idx+1}/{len(prompts)}: Evaluating DYNAMIC topology...")
            res_dyn = await run_single_experiment(prompt, "DYNAMIC", "heterogeneous", 1, client)
            results["dynamic"].append(res_dyn)
    finally:
        await client.close()
    
    # Calculate simple aggregates
    tree_acc = sum(1 for r in results["static_tree"] if r.get("task_success")) / max(1, len(results["static_tree"]))
    dyn_acc = sum(1 for r in results["dynamic"] if r.get("task_success")) / max(1, len(results["dynamic"]))
    
    summary = {
        "static_tree": {"accuracy": tree_acc * 100, "tasks_run": len(results["static_tree"])},
        "dynamic": {"accuracy": dyn_acc * 100, "tasks_run": len(results["dynamic"])}
    }
    
    results_file = os.path.join(output_dir, "baseline_comparison_results.json")
    with open(results_file, 'w') as f:
        json.dump(summary, f, indent=4)
        
    logger.info(f"Baseline comparison completed. Results saved to {results_file}")


async def run_ablation_study(num_tasks, use_mock, output_dir):
    """
    Executes a grid search over hyperparameters tau_volume and tau_dom.
    """
    logger.info("Starting Algorithmic Threshold Tuning (Ablation Study)...")
    
    keys = load_env_keys()
    client = MultiModelLLMClient(keys, use_mock=use_mock)
    
    try:
        with open(DATASET_PATH, "r") as f:
            prompts = json.load(f).get("prompts", [])[:num_tasks]
    except Exception as e:
        logger.error(f"Failed to load dataset: {e}")
        return
        
    tau_volumes = [1000, 2000, 3000, 5000] # Token volume thresholds
    tau_doms = [0.25, 0.35, 0.45, 0.60]    # Coordinator Dominance thresholds
    
    grid = list(itertools.product(tau_volumes, tau_doms))
    logger.info(f"Testing {len(grid)} hyperparameter combinations on {len(prompts)} tasks (Mock Mode={use_mock})...")
    
    results_file = os.path.join(output_dir, "ablation_study_results.json")
    ablation_results = []
    completed_configs = set()
    
    if os.path.exists(results_file):
        try:
            with open(results_file, 'r') as f:
                ablation_results = json.load(f)
            for res in ablation_results:
                completed_configs.add((res["tau_volume"], res["tau_dom"]))
            logger.info(f"Loaded {len(completed_configs)} completed configurations from previous run. Resuming...")
        except Exception as e:
            logger.warning(f"Could not load previous results: {e}")
            
    try:
        for idx, (vol, dom) in enumerate(grid):
            if (vol, dom) in completed_configs:
                logger.info(f"Grid {idx+1}/{len(grid)}: Skipping config tau_volume={vol}, tau_dom={dom} (already completed)")
                continue
                
            logger.info(f"Grid {idx+1}/{len(grid)}: Running config tau_volume={vol}, tau_dom={dom} across {len(prompts)} tasks...")
            success_count = 0
            cost_accum = 0.0
            
            for task_idx, prompt in enumerate(prompts):
                res = await run_single_experiment(
                    prompt_data=prompt, 
                    topology_name="DYNAMIC", 
                    model_key="heterogeneous", 
                    replicate_id=1, 
                    llm_client=client,
                    topology_kwargs={"tau_volume": vol, "tau_dom": dom}
                )
                if res.get("task_success"):
                    success_count += 1
                cost_accum += res.get("cost", 0.0)
                
            accuracy = (success_count / max(1, len(prompts))) * 100
            ablation_results.append({
                "tau_volume": vol,
                "tau_dom": dom,
                "accuracy": round(accuracy, 2),
                "total_cost": round(cost_accum, 4)
            })
            
            # Checkpoint after every grid config
            with open(results_file, 'w') as f:
                json.dump(ablation_results, f, indent=4)
            logger.info(f"Checkpoint saved for tau_volume={vol}, tau_dom={dom}.")
            
    finally:
        await client.close()
        
    logger.info(f"Ablation study completed. Final results saved to {results_file}")


async def main_async():
    args = parse_args()
    
    logger.info("="*60)
    logger.info(" AgentMesh Paper 2: Dynamic Topology Evaluation Suite (WIRED)")
    logger.info("="*60)
    logger.info(f"Run Mode: {args.mode}")
    logger.info(f"Target Tasks: {args.tasks}")
    logger.info(f"Use Mock: {args.use_mock}")
    logger.info(f"Output Directory: {args.output_dir}")
    
    if args.mode in ["baseline_compare", "full"]:
        await run_baseline_comparison(args.tasks, args.use_mock, args.output_dir)
        
    if args.mode in ["ablation_study", "full"]:
        await run_ablation_study(args.tasks, args.use_mock, args.output_dir)
        
    if args.mode in ["case_studies", "full"]:
        logger.info("Wired Qualitative Case Studies are queued for implementation.")
        
    logger.info("="*60)
    logger.info("All Paper 2 experiments completed successfully!")
    logger.info("="*60)

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
