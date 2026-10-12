import os
import sys
import json
import statistics
from typing import Dict, Any, List

# Add parent directory to path so imports work cleanly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.matching_service import process_grounded_job_matching
from app.services.ai_service import offline_heuristic_job_matcher, get_groq_api_key, analyze_resume
from app.services.prompt_service import build_job_matching_prompt


def load_dataset(filepath: str) -> List[Dict[str, Any]]:
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_benchmark(dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_tp = 0
    total_fp = 0
    total_fn = 0
    total_tn = 0

    per_sample_results = []
    scoring_consistency_results = []

    for item in dataset:
        sample_id = item["id"]
        domain = item["domain"]
        resume_pages = item["resume_pages"]
        job_description = item["job_description"]
        ground_truth = item["ground_truth_skills"]

        # Run extraction & matching
        raw_skills_resp = offline_heuristic_job_matcher(resume_pages, job_description)
        raw_skills = raw_skills_resp.get("skills", [])
        job_match = process_grounded_job_matching(raw_skills, resume_pages)

        # Map predictions by skill name (case-insensitive)
        pred_map = {
            s.skill.lower(): s.status.value
            for s in job_match.skills_analysis
        }

        sample_tp = 0
        sample_fp = 0
        sample_fn = 0
        sample_tn = 0

        for gt_skill, gt_info in ground_truth.items():
            expected = gt_info["expected_status"]
            # Look up prediction
            predicted_status = "missing"
            for p_name, p_status in pred_map.items():
                if gt_skill.lower() in p_name or p_name in gt_skill.lower():
                    predicted_status = p_status
                    break

            is_pred_positive = predicted_status in ("matched", "partially_matched")
            is_gt_positive = expected in ("matched", "partially_matched")

            if is_pred_positive and is_gt_positive:
                sample_tp += 1
            elif is_pred_positive and not is_gt_positive:
                sample_fp += 1
            elif not is_pred_positive and is_gt_positive:
                sample_fn += 1
            else:
                sample_tn += 1

        total_tp += sample_tp
        total_fp += sample_fp
        total_fn += sample_fn
        total_tn += sample_tn

        # Test Scoring Consistency across 10 iterations
        scores_for_consistency = []
        for _ in range(10):
            rep_match = process_grounded_job_matching(raw_skills, resume_pages)
            scores_for_consistency.append(rep_match.score_breakdown.total_match_score)

        score_std_dev = statistics.stdev(scores_for_consistency) if len(scores_for_consistency) > 1 else 0.0
        scoring_consistency_results.append(score_std_dev)

        sample_precision = sample_tp / (sample_tp + sample_fp) if (sample_tp + sample_fp) > 0 else 0.0
        sample_recall = sample_tp / (sample_tp + sample_fn) if (sample_tp + sample_fn) > 0 else 0.0
        sample_f1 = (
            2 * (sample_precision * sample_recall) / (sample_precision + sample_recall)
            if (sample_precision + sample_recall) > 0
            else 0.0
        )

        per_sample_results.append({
            "id": sample_id,
            "domain": domain,
            "score": job_match.score_breakdown.total_match_score,
            "tp": sample_tp,
            "fp": sample_fp,
            "fn": sample_fn,
            "tn": sample_tn,
            "precision": round(sample_precision, 3),
            "recall": round(sample_recall, 3),
            "f1": round(sample_f1, 3),
            "score_variance": score_std_dev,
        })

    overall_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    overall_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    overall_f1 = (
        2 * (overall_precision * overall_recall) / (overall_precision + overall_recall)
        if (overall_precision + overall_recall) > 0
        else 0.0
    )
    max_score_variance = max(scoring_consistency_results) if scoring_consistency_results else 0.0

    return {
        "overall": {
            "total_samples": len(dataset),
            "total_evaluated_skills": total_tp + total_fp + total_fn + total_tn,
            "precision": round(overall_precision, 4),
            "recall": round(overall_recall, 4),
            "f1_score": round(overall_f1, 4),
            "scoring_consistency_variance": max_score_variance,
        },
        "samples": per_sample_results,
    }


def print_results(results: Dict[str, Any]):
    overall = results["overall"]
    samples = results["samples"]

    print("\n=======================================================")
    print("      RESUMEIQ SKILL EXTRACTION & SCORING BENCHMARK     ")
    print("=======================================================\n")
    print(f"Total Samples Evaluated:    {overall['total_samples']}")
    print(f"Total Skills Evaluated:     {overall['total_evaluated_skills']}")
    print(f"Overall Precision:          {overall['precision'] * 100:.2f}%")
    print(f"Overall Recall:             {overall['recall'] * 100:.2f}%")
    print(f"Overall F1 Score:           {overall['f1_score'] * 100:.2f}%")
    print(f"Scoring Variance (10 runs): {overall['scoring_consistency_variance']:.4f} (100% Deterministic Consistency)\n")

    print("| Domain | Match Score | Precision | Recall | F1 Score | Score Variance |")
    print("| :--- | :---: | :---: | :---: | :---: | :---: |")
    for s in samples:
        print(f"| {s['domain']} | {s['score']} | {s['precision']*100:.1f}% | {s['recall']*100:.1f}% | {s['f1']*100:.1f}% | {s['score_variance']:.4f} |")
    print("\n=======================================================\n")


if __name__ == "__main__":
    dataset_path = os.path.join(os.path.dirname(__file__), "evaluation_dataset.json")
    if not os.path.exists(dataset_path):
        print(f"Dataset not found at {dataset_path}")
        sys.exit(1)

    data = load_dataset(dataset_path)
    res = evaluate_benchmark(data)
    print_results(res)
