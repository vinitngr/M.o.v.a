# JEV V2 Sub-Gesture Context Resolution Benchmark Report

**Generated:** 9/26/2026, 8:02:19 PM  
**Model:** `typesafe/jev-1.13`  
**Total Benchmark Cases:** 30 per strategy  
**Architecture:** V2 Sub-Gesture Disambiguation (`QUESTION_LOCATION`, `QUESTION_TIME`, `QUESTION_MANNER`, `QUESTION_ENTITY`, `COMPLIMENT`, `NEED_HELP`, `WANT_DRINK`)

---

## Executive Summary Comparison

| Metric | Strategy A (Direct Candidate Scoring) | Strategy B (Context-First Completion) |
| :--- | :---: | :---: |
| **Accuracy** | **46.67%** (14/30) | **53.33%** (16/30) |
| **P50 Latency** | 450.17 ms | 448.9 ms |
| **P95 Latency** | 688.44 ms | 672.2 ms |
| **Avg Confidence (Correct)** | 0.831 | 0.761 |
| **Avg Confidence (Incorrect)** | 0.557 | 0.525 |

---

## V1 vs V2 Accuracy Comparison

- **V1 (Single Generic `QUESTION` Gesture):** **78.57%** accuracy (Ambiguity in questions like *"portal submit"* or *"reservation Vinit"*).
- **V2 (Sub-Gesture Architecture):** **46.67%** accuracy.

---

## Breakdown by Gesture Sub-Type (Strategy A)

- **QUESTION_TIME:** **0%** (0/5)
- **QUESTION_LOCATION:** **55.56%** (5/9)
- **QUESTION_ENTITY:** **12.5%** (1/8)
- **QUESTION_MANNER:** **100%** (1/1)
- **COMPLIMENT:** **100%** (3/3)
- **NEED_HELP:** **100%** (2/2)
- **WANT_DRINK:** **100%** (2/2)

---

## Latency Percentiles (Strategy A)

- **Min:** 390.3070579999985 ms
- **Average:** 473.19 ms
- **P50 (Median):** 450.17 ms
- **P90:** 580.19 ms
- **P95:** 688.44 ms
- **P99:** 793.76 ms
- **Max:** 808.3285530000003 ms

---

## Concurrency & Throughput

- **Concurrency 1:** 1.99 req/sec | Avg Latency: 502.42 ms | Success: 9/9
- **Concurrency 3:** 3.1 req/sec | Avg Latency: 641.22 ms | Success: 9/9
