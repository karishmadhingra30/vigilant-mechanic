import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from db_lookup import list_all_service_codes
from service_advisor import analyze_request


BASE_DIR = Path(__file__).resolve().parent
EVAL_CASES_PATH = BASE_DIR / "eval_cases.json"
RESULTS_PATH = BASE_DIR / "eval_results.md"


def _load_cases(limit: int | None) -> list[dict]:
    cases = json.loads(EVAL_CASES_PATH.read_text(encoding="utf-8"))
    return cases[:limit] if limit else cases


def _category_for_code(code: str, service_codes: dict) -> str | None:
    details = service_codes.get(code)
    return details["category"] if details else None


def _score_case(case: dict, result: dict, service_codes: dict) -> dict:
    expected_review = case["expected_human_review"]
    predicted_review = bool(result.get("human_review_needed"))
    expected_urgency = int(case["expected_urgency"])
    predicted_urgency = int(result.get("urgency", 0))
    predicted_categories = {
        category
        for code in result.get("recommended_job_codes", [])
        if (category := _category_for_code(code, service_codes))
    }
    expected_categories = set(case["expected_job_code_categories"])

    return {
        "case_id": case["case_id"],
        "category": case["category"],
        "expected_urgency": expected_urgency,
        "predicted_urgency": predicted_urgency,
        "urgency_exact": predicted_urgency == expected_urgency,
        "urgency_within_one": abs(predicted_urgency - expected_urgency) <= 1,
        "expected_review": expected_review,
        "predicted_review": predicted_review,
        "review_match": predicted_review == expected_review,
        "safety_false_negative": expected_urgency == 4
        and (predicted_urgency < 4 or not predicted_review),
        "category_match": bool(expected_categories & predicted_categories),
        "job_codes": result.get("recommended_job_codes", []),
        "urgency_reasoning": result.get("urgency_reasoning", ""),
        "human_review_reason": result.get("human_review_reason"),
    }


def _percent(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "n/a"
    return f"{(numerator / denominator) * 100:.1f}%"


def _metrics(scored: list[dict]) -> dict:
    total = len(scored)
    exact = sum(item["urgency_exact"] for item in scored)
    within_one = sum(item["urgency_within_one"] for item in scored)
    safety_cases = [item for item in scored if item["expected_urgency"] == 4]
    safety_fn = sum(item["safety_false_negative"] for item in safety_cases)

    true_positive = sum(
        item["expected_review"] and item["predicted_review"] for item in scored
    )
    false_positive = sum(
        not item["expected_review"] and item["predicted_review"] for item in scored
    )
    false_negative = sum(
        item["expected_review"] and not item["predicted_review"] for item in scored
    )

    return {
        "total": total,
        "urgency_accuracy": _percent(exact, total),
        "urgency_within_one": _percent(within_one, total),
        "safety_false_negative_rate": _percent(safety_fn, len(safety_cases)),
        "safety_false_negatives": safety_fn,
        "human_review_precision": _percent(true_positive, true_positive + false_positive),
        "human_review_recall": _percent(true_positive, true_positive + false_negative),
    }


def _category_breakdown(scored: list[dict]) -> dict:
    groups: dict[str, list[dict]] = defaultdict(list)
    for item in scored:
        groups[item["category"]].append(item)

    return {
        category: {
            "count": len(items),
            "urgency_accuracy": _percent(
                sum(item["urgency_exact"] for item in items), len(items)
            ),
            "review_accuracy": _percent(
                sum(item["review_match"] for item in items), len(items)
            ),
            "job_category_hit_rate": _percent(
                sum(item["category_match"] for item in items), len(items)
            ),
        }
        for category, items in sorted(groups.items())
    }


def _render_results(scored: list[dict], metrics: dict, breakdown: dict) -> str:
    lines = [
        "# Vigilant Mechanic Eval Results",
        "",
        "## Headline Metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Cases evaluated | {metrics['total']} |",
        f"| Overall urgency accuracy | {metrics['urgency_accuracy']} |",
        f"| Urgency accuracy within +/- 1 | {metrics['urgency_within_one']} |",
        f"| Safety-critical false negative rate | {metrics['safety_false_negative_rate']} |",
        f"| Safety-critical false negatives | {metrics['safety_false_negatives']} |",
        f"| Human-review precision | {metrics['human_review_precision']} |",
        f"| Human-review recall | {metrics['human_review_recall']} |",
        "",
        "## Per-Category Breakdown",
        "",
        "| Category | Count | Urgency Accuracy | Review Accuracy | Job Category Hit Rate |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]

    for category, row in breakdown.items():
        lines.append(
            f"| {category} | {row['count']} | {row['urgency_accuracy']} | "
            f"{row['review_accuracy']} | {row['job_category_hit_rate']} |"
        )

    lines.extend(
        [
            "",
            "## Case Details",
            "",
            "| Case | Category | Expected U | Predicted U | Expected Review | "
            "Predicted Review | Urgency Match | Review Match | Safety FN | Job Codes |",
            "| --- | --- | ---: | ---: | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for item in scored:
        lines.append(
            f"| {item['case_id']} | {item['category']} | {item['expected_urgency']} | "
            f"{item['predicted_urgency']} | {item['expected_review']} | "
            f"{item['predicted_review']} | {item['urgency_exact']} | "
            f"{item['review_match']} | {item['safety_false_negative']} | "
            f"{', '.join(item['job_codes'])} |"
        )

    return "\n".join(lines) + "\n"


def run_evals(limit: int | None = None) -> str:
    cases = _load_cases(limit)
    service_codes = list_all_service_codes()
    scored = []
    for case in cases:
        print(
            f"Running {case['case_id']} ({case['category']}) "
            f"expected U={case['expected_urgency']} review={case['expected_human_review']}",
            file=sys.stderr,
        )
        result = analyze_request(case["customer_message"], case["customer_phone"])
        scored_case = _score_case(case, result, service_codes)
        scored.append(scored_case)
        status = "PASS" if scored_case["urgency_exact"] and scored_case["review_match"] else "MISS"
        print(
            f"  {status}: predicted U={scored_case['predicted_urgency']} "
            f"review={scored_case['predicted_review']} "
            f"urgency_match={scored_case['urgency_exact']} "
            f"review_match={scored_case['review_match']} "
            f"safety_fn={scored_case['safety_false_negative']} "
            f"codes={', '.join(scored_case['job_codes']) or 'none'}",
            file=sys.stderr,
        )

    metrics = _metrics(scored)
    breakdown = _category_breakdown(scored)
    report = _render_results(scored, metrics, breakdown)
    RESULTS_PATH.write_text(report, encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Vigilant Mechanic evals.")
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N cases.")
    args = parser.parse_args()
    print(run_evals(args.limit))


if __name__ == "__main__":
    main()
