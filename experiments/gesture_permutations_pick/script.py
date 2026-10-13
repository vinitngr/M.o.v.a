"""JEV sentence-builder benchmark (Python port of script.js).

Reads dataset.json + test.json (read-only, never modified),
builds the cartesian product of gesture meanings, and asks
the JEV model (typesafe/jev-1.13 via OpenRouter Decisions API)
to pick the most likely sentence.

Usage:
    python script.py --dry-run   # no API calls, just validate reachability
    python script.py              # MiniLM filter + Jev (needs OPENROUTER_API_KEY)
    python script.py --filter-only  # MiniLM alone picks top-1, no API key needed
    python script.py --no-filter    # Jev on full pools (baseline to beat)
    python script.py --top-k 12     # keep 12 options after MiniLM filter

Filter deps (torch NOT required — ONNX runtime):
    pip install onnxruntime transformers huggingface-hub
"""

import argparse
import itertools
import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

MODEL = "typesafe/jev-1.13"

parser = argparse.ArgumentParser(description="MiniLM pre-filter + Jev sentence benchmark")
parser.add_argument("--dry-run", action="store_true", help="validate only, no API calls")
parser.add_argument("--top-k", type=int, default=8, help="options kept after MiniLM filter")
parser.add_argument("--no-filter", action="store_true", help="skip MiniLM, Jev sees full pools")
parser.add_argument("--filter-only", action="store_true", help="MiniLM alone picks top-1, no API calls")
args = parser.parse_args()

DRY_RUN = args.dry_run
TOP_K = args.top_k
NO_FILTER = args.no_filter
FILTER_ONLY = args.filter_only

BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "dataset.json"
TEST_PATH = BASE_DIR / "test.json"
RESULTS_DIR = BASE_DIR / "benchmark-results"

API_URL = "https://openrouter.ai/api/alpha/decisions"

api_key = os.environ.get("OPENROUTER_API_KEY")
if not DRY_RUN and not FILTER_ONLY and not api_key:
    raise RuntimeError(
        "OPENROUTER_API_KEY environment variable is missing. "
        "(You said you will add it yourself — export it before running without --dry-run.)"
    )

with open(DATASET_PATH, encoding="utf-8") as f:
    gestures = json.load(f)["gestures"]
with open(TEST_PATH, encoding="utf-8") as f:
    tests = json.load(f)["tests"]

RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# CARTESIAN PRODUCT -> ALL POSSIBLE SENTENCES
# ============================================================
def build_sentences(gesture_names):
    slots = []
    for name in gesture_names:
        entry = gestures.get(name)
        if not entry or not isinstance(entry.get("meanings"), list):
            raise ValueError(
                f'Gesture "{name}" missing or has no meanings[] in dataset.json'
            )
        slots.append(entry["meanings"])
    return [" ".join(words) for words in itertools.product(*slots)]


# ============================================================
# MINILM PRE-FILTER (local, fast — drops obvious junk before Jev)
# ONNX cross-encoder, ~22M params. torch NOT required.
# ============================================================
FILTER_MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"
_filter = None


def _find_onnx(snap):
    """Find model_quantized.onnx (preferred) or model.onnx anywhere in snapshot
    (Xenova repos keep them under onnx/)."""
    found = []
    for root, _, files in os.walk(snap):
        for f in files:
            if f in ("model_quantized.onnx", "model.onnx"):
                found.append(os.path.join(root, f))
    found.sort(key=lambda p: (os.path.basename(p) != "model_quantized.onnx", len(p)))
    return found[0] if found else None


def load_filter():
    global _filter
    if _filter is not None:
        return _filter
    try:
        import onnxruntime as ort
        from huggingface_hub import snapshot_download
        from transformers import AutoTokenizer
    except ImportError as e:
        raise RuntimeError(
            "MiniLM filter needs: pip install onnxruntime transformers huggingface-hub "
            "(torch NOT required — runs on ONNX)"
        ) from e
    import numpy as _np

    snap = None
    for patterns in (["*.json", "*model_quantized.onnx"], ["*.json", "*model.onnx"], None):
        try:
            snap = snapshot_download(repo_id=FILTER_MODEL, allow_patterns=patterns)
            found = _find_onnx(snap)
            if found:
                break
            snap = None
        except Exception:
            snap = None
    if snap is None:
        raise RuntimeError(f"Could not download {FILTER_MODEL} from HF Hub")
    tok = AutoTokenizer.from_pretrained(snap)
    fpath = _find_onnx(snap)
    if not fpath:
        raise RuntimeError(f"No model.onnx found in {FILTER_MODEL} snapshot")
    sess = ort.InferenceSession(fpath, providers=["CPUExecutionProvider"])
    _filter = (tok, sess, _np)
    return _filter


