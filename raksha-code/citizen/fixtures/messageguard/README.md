# MessageGuard v1 fixture corpus — one hand-authored corpus

Hand-authored, labelled, deterministic fixtures for the single canonical
Citizen MessageGuard scorer. They are **not** a dump of real device traffic and
they contain no personal data. The corpus exists to measure catalogue coverage
and the cost of false positives on messages written to look like genuine Indian
bank, telecom, utility and marketing alerts. Every published number from this
corpus is **hand-authored / in-distribution**; real-world recall and FPR remain
UNMEASURED.

| Label | English | Hindi | Telugu | Hinglish | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Scam | 120 | 132 | 120 | 30 | **402** |
| Genuine / benign | 40 | 40 | 40 | 16 | **136** |
| Total | 160 | 172 | 160 | 46 | **538** |

Each JSONL line has:

- `id`: stable fixture identifier;
- `lang`: `en`, `hi`, `te` or `hinglish`;
- `label`: `scam` or `benign`;
- `kind` / `category`: a short traffic class used in the false-positive review;
- `families`: the signal families the scam fixture was authored to trigger;
- `text`: the message, in the requested script;
- `source` on the 46 Phase 5 Hinglish rows: provenance of the unique port.

The older Hindi scam set includes 12 Hinglish-Latin messages. Phase 5 added 46
unique Hinglish rows ported from the now-archived alternative Part 3 corpus;
all 46 normalized texts differ from the earlier historical 492-fixture corpus,
which is superseded by the 538-fixture canonical corpus; all are hand-authored. The eval runner scores those rows with the explicit
`analyze(..., lang="hinglish")` interface so the dedicated Latin-Hindi token
set is measured without changing the published en/hi/te `auto` results.
Transliteration coverage remains partial and is called out in the evaluation.
Three deliberately benign-looking scam fixtures (one per en/hi/te) contain no
catalogue vocabulary: they are kept so the novel-script failure mode remains
visible in the measured recall, not hidden by a perfect-looking number.

Published numbers are generated from these fixtures by
`evals/messageguard/run_evals.py` into `raksha/MESSAGEGUARD_EVALS.md`. Do not
edit that document by hand. The independent alternative corpus and runner are
archived under `archive/provenance/` and are not runtime imports.
