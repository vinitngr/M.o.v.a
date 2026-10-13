import { OpenRouter } from "@openrouter/sdk";
import fs from "node:fs/promises";
import path from "node:path";

const MODEL = "typesafe/jev-1.13";
const apiKey = process.env.OPENROUTER_API_KEY;

if (!apiKey) {
  throw new Error("OPENROUTER_API_KEY environment variable is missing.");
}

const openrouter = new OpenRouter({ apiKey });

// Load compact dataset.json
const datasetRaw = await fs.readFile("dataset.json", "utf-8");
const { sessions } = JSON.parse(datasetRaw);

const RESULTS_DIR = "benchmark-results";
await fs.mkdir(RESULTS_DIR, { recursive: true });

// ============================================================
// BUILD JEV STATE
// ============================================================
function buildState(session, decision) {
  return {
    participants: session.participants,
    scene: session.scene,
    conversation_history: session.turns,
    current_communication: {
      speaker: "U",
      interpreted_fragment: decision.current_fragment,
      gesture: decision.gesture,
      possible_meanings: decision.candidates,
    },
  };
}

// ============================================================
// STRATEGY A — DIRECT CANDIDATE SCORING
// ============================================================
function buildQuestionStrategyA(decision) {
  const criteria = {};
  for (const candidate of decision.candidates) {
    criteria[candidate] = `The intended semantic keyword is "${candidate}".`;
  }

  return {
    type: "choice",
    instructions:
      "Determine which candidate keyword best represents what the non-verbal user intends to communicate at this point in the conversation. " +
      "Use conversation history, scene context, speaker identities, and current gesture fragment. " +
      "Choose exactly one candidate from the supplied list.",
    criteria,
  };
}

// ============================================================
// STRATEGY B — CONTEXT-FIRST SEMANTIC COMPLETION
// ============================================================
function buildQuestionStrategyB(decision) {
  const criteria = {};
  for (const candidate of decision.candidates) {
    criteria[candidate] = `Select "${candidate}" if it is the most natural, semantically fluent word completing the user's intent in this conversation scene.`;
  }

  return {
    type: "choice",
    instructions:
      "Context-first resolution: Infer what semantic concept naturally completes the user's turn in this exact scene, " +
      "strictly choosing the best candidate from the supplied list. " +
      "Focus heavily on conversational continuity, scene role, and immediate dialogue context.",
    criteria,
  };
}

// ============================================================
// SINGLE JEV RESOLUTION CALL
// ============================================================
async function resolve(session, decision, strategy = "A") {
  const state = buildState(session, decision);
  const question = strategy === "B" ? buildQuestionStrategyB(decision) : buildQuestionStrategyA(decision);

  const start = performance.now();
  const response = await openrouter.alpha.decisions.create({
    decisionsRequest: {
      model: MODEL,
      state,
      questions: { meaning: question },
    },
  });
  const latency = performance.now() - start;

  const answer = response.answers.meaning;
  return {
    selected: answer.choice,
    confidence: answer.confidence,
    probabilities: answer.probabilities,
    latencyMs: latency,
    usage: response.usage ?? null,
    provider: response.provider,
    model: response.model,
    requestId: response.id,
  };
}

// ============================================================
// PERCENTILE CALCULATION
// ============================================================
function percentile(values, p) {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const index = (p / 100) * (sorted.length - 1);
  const lower = Math.floor(index);
  const upper = Math.ceil(index);
  if (lower === upper) return sorted[lower];
  return sorted[lower] + (sorted[upper] - sorted[lower]) * (index - lower);
}

// ============================================================
// CALCULATE BENCHMARK SUMMARY
// ============================================================
function calculateSummary(results) {
  const valid = results.filter(r => !r.error);
  const latencies = valid.map(r => r.latencyMs);
  const correct = valid.filter(r => r.correct).length;
  const total = valid.length;
  const accuracyPercent = total ? (correct / total) * 100 : 0;

  const avg = arr => (arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0);

  return {
    totalTests: results.length,
    successful: total,
    errors: results.length - total,
    correct,
    incorrect: total - correct,
    accuracyPercent: Number(accuracyPercent.toFixed(2)),
    confidence: {
      all: Number(avg(valid.map(r => r.confidence)).toFixed(3)),
      correct: Number(avg(valid.filter(r => r.correct).map(r => r.confidence)).toFixed(3)),
      incorrect: Number(avg(valid.filter(r => !r.correct).map(r => r.confidence)).toFixed(3)),
    },
    latencyMs: {
      min: latencies.length ? Math.min(...latencies) : 0,
      average: Number(avg(latencies).toFixed(2)),
      p50: Number(percentile(latencies, 50).toFixed(2)),
      p90: Number(percentile(latencies, 90).toFixed(2)),
      p95: Number(percentile(latencies, 95).toFixed(2)),
      p99: Number(percentile(latencies, 99).toFixed(2)),
      max: latencies.length ? Math.max(...latencies) : 0,
    },
  };
}