def build_query(test):
    lines = [test.get("scene", "")]
    for turn in test.get("history", []):
        lines.append(f"{turn.get('speaker', '?')}: {turn.get('text', '')}")
    lines.append("gestures: " + " + ".join(test["gestures"]))
    return " ".join(line for line in lines if line)


def minilm_topk(test, sentences, top_k):
    """Score (context, candidate) pairs, keep top-k.

    Returns (kept_in_original_order, top1_sentence, elapsed_ms).
    """
    tok, sess, np = load_filter()
    query = build_query(test)
    enc = tok(
        [query] * len(sentences),
        sentences,
        padding=True,
        truncation=True,
        max_length=256,
        return_tensors="np",
    )
    wanted = {i.name for i in sess.get_inputs()}
    ort_inputs = {
        k: np.asarray(enc[k]).astype(np.int64)
        for k in ("input_ids", "attention_mask", "token_type_ids")
        if k in wanted and k in enc
    }
    start = time.perf_counter()
    logits = sess.run(None, ort_inputs)[0]
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    scores = logits.reshape(-1)
    order = sorted(range(len(sentences)), key=lambda i: float(scores[i]), reverse=True)
    top1 = sentences[order[0]]
    keep_idx = set(order[:top_k])
    kept = [s for i, s in enumerate(sentences) if i in keep_idx]
    return kept, top1, elapsed_ms


# ============================================================
# BUILD JEV STATE (fresh context = empty history is fine)
# ============================================================
def build_state(test, sentences):
    return {
        "participants": [
            {"id": "U", "role": "mute_user"},
            {"id": "P", "role": "partner"},
        ],
        "scene": test["scene"],
        "conversation_history": test["history"],
        "current_communication": {
            "speaker": "U",
            "interpreted_fragment": " + ".join(test["gestures"]),
            "gesture": "+".join(test["gestures"]),
            "possible_meanings": sentences,
        },
    }


def build_question(sentences):
    criteria = {
        s: f'This is a candidate full sentence the user may intend: "{s}".'
        for s in sentences
    }
    return {
        "type": "choice",
        "instructions": (
            "Two humans are talking to each other; one communicates only via gestures. "
            "Given the scene, conversation history, and gesture sequence, choose the ONE candidate sentence "
            "most likely intended. Prefer the most natural fit for context and grammar. "
            "Broken gesture-grammar (e.g. 'I am like pasta', 'what you want water') is acceptable — "
            "pick whichever candidate fits best, choosing exactly one from the supplied list."
        ),
        "criteria": criteria,
    }


# ============================================================
# SINGLE JEV CALL
# ============================================================
def resolve(test, sentences):
    state = build_state(test, sentences)
    question = build_question(sentences)
    body = json.dumps(
        {"model": MODEL, "state": state, "questions": {"sentence": question}}
    ).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8")
        except Exception:
            detail = ""
        raise RuntimeError(f"JEV API HTTP {e.code}: {detail or e.reason}") from e
    latency_ms = (time.perf_counter() - start) * 1000.0
    answer = payload["answers"]["sentence"]
    return {
        "selected": answer["choice"],
        "confidence": answer.get("confidence"),
        "probabilities": answer.get("probabilities"),
        "latencyMs": latency_ms,
        "usage": payload.get("usage"),
        "provider": payload.get("provider"),
        "model": payload.get("model"),
        "requestId": payload.get("id"),
    }


