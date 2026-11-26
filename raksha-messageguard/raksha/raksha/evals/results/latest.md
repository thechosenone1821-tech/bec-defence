# MessageGuard evaluation results (generated)

Corpus: 431 fixtures — scam 324, benign 107 (genuine bank alerts: 85).

| scam lang | n | det@MODERATE | det@HIGH |
|---|---|---|---|
| en | 102 | 100.0% | 100.0% |
| hi | 94 | 100.0% | 100.0% |
| te | 94 | 100.0% | 100.0% |
| hinglish | 29 | 100.0% | 100.0% |
| **all (excl gap)** | 319 | **100.0%** | **100.0%** |
| known-gap only | 5 | 20.0% | 20.0% |

## False positives on genuine messages

| set | n | FP@MODERATE | FP@HIGH |
|---|---|---|---|
| all benign | 107 | 1.9% | 0.0% |
| genuine bank alerts | 85 | 2.4% | 0.0% |

### False positives by language (bank-alert subset FP@HIGH)

| lang | benign n | FP@MODERATE | FP@HIGH | bank n | bank FP@HIGH |
|---|---|---|---|---|---|
| en | 43 | 0.0% | 0.0% | 32 | 0.0% |
| hi | 24 | 4.2% | 0.0% | 20 | 0.0% |
| te | 24 | 4.2% | 0.0% | 20 | 0.0% |
| hinglish | 16 | 0.0% | 0.0% | 13 | 0.0% |

### False-positive review listing (all benign fixtures >= MODERATE)

| id | lang | category | band | score | fired |
|---|---|---|---|---|---|
| benign_hi_015 | hi | loan_emi | MODERATE | 0.20 | urgency: आज रात |
| benign_te_015 | te | loan_emi | MODERATE | 0.20 | urgency: ఈ రాత్రి |

Determinism verified: True (verdict hash `596e3cd861588e99`).

## Gates

- [x] scam_fixtures_ge_300
- [x] per_language_coverage
- [x] benign_bank_alerts_ge_60
- [x] detection_high_excl_gap_ge_0.90
- [x] fp_high_bank_alerts_le_0.10

## Scam fixtures scoring below MODERATE (honest misses)

- scam_en_103 (en, obfuscation_gap, score 0.00)
- scam_hi_095 (hi, obfuscation_gap, score 0.00)
- scam_hinglish_030 (hinglish, obfuscation_gap, score 0.00)
- scam_te_095 (te, obfuscation_gap, score 0.00)
