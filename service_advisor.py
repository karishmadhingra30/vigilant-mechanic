import json
import os
from pathlib import Path
from typing import Any

from anthropic import Anthropic
from dotenv import load_dotenv

from db_lookup import (
    get_customer_by_phone,
    get_service_history,
    get_vehicles_for_customer,
    list_all_service_codes,
)


MODEL_NAME = "claude-sonnet-4-6"
BASE_DIR = Path(__file__).resolve().parent

SYSTEM_PROMPT = SERVICE_ADVISOR_SYSTEM_PROMPT = """You are Vigilant Mechanic, an AI service advisor for an automotive dealership. You analyze customer-reported vehicle issues and recommend service work, but you are NOT the final decision maker on safety-critical issues. A human service advisor reviews your recommendations before they reach the customer.

## Your task

Given a customer message and their vehicle's recent service history, you will:
1. Classify the urgency of the reported issue on a 1-4 scale
2. Recommend job codes ONLY from the provided service catalog
3. Estimate cost range and labor hours by summing the catalog values for your recommended codes
4. Decide whether a human advisor must review before this response reaches the customer
5. Write a brief plain-language summary the customer would understand

## Urgency scale

1 - Routine maintenance, no time pressure. Examples: oil change due, tire rotation, scheduled inspection, cabin filter replacement.

2 - Should address within 2 weeks. Examples: worn but functional brake pads, minor fluid seep (not drip), tire tread approaching minimum, battery testing weak but starting.

3 - Address this week. Examples: brake performance noticeably degraded, check engine light on but car driveable, active fluid leak, intermittent electrical issues affecting safety systems.

4 - Safety-critical, customer should not drive the vehicle. Examples: brake failure or metal-on-metal grinding, loss of steering response or pulling, smoke from engine or brakes, airbag warning light, transmission slipping under load, overheating, fuel smell.

## Safety-first escalation rules

Set human_review_needed to true if ANY of these apply:
- Urgency is 4
- The customer describes symptoms that COULD be safety-critical but you are not confident (ambiguous descriptions like "weird noise", "feels off", "something's wrong")
- The reported symptom does not clearly match any service code in the catalog
- The customer's vehicle history shows the same issue was serviced recently (possible warranty or repeat-failure situation)
- You are recommending more than 3 job codes (large bundles need human review for accuracy)

When in doubt about safety, escalate. A false positive (flagging something safe for review) costs a few minutes of advisor time. A false negative (missing a real safety issue) costs the customer's safety and the dealership's liability. Optimize for the former.

## Customer-facing language

The customer_summary field is the only field the customer might see. Rules for it:
- Plain language, no job codes, no internal jargon
- Do not give a final diagnosis. Say what you suspect and that a technician will confirm.
- Never tell a customer to ignore a symptom. If urgency is 1, still say it's worth checking.
- Two sentences maximum.

## Output guidelines

Return ONLY valid JSON matching this exact schema. No prose before or after the JSON.

{
  "urgency": <int 1-4>,
  "urgency_reasoning": "<one sentence on why this urgency level>",
  "recommended_job_codes": [<list of code strings from the catalog>],
  "estimated_cost_range_usd": [<min int>, <max int>],
  "estimated_hours": <float>,
  "human_review_needed": <bool>,
  "human_review_reason": <string or null>,
  "customer_summary": "<1-2 sentences for the customer>"
}

## Constraints

- Use ONLY job codes that appear in the provided service catalog. Do not invent codes.
- If you cannot identify any matching codes, return an empty list for recommended_job_codes, set human_review_needed to true, and explain in human_review_reason.
- estimated_cost_range_usd and estimated_hours must be computed by summing the catalog values for the codes you recommend. If the list is empty, return [0, 0] and 0.0.
- Never include personally identifiable information in any field. Refer to "the customer" and "the vehicle".
"""

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "urgency": {"type": "integer", "description": "Integer from 1 to 4."},
        "urgency_reasoning": {"type": "string"},
        "recommended_job_codes": {"type": "array", "items": {"type": "string"}},
        "estimated_cost_range_usd": {
            "type": "array",
            "items": {"type": "integer"},
            "description": "Two integers: [minimum total estimate, maximum total estimate].",
        },
        "estimated_hours": {"type": "number"},
        "human_review_needed": {"type": "boolean"},
        "human_review_reason": {
            "type": ["string", "null"],
            "description": "Required explanation when human_review_needed is true.",
        },
        "customer_summary": {
            "type": "string",
            "description": "1-2 plain-language sentences for the customer.",
        },
    },
    "required": [
        "urgency",
        "urgency_reasoning",
        "recommended_job_codes",
        "estimated_cost_range_usd",
        "estimated_hours",
        "human_review_needed",
        "human_review_reason",
        "customer_summary",
    ],
    "additionalProperties": False,
}


