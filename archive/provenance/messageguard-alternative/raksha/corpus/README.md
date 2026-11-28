# MessageGuard fixture corpus

Hand-authored fixtures for the deterministic scam-script detector (Part 3).
This corpus supersedes the original 20-fixture set: the detection Definition
of Done requires >= 300 messages with per-language coverage, plus a benign
set so the false-positive rate can be measured on GENUINE messages.

## Files

| File | Contents |
|---|---|
| `scam_en.jsonl` | scam scripts, English (~104) |
| `scam_hi.jsonl` | scam scripts, Hindi / Devanagari (~95) |
| `scam_te.jsonl` | scam scripts, Telugu (~95) |
| `scam_hinglish.jsonl` | scam scripts, Hindi in Latin script (~30) |
| `benign_en.jsonl` | genuine messages, English (~43) |
| `benign_hi.jsonl` | genuine messages, Hindi (~24) |
| `benign_te.jsonl` | genuine messages, Telugu (~24) |
| `benign_hinglish.jsonl` | genuine messages, Hinglish (~16) |

## Schema (one JSON object per line)

```json
{"id": "scam_en_001", "label": "scam", "lang": "en", "category": "otp_request", "text": "..."}
```

- `id`      unique across the whole corpus (`scam_<lang>_NNN` / `benign_<lang>_NNN`)
- `label`   `scam` or `benign`
- `lang`    `en` | `hi` | `te` | `hinglish` (the display language for
  `hinglish` is Hindi; the matcher treats Latin script as en+hinglish)
- `category` scam script family or genuine-message kind (see below)
- `text`    the message body exactly as a person would have received it

## Scam categories

`otp_request`, `upi_collect`, `digital_arrest`, `police_cbi_ed`,
`rbi_freeze`, `electricity_cutoff`, `kyc_expiry`, `lottery_prize`,
`loan_fee`, `refund_fee`, `sim_suspend`, `parcel_customs`, `job_task`,
`card_block_phish`, `bail_emergency`, `insurance_lapse`, `tax_refund`,
`obfuscation_gap`.

`obfuscation_gap` fixtures are DELIBERATE misses (spaced-out text, homoglyph
links). They exist so EVALS.md can report the documented failure mode of
exact-token matching honestly, separately from the headline accuracy.

## Benign categories

`bank_txn`, `otp_notice`, `kyc_official`, `loan_emi`, `salary`,
`bill_receipt`, `bank_fraud_alert` are GENUINE BANK ALERTS — the exact set on
which the false-positive rate must be measured (spec, definition of done).
`marketing`, `govt_service`, `delivery` are other genuine everyday messages
included to stress urgency/link false positives.

## Authoring rules

1. Every message is hand-authored for testing. No scraped or forwarded real
   victim messages; adding a real-world corpus requires the consent-clearing
   step from the spec's model-training table (section 3).
2. All phone numbers are masked (`90000 12345`, `98999`) or fake
   (`1800 000 111`). All UPI handles are fictional. All shortener links point
   nowhere meaningful; they are inert patterns.
3. Every scam fixture (except `obfuscation_gap`) must be detectable under the
   spec's scoring model: either the credential or authority family fires, or
   at least two families fire.
4. The benign set deliberately includes hard cases: genuine "never share your
   OTP" warnings, genuine KYC notices with official links, genuine bank fraud
   alerts, marketing urgency, and utility reminders. These are where the
   false-positive rate is measured.
