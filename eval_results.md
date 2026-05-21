# Vigilant Mechanic Eval Results

## Headline Metrics

| Metric | Value |
| --- | ---: |
| Cases evaluated | 20 |
| Overall urgency accuracy | 95.0% |
| Urgency accuracy within +/- 1 | 100.0% |
| Safety-critical false negative rate | 0.0% |
| Safety-critical false negatives | 0 |
| Human-review precision | 100.0% |
| Human-review recall | 92.9% |

## Per-Category Breakdown

| Category | Count | Urgency Accuracy | Review Accuracy | Job Category Hit Rate |
| --- | ---: | ---: | ---: | ---: |
| ambiguous | 5 | 80.0% | 100.0% | 100.0% |
| routine | 6 | 100.0% | 100.0% | 100.0% |
| safety_critical | 6 | 100.0% | 100.0% | 100.0% |
| upsell_opportunity | 3 | 100.0% | 66.7% | 100.0% |

## Case Details

| Case | Category | Expected U | Predicted U | Expected Review | Predicted Review | Urgency Match | Review Match | Safety FN | Job Codes |
| --- | --- | ---: | ---: | --- | --- | --- | --- | --- | --- |
| EC-001 | safety_critical | 4 | 4 | True | True | True | True | False | BRK-004, BRK-001, BRK-002, BRK-003 |
| EC-002 | safety_critical | 4 | 4 | True | True | True | True | False | DIA-003 |
| EC-003 | safety_critical | 4 | 4 | True | True | True | True | False | DIA-001 |
| EC-004 | safety_critical | 4 | 4 | True | True | True | True | False | TRN-002, TRN-001 |
| EC-005 | safety_critical | 4 | 4 | True | True | True | True | False | DIA-002, ELE-001, ELE-002 |
| EC-006 | safety_critical | 4 | 4 | True | True | True | True | False | DIA-001 |
| EC-007 | routine | 1 | 1 | False | False | True | True | False | OIL-001, TIR-002 |
| EC-008 | routine | 1 | 1 | False | False | True | True | False | TIR-002 |
| EC-009 | routine | 1 | 1 | False | False | True | True | False | FLT-001 |
| EC-010 | routine | 1 | 1 | False | False | True | True | False | OIL-001, TIR-002, FLT-001, FLT-002 |
| EC-011 | routine | 1 | 1 | False | False | True | True | False | OIL-001, TIR-002, FLT-002 |
| EC-012 | routine | 1 | 1 | False | False | True | True | False | FLT-002 |
| EC-013 | ambiguous | 3 | 3 | True | True | True | True | False | BRK-004 |
| EC-014 | ambiguous | 3 | 3 | True | True | True | True | False | DIA-001 |
| EC-015 | ambiguous | 3 | 3 | True | True | True | True | False | DIA-003, BRK-003, TIR-002, TIR-003 |
| EC-016 | ambiguous | 2 | 3 | True | True | False | True | False | HVAC-001, DIA-002 |
| EC-017 | ambiguous | 3 | 3 | True | True | True | True | False | DIA-001 |
| EC-018 | upsell_opportunity | 1 | 1 | True | True | True | True | False | OIL-001, BRK-001, BRK-004, TIR-002, FLT-001, FLT-002 |
| EC-019 | upsell_opportunity | 1 | 1 | True | False | True | False | False | OIL-001, TIR-002, FLT-001, FLT-002, ENG-002, BRK-004 |
| EC-020 | upsell_opportunity | 1 | 1 | True | True | True | True | False | OIL-001, TIR-002, TIR-003, BRK-004, FLT-001, FLT-002, ENG-002 |