def _vehicle_context(customer: dict | None) -> list[dict]:
    if not customer:
        return []
    vehicles = get_vehicles_for_customer(customer["customer_id"])
    for vehicle in vehicles:
        vehicle["recent_service_history"] = get_service_history(vehicle["vehicle_id"])[:3]
    return vehicles


def _build_user_message(
    customer_message: str,
    customer_phone: str,
    customer: dict | None,
    vehicles: list[dict],
    service_codes: dict,
) -> str:
    payload = {
        "customer_phone": customer_phone,
        "customer": customer,
        "vehicles": vehicles,
        "customer_message": customer_message,
        "available_service_codes": service_codes,
    }
    return json.dumps(payload, indent=2)


def _extract_text(response: Any) -> str:
    for block in response.content:
        if getattr(block, "type", None) == "text":
            return block.text
    return ""


def _parse_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return {}
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return {}


def _normalize_result(result: dict, service_codes: dict) -> dict:
    codes = [
        str(code)
        for code in result.get("recommended_job_codes", [])
        if isinstance(code, str)
    ]
    cost_range = result.get("estimated_cost_range_usd", [0, 0])
    if not isinstance(cost_range, list) or len(cost_range) != 2:
        cost_range = _estimate_from_codes(codes, service_codes)[0]

    urgency = result.get("urgency", 3)
    try:
        urgency = max(1, min(4, int(urgency)))
    except (TypeError, ValueError):
        urgency = 3

    return {
        "urgency": urgency,
        "urgency_reasoning": str(result.get("urgency_reasoning") or "Model response was incomplete."),
        "recommended_job_codes": codes,
        "estimated_cost_range_usd": [int(cost_range[0]), int(cost_range[1])],
        "estimated_hours": float(result.get("estimated_hours") or 0.0),
        "human_review_needed": bool(result.get("human_review_needed", True)),
        "human_review_reason": result.get("human_review_reason"),
        "customer_summary": str(
            result.get("customer_summary")
            or "A service advisor should review this request before responding."
        ),
    }


def _estimate_from_codes(codes: list[str], service_codes: dict) -> tuple[list[int], float]:
    min_cost = 0
    max_cost = 0
    hours = 0.0
    for code in codes:
        details = service_codes.get(code)
        if not details:
            continue
        cost = details["estimated_cost_usd"]
        min_cost += int(cost[0])
        max_cost += int(cost[1])
        hours += float(details["estimated_hours"])
    return [min_cost, max_cost], round(hours, 1)


def _apply_guardrails(result: dict, service_codes: dict) -> dict:
    unknown_codes = [
        code for code in result["recommended_job_codes"] if code not in service_codes
    ]
    reasons = []

    if result["urgency"] == 4:
        result["human_review_needed"] = True
        reasons.append("Safety-critical urgency requires human advisor review.")

    if unknown_codes:
        result["human_review_needed"] = True
        reasons.append(f"Model recommended unknown service code(s): {', '.join(unknown_codes)}.")
        result["urgency_reasoning"] = (
            f"{result['urgency_reasoning']} Guardrail: unknown service code detected."
        )

    if result["human_review_needed"] and not result["human_review_reason"]:
        result["human_review_reason"] = " ".join(reasons) or "Human review requested by model."
    elif reasons:
        result["human_review_reason"] = " ".join([result["human_review_reason"], *reasons])

    estimated_cost, estimated_hours = _estimate_from_codes(
        result["recommended_job_codes"], service_codes
    )
    if estimated_cost != [0, 0]:
        result["estimated_cost_range_usd"] = estimated_cost
        result["estimated_hours"] = estimated_hours

    return result


def analyze_request(customer_message: str, customer_phone: str) -> dict:
    load_dotenv(BASE_DIR / ".env")
    customer = get_customer_by_phone(customer_phone)
    vehicles = _vehicle_context(customer)
    service_codes = list_all_service_codes()
    user_message = _build_user_message(
        customer_message, customer_phone, customer, vehicles, service_codes
    )

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=1000,
        temperature=0,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        output_config={"format": {"type": "json_schema", "schema": OUTPUT_SCHEMA}},
    )

    result = _normalize_result(_parse_json(_extract_text(response)), service_codes)
    return _apply_guardrails(result, service_codes)


if __name__ == "__main__":
    example = analyze_request(
        "When I brake, I hear grinding and the pedal feels soft.",
        "555-0142",
    )
    print(json.dumps(example, indent=2))