# ============================================================
# BENCHMARK HELPERS (same style as jev_test_guess/script.js)
# ============================================================
def percentile(values, p):
    if not values:
        return 0
    ordered = sorted(values)
    index = (p / 100) * (len(ordered) - 1)
    lower = int(index // 1)
    upper = int(-(-index // 1))  # ceil
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def calculate_summary(results):
    valid = [r for r in results if not r.get("error")]
    latencies = [r["latencyMs"] for r in valid if r.get("latencyMs") is not None]
    correct = sum(1 for r in valid if r.get("correct"))
    total = len(valid)

    def avg(arr):
        return sum(arr) / len(arr) if arr else 0

    by_level = {}
    for level in (1, 2, 3):
        group = [r for r in valid if r.get("level") == level]
        hits = sum(1 for r in group if r.get("correct"))
        by_level[f"L{level}"] = {
            "correct": hits,
            "total": len(group),
            "accuracyPercent": round((hits / len(group) if group else 0) * 100, 2),
        }

    filt_ms = [r.get("filterMs") or 0 for r in valid]
    kept_flags = [r for r in valid if r.get("filterKeptAnswer") is not None]
    filter_recall = (
        sum(1 for r in kept_flags if r.get("filterKeptAnswer")) / len(kept_flags)
        if kept_flags
        else 1.0
    )

    return {
        "totalTests": len(results),
        "successful": total,
        "errors": len(results) - total,
        "correct": correct,
        "incorrect": total - correct,
        "accuracyPercent": round((correct / total if total else 0) * 100, 2),
        "byLevel": by_level,
        "filter": {
            "recallPercent": round(filter_recall * 100, 2),
            "avgOptionsBefore": round(avg([r.get("optionsBefore") or 0 for r in valid]), 2),
            "avgOptionsAfter": round(avg([r.get("optionsAfter") or 0 for r in valid]), 2),
            "avgMs": round(avg(filt_ms), 2),
        },
        "confidence": {
            "all": round(avg([r.get("confidence") or 0 for r in valid]), 3),
            "correct": round(
                avg([r.get("confidence") or 0 for r in valid if r.get("correct")]), 3
            ),
            "incorrect": round(
                avg([r.get("confidence") or 0 for r in valid if not r.get("correct")]),
                3,
            ),
        },
        "latencyMs": {
            "min": min(latencies) if latencies else 0,
            "average": round(avg(latencies), 2),
            "p50": round(percentile(latencies, 50), 2),
            "p90": round(percentile(latencies, 90), 2),
            "p95": round(percentile(latencies, 95), 2),
            "p99": round(percentile(latencies, 99), 2),
            "max": max(latencies) if latencies else 0,
        },
    }


# ============================================================
# MAIN
# ============================================================
def run_one(args):
    test, i, total = args
    sentences = build_sentences(test["gestures"])
    accepted = test.get("accept", [test["answer"]])
    before = len(sentences)
    filter_ms, top1, kept = 0.0, sentences[0], sentences
    if not NO_FILTER and before > TOP_K:
        try:
            kept, top1, filter_ms = minilm_topk(test, sentences, TOP_K)
        except Exception as err:  # noqa: BLE001 - report per-test, keep going
            print(f"✗ [{i + 1}/{total}] {test['id']} | FILTER ERROR: {err}", flush=True)
            return {
                "testId": test["id"],
                "level": test["level"],
                "category": test["category"],
                "gestures": test["gestures"],
                "candidates": sentences,
                "expected": test["answer"],
                "error": f"filter: {err}",
            }
    after = len(kept)
    kept_answer = any(a in kept for a in accepted)
    tag = f"kept={after}/{before} | filter={filter_ms:.0f}ms"
    if FILTER_ONLY:
        correct = top1 in accepted
        print(
            f"{'✓' if correct else '✗'} [{i + 1}/{total}] {test['id']} | "
            f"got=\"{top1}\" | exp=\"{test['answer']}\" | {tag}",
            flush=True,
        )
        return {
            "testId": test["id"],
            "level": test["level"],
            "category": test["category"],
            "gestures": test["gestures"],
            "candidates": sentences,
            "expected": test["answer"],
            "accepted": accepted,
            "selected": top1,
            "correct": correct,
            "confidence": None,
            "probabilities": None,
            "latencyMs": filter_ms,
            "optionsBefore": before,
            "optionsAfter": after,
            "filterMs": filter_ms,
            "filterTop1": top1,
            "filterKeptAnswer": kept_answer,
            "error": None,
        }
    try:
        res = resolve(test, kept)
        accepted = test.get("accept", [test["answer"]])
        correct = res["selected"] in accepted
        record = {
            "testId": test["id"],
            "level": test["level"],
            "category": test["category"],
            "gestures": test["gestures"],
            "candidates": kept,
            "expected": test["answer"],
            "accepted": accepted,
            "selected": res["selected"],
            "correct": correct,
            "confidence": res["confidence"],
            "probabilities": res["probabilities"],
            "latencyMs": res["latencyMs"],
            "optionsBefore": before,
            "optionsAfter": after,
            "filterMs": filter_ms,
            "filterTop1": top1,
            "filterKeptAnswer": kept_answer,
            "error": None,
        }
        conf = res["confidence"] or 0
        print(
            f"{'✓' if correct else '✗'} [{i + 1}/{total}] {test['id']} | "
            f"got=\"{res['selected']}\" | exp=\"{test['answer']}\" | "
            f"{res['latencyMs']:.0f}ms | conf={conf:.2f} | {tag}",
            flush=True,
        )
        return record
    except Exception as err:  # noqa: BLE001 - report per-test, keep going
        print(f"✗ [{i + 1}/{total}] {test['id']} | ERROR: {err}", flush=True)
        return {
            "testId": test["id"],
            "level": test["level"],
            "category": test["category"],
            "gestures": test["gestures"],
            "candidates": sentences,
            "expected": test["answer"],
            "error": str(err),
        }


def main():
    print("\n================================================")
    print("   JEV SENTENCE-BUILDER BENCHMARK")
    print("================================================")
    if DRY_RUN:
        mode = "DRY-RUN (no API)"
    elif FILTER_ONLY:
        mode = "FILTER-ONLY (MiniLM top-1, no API)"
    elif NO_FILTER:
        mode = "LIVE no-filter baseline"
    else:
        mode = f"LIVE (MiniLM top-{TOP_K} + Jev)"
    print(f"Model: {MODEL} | Mode: {mode}")
    print(f"Tests: {len(tests)}")

    # Validate every answer is actually reachable (must be one permutation)
    for test in tests:
        sentences = build_sentences(test["gestures"])
        n = len(sentences)
        accepted = test.get("accept", [test["answer"]])
        reachable = all(a in sentences for a in accepted)
        print(
            f"\n[L{test['level']}/{test['category']}] {test['id']} "
            f"gestures=[{', '.join(test['gestures'])}] → {n} options | "
            f"answer=\"{test['answer']}\" | accept={len(accepted)} | "
            f"reachable={'YES' if reachable else 'NO ✗'}"
        )
        if DRY_RUN:
            for s in sentences:
                mark = "  ← accepted" if s in accepted else ""
                print(f"   - {s}{mark}")
        if not reachable:
            raise RuntimeError(
                f"Test \"{test['id']}\" has accepted answers NOT in permutations. Fix test.json."
            )

    if DRY_RUN:
        print(
            "\nDry-run OK — all answers reachable. "
            "Run live with: OPENROUTER_API_KEY=xxx python script.py"
        )
        return

    if FILTER_ONLY or not NO_FILTER:
        print("Warming up MiniLM filter (first run downloads model once)...")
        warm_k, warm_top1, warm_fms = minilm_topk(
            tests[0], build_sentences(tests[0]["gestures"]), TOP_K
        )
        print(f"MiniLM OK (kept {len(warm_k)}, top1=\"{warm_top1}\", {warm_fms:.0f}ms)")

    if not FILTER_ONLY:
        print("\nWarming up JEV model...")
        warm_sentences = build_sentences(tests[0]["gestures"])
        warm = resolve(tests[0], warm_sentences)
        print(f"Warmup OK (latency {warm['latencyMs']:.0f}ms, picked \"{warm['selected']}\")")

    with ThreadPoolExecutor(max_workers=min(32, len(tests))) as pool:
        results = list(
            pool.map(run_one, [(t, i, len(tests)) for i, t in enumerate(tests)])
        )

    summary = calculate_summary(results)
    output = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "model": MODEL,
        "results": results,
        "summary": summary,
    }
    out_path = RESULTS_DIR / "latest.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("\n================================================")
    print(f"Accuracy: {summary['accuracyPercent']}% ({summary['correct']}/{summary['successful']})")
    for lvl, s in (summary.get("byLevel") or {}).items():
        print(f"  {lvl}: {s['accuracyPercent']}% ({s['correct']}/{s['total']})")
    flt = summary.get("filter") or {}
    if flt:
        print(f"Filter recall: {flt.get('recallPercent')}% | kept {flt.get('avgOptionsAfter')}/{flt.get('avgOptionsBefore')} | {flt.get('avgMs')}ms avg")
    print(f"P50: {summary['latencyMs']['p50']}ms | P95: {summary['latencyMs']['p95']}ms")
    print(f"Saved: {out_path}")
    print("================================================\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(f"\nFatal Error: {e}", file=sys.stderr)
        sys.exit(1)
