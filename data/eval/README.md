# Triage evaluation set

`triage_eval_v1.jsonl` holds 20 resident requests with the category and urgency a good triage desk should assign. It is the baseline set for measuring triage quality from S01 onwards.

**All data is synthetic.** Buildings (Contoso Heights, Contoso Marina Residence, Contoso Gardens), apartment numbers and messages are invented. There are no real names, phone numbers or personal data.

## Schema

One JSON object per line, UTF-8, Arabic stored as literal characters (not `\u` escapes).

| Field | Type | Meaning |
|---|---|---|
| `id` | string | `T01` to `T20`, unique |
| `text` | string | The resident's message as they would type it |
| `language` | string | `en`, `ar` or `mixed` (Arabic and English in one message) |
| `expected_category` | string | One of the categories below |
| `expected_urgency` | string | One of the urgency levels below |
| `hard` | bool | `true` when the right label is genuinely ambiguous |
| `note` | string | One line explaining why this label is correct |

## Labels

**Categories**

| Value | Covers |
|---|---|
| `plumbing` | Leaks, blockages, taps, toilets, water heaters |
| `electrical` | Power loss, breakers, sockets, lights, wiring |
| `hvac` | Air conditioning, ventilation, filters |
| `appliance` | Landlord-supplied fridge, washer, oven, dishwasher |
| `pest` | Insects, rodents, pest control visits |
| `noise` | Complaints about sound from neighbours or the building |
| `access_security` | Access cards, gates, doors, locks, building security |
| `common_area` | Lifts, gym, pool, lobby, car park and other shared spaces |
| `lease_billing` | Rent, charges, deposits, renewals, contract questions |

**Urgency**

| Value | Definition |
|---|---|
| `emergency` | Risk to life or property now |
| `urgent` | Fix within 24 hours |
| `routine` | Fix within the normal SLA window |

## Mix (v1)

- Categories: plumbing 3, electrical 3, hvac 3, appliance 2, pest 1, noise 2, access_security 2, common_area 2, lease_billing 2
- Urgency: emergency 4, urgent 7, routine 9
- Language: 14 en, 5 ar, 1 mixed
- Hard rows: 3 (T08, T14, T19)

## Validate

From the `capstone` folder:

```bash
python scripts/validate_eval_set.py
```

It checks fields and types, allowed values, unique ids and exactly 20 rows, then prints counts per category, urgency, language and hard flag. Exit code 0 means valid; 1 means at least one error, listed at the end of the output. Pass a path to check another file: `python scripts/validate_eval_set.py data/eval/other.jsonl`.
