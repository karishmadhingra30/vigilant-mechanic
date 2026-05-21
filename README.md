# Vigilant Mechanic

Vigilant Mechanic is a compact AI service-advisor agent for dealership service workflows. Given a customer message and phone number, it looks up mock customer and vehicle history, classifies urgency on a 1-4 scale, recommends dealership service job codes with estimated cost and labor time, and decides whether a human advisor should review the response before it reaches the customer. The key differentiator is the eval harness: it runs 20 hand-labeled cases and reports safety-critical false negatives, urgency accuracy, and human-review decision quality.

## Architecture

```text
Customer message + phone
          |
          v
  db_lookup.py
  - customer lookup
  - vehicle lookup
  - recent service history
          |
          v
  service_advisor.py
  - Claude prompt
  - service code catalog
  - JSON response schema
          |
          v
  deterministic guardrails
  - urgency 4 => human review
  - unknown job code => human review
  - large non-routine bundles => human review
          |
          v
Structured advisor output
```

## How to Run

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Add your Anthropic API key:

```bash
cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY
```

Run a single hardcoded example:

```bash
python service_advisor.py
```

Run a quick eval subset:

```bash
python run_evals.py --limit 2
```

Run the full eval suite:

```bash
python run_evals.py
```

The eval runner prints per-case progress to stderr, prints the final Markdown report to stdout, and writes the same report to `eval_results.md`.

## Sample Eval Results

Latest full run:

```text
Cases evaluated: 20
Overall urgency accuracy: 95.0%
Urgency accuracy within +/- 1: 100.0%
Safety-critical false negative rate: 0.0%
Safety-critical false negatives: 0
Human-review precision: 100.0%
Human-review recall: 92.9%
```

The headline metric is the safety-critical false negative rate. In this run, all six safety-critical cases were classified as urgency 4 and routed to human review.

## Learnings

This project intentionally treats eval failures as product feedback, not just test failures. A few useful issues surfaced during development:

- The first full eval run had strong safety behavior but low human-review precision. The agent escalated routine and upsell cases too often because the prompt said any recommendation bundle over three job codes needed review. I changed the review policy so routine maintenance and upsell recommendations do not require human review unless safety symptoms are present, and added a deterministic guardrail that only forces review for large bundles when urgency is 2 or higher. Result: routine review accuracy improved to 100%, while safety-critical false negative rate stayed at 0.0%.
- The initial full eval run looked frozen because 20 live model calls ran sequentially with no per-case visibility. I added per-case stderr logging with case id, expected labels, predicted urgency, predicted review decision, pass/miss status, and job codes. Result: evals are now much easier to debug, and the final stdout report stays clean enough to commit.
- A live API call hung longer than expected during evaluation. I added a 30-second timeout to the Claude request. Result: the harness is less likely to stall indefinitely during demos or interview walkthroughs.
- The eval labels themselves needed iteration. After changing the review policy, the upsell cases became ambiguous: should broad maintenance bundles be reviewed or treated as routine? I updated the upsell expected labels to reflect that these cases invite broader bundled recommendations. Result: the eval now captures a real product tradeoff between advisor workload and recommendation quality.
- The model classified one HVAC case as urgency 3 when the label expected urgency 2. I left that as a visible miss because it is within +/- 1 and shows why the harness tracks both exact accuracy and a more forgiving urgency metric.

## Project Files

- `service_advisor.py`: agent prompt, Claude call, JSON parsing, and guardrails
- `db_lookup.py`: read-only helpers for mock customer, vehicle, and service-code data
- `mock_db.json`: fake customers, vehicles, and service history
- `service_codes.json`: dealership job-code catalog with estimates
- `eval_cases.json`: 20 labeled eval cases
- `run_evals.py`: eval harness and Markdown report writer
- `eval_results.md`: latest eval output

## Limitations

- Small eval set: 20 hand-labeled cases is enough to demonstrate the harness, not enough to prove production performance.
- Single-turn only: the agent does not ask follow-up questions before making a recommendation.
- Mock data only: customer, vehicle, and service history records are synthetic and much simpler than real dealership data.
- No real-time scheduling: the agent recommends service work but cannot check bay availability or create appointments.
- Multi-vehicle households are not handled gracefully: the context supports multiple vehicles, but the prompt does not reliably disambiguate which vehicle the customer means.
- Job-code coverage is intentionally narrow, so some real symptoms map to diagnostics rather than precise repairs.

## What I Would Build Next

- Multi-turn conversation for clarifying vehicle, symptoms, timing, and drivability
- Real appointment scheduling tool with shop capacity and transportation options
- Golden-set expansion to 200+ cases with edge cases from advisor transcripts
- A/B prompt evaluation to compare safety recall, review workload, and customer-summary quality
- Separate eval slices for safety, revenue/upsell quality, customer experience, and advisor workload
