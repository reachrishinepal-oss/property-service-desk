"""
PURPOSE: Turn your triage answer key into fine-tuning training data and check it the way Microsoft says to, to see what a training file needs. No Azure calls, no cost.
LAYER:   Evaluation/Reliability
SESSION: S04
Concept:   fine-tuning data: JSONL chat examples, one consistent system message, hundreds of examples, and never your own test set.
Watch for: the shape of one training example, the three checks failing on the bad file, and why your 20 rows cannot be the training data.
Run:       python scripts/try_finetune_data.py
"""
import json

from lab_helpers import REPO_ROOT, title

# Try changing:
SYSTEM = "You triage resident messages for Contoso Living, a property manager in Dubai. Reply with Category and Urgency."
MIN_EXAMPLES = 100   # Microsoft says "at least hundreds"; this is a floor for the check, not a promise of quality

rows = [json.loads(line) for line in (REPO_ROOT / "data/eval/triage_eval_v1.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]


def to_example(row, system=SYSTEM):
    # AI-103 1.4.c: one training example is one conversation: system, user, assistant. The assistant turn is the answer you want.
    return {"messages": [
        {"role": "system", "content": system},
        {"role": "user", "content": row["text"]},
        {"role": "assistant", "content": f"Category: {row['expected_category']}\nUrgency: {row['expected_urgency']}"},
    ]}


def check(examples, test_texts):
    problems = []
    systems = {ex["messages"][0]["content"] for ex in examples}
    if "" in systems:
        problems.append("an example has an EMPTY system message (Microsoft: blank tends to give lower-accuracy models)")
    if len(systems) > 1:
        problems.append(f"{len(systems)} different system messages (use the same one in every example, and again when you call the model)")
    if len(examples) < MIN_EXAMPLES:
        problems.append(f"only {len(examples)} examples (Microsoft: at least hundreds)")
    leaked = [ex for ex in examples if ex["messages"][1]["content"] in test_texts]
    if leaked:
        problems.append(f"{len(leaked)} examples ARE your test rows: scoring the tuned model on them would prove nothing")
    bad_last = [ex for ex in examples if ex["messages"][-1]["role"] != "assistant"]
    if bad_last:
        problems.append(f"{len(bad_last)} examples do not end with an assistant message")
    return problems


title("One training example (a line of the .jsonl file)")
print(json.dumps(to_example(rows[0]), ensure_ascii=False, indent=2))

title("Check 1: the file built straight from your 20 answer-key rows")
good = [to_example(r) for r in rows]
test_texts = {r["text"] for r in rows}
for problem in check(good, test_texts) or ["no problems"]:
    print(f"   - {problem}")

title("Check 2: the same file with two deliberate mistakes")
bad = [to_example(r) for r in rows]
bad[2] = to_example(rows[2], system="")
bad[4] = to_example(rows[4], system="Answer briefly.")
for problem in check(bad, test_texts):
    print(f"   - {problem}")

title("What this means for your product")
tokens = sum(len(json.dumps(ex, ensure_ascii=False)) for ex in good) // 4
print(f"   Rough size of the 20-row file: about {tokens} tokens. Training cost grows with tokens x epochs.")
print("   Your 20 rows stay the TEST set. A tuned model would need its own hundreds of examples, written fresh.")
print("   Microsoft: evaluate the standard model's baseline first. You already have it: 15 of 20 on ai103model1.")
