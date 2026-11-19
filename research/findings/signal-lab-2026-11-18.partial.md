# Signal lab — 2026-11-18

Creative lead hypotheses tested against Chicago history. Reproduce with `uv run python research/signal_lab/lab.py`. Verdicts: **Strong** = lift ≥ 3 with ≥ 5 signals/week; **Useful** = lift ≥ 1.8; **Weak** = lift ≥ 1.25; otherwise **No signal**. Permits capture permitted work only, so conversion rates are floors.

## Leaderboard

| # | Hypothesis | Verdict | Lift | Conversion | Baseline | Signals/week | Who it's for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| H42 | Building Code Scofflaw List → permitted work | **No signal** | 0.92× | 24.3% | 26.4% | 0.70 | Porch, masonry and general repair contractors (a priority flag on violation and investor leads) |

## H42 — Building Code Scofflaw List → permitted work

- **Signal:** Address placed on the City's Building Code Scofflaw List (building list date)
- **Target:** Any permit at the address within 365 days; control = addresses cited in the same month, never listed
- **Data:** Building Code Scofflaw List (current list only), building violations, permits
- **Verdict:** No signal
- **Notes:** The open data holds only the CURRENT list. Buildings removed after fixing their violations (often with a permit) are missing, so conversion is biased downward; treat the lift as a floor and the sample as small. Do not rank leads on it unless the lift is clearly above 1.

| trade | conversion | control | lift |
| --- | --- | --- | --- |
| porch | 5.7% | 0.05 | 1.21 |
| masonry | 3.9% | 0.06 | 0.63 |
| roofing | 0.3% | 0.02 | 0.12 |

- Key numbers (rates are fractions): signals = 387; conversion = 0.24; baseline = 0.26; lift = 0.92; own_year_before = 0.30; controls = 9493; control_year_before = 0.22; signals_per_week = 0.67