// ============================================================
// RUN BENCHMARK PASS
// ============================================================
async function runBenchmarkPass(strategyName, strategyCode) {
  console.log(`\n================================================`);
  console.log(`           RUNNING STRATEGY ${strategyName}`);
  console.log(`================================================`);

  const results = [];
  let completed = 0;
  const totalDecisions = sessions.reduce((s, sess) => s + sess.decisions.length, 0);

  for (const session of sessions) {
    for (const decision of session.decisions) {
      completed++;
      try {
        const res = await resolve(session, decision, strategyCode);
        const correct = res.selected === decision.expected;
        const record = {
          strategy: strategyName,
          sessionId: session.id,
          decisionId: decision.id,
          currentFragment: decision.current_fragment,
          gesture: decision.gesture,
          candidates: decision.candidates,
          expected: decision.expected,
          selected: res.selected,
          correct,
          confidence: res.confidence,
          probabilities: res.probabilities,
          latencyMs: res.latencyMs,
          error: null,
        };
        results.push(record);

        const mark = correct ? "✓" : "✗";
        console.log(
          `${mark} [${completed}/${totalDecisions}] ${decision.id} (${decision.gesture}) | got=${res.selected} | exp=${decision.expected} | ${res.latencyMs.toFixed(0)}ms | conf=${res.confidence.toFixed(2)}`
        );
      } catch (err) {
        console.error(`✗ [${completed}/${totalDecisions}] ${decision.id} | ERROR: ${err.message}`);
        results.push({
          strategy: strategyName,
          sessionId: session.id,
          decisionId: decision.id,
          expected: decision.expected,
          candidates: decision.candidates,
          gesture: decision.gesture,
          error: err.message,
        });
      }
    }
  }

  return { results, summary: calculateSummary(results) };
}

// ============================================================
// MAIN BENCHMARK RUNNER
// ============================================================
async function main() {
  console.log("\n================================================");
  console.log("   MOVA × JEV COMPACT DATASET BENCHMARK");
  console.log("================================================");
  console.log(`Model: ${MODEL}`);
  console.log(`Total Sessions: ${sessions.length}`);
  const totalDecisions = sessions.reduce((s, sess) => s + sess.decisions.length, 0);
  console.log(`Total Decisions per Strategy: ${totalDecisions}`);

  console.log("\nWarming up JEV model...");
  try {
    const warmupRes = await resolve(sessions[0], sessions[0].decisions[0], "A");
    console.log(`Warmup successful! (Latency: ${warmupRes.latencyMs.toFixed(0)}ms)`);
  } catch (err) {
    console.error(`Warmup failed: ${err.message}`);
    process.exit(1);
  }

  const stratA = await runBenchmarkPass("A", "A");
  const stratB = await runBenchmarkPass("B", "B");

  const overallOutput = {
    timestamp: new Date().toISOString(),
    model: MODEL,
    decisionCount: totalDecisions,
    strategyA: stratA,
    strategyB: stratB,
  };

  const latestJsonPath = path.join(RESULTS_DIR, "latest.json");
  await fs.writeFile(latestJsonPath, JSON.stringify(overallOutput, null, 2));

  console.log("\n================================================");
  console.log("            BENCHMARK RESULTS SUMMARY");
  console.log("================================================");
  console.log(`Strategy A Accuracy: ${stratA.summary.accuracyPercent}% (${stratA.summary.correct}/${stratA.summary.successful})`);
  console.log(`Strategy B Accuracy: ${stratB.summary.accuracyPercent}% (${stratB.summary.correct}/${stratB.summary.successful})`);
  console.log(`P50 Latency:        ${stratA.summary.latencyMs.p50} ms`);
  console.log(`P95 Latency:        ${stratA.summary.latencyMs.p95} ms`);
  console.log("------------------------------------------------");
  console.log(`Saved results to: ${latestJsonPath}`);
  console.log("================================================\n");
}

main().catch(err => {
  console.error("\nFatal Benchmark Error:", err);
  process.exit(1);
});
