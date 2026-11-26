# MessageGuard v1 fixture corpus

Hand-authored, labelled, deterministic fixtures for the integrated Citizen
MessageGuard scorer. They are **not** a dump of real device traffic and they
contain no personal data. The corpus exists to measure catalogue coverage and
the cost of false positives on messages written to look like genuine Indian
bank, telecom, utility and marketing alerts.

| Label | English | Hindi | Telugu | Total |
| --- | ---: | ---: | ---: | ---: |
| Scam | 120 | 132 | 120 | **372** |
| Genuine / benign | 40 | 40 | 40 | **120** |
| Total | 160 | 172 | 160 | **492** |

Each JSONL line has:

- `id`: stable fixture identifier;
- `lang`: `en`, `hi` or `te`;
- `label`: `scam` or `benign`;
- `kind`: a short traffic class used in the false-positive review;
- `families`: the signal families the scam fixture was authored to trigger;
- `text`: the message, in the requested script.

The Hindi scam set includes 12 Hinglish-Latin messages; transliteration
coverage is still partial and is called out in the evaluation. Three
deliberately benign-looking scam fixtures (one per language) contain no
catalogue vocabulary: they are kept so the novel-script failure mode remains
visible in the measured recall, not hidden by a perfect-looking number.

Published numbers are generated from these fixtures by
`evals/messageguard/run_evals.py` into `raksha/MESSAGEGUARD_EVALS.md`. Do not
edit that document by hand.
