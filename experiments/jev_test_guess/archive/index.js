import { OpenRouter } from "@openrouter/sdk";

const openrouter = new OpenRouter({
  apiKey: process.env.OPENROUTER_API_KEY,
});

const start = performance.now();

try {
  const decision = await openrouter.alpha.decisions.create({
    decisionsRequest: {
      model: "~typesafe/jev-latest",

      state: {
        conversation: "I am going",
        scene: "The person is standing beside a car.",
        gesture: "QUESTION",
      },

      questions: {
        meaning: {
          type: "choice",

          instructions:
            "Which candidate best represents the intended meaning of the current gesture, considering the conversation and scene?",

          criteria: {
            where:
              "The person is asking about a location or destination.",

            what:
              "The person is asking about a thing, object, or information.",

            when:
              "The person is asking about a time or timing.",

            why:
              "The person is asking about a reason or cause.",

            how:
              "The person is asking about a method or way of doing something.",
          },
        },
      },
    },
  });

  const latency = performance.now() - start;

  console.log("\n========== JEV RESULT ==========\n");

  console.log("Latency:", latency.toFixed(2), "ms");

  console.log("\nAnswer:");
  console.dir(decision.answers.meaning, {
    depth: null,
  });

  console.log("\nFull response:");
  console.dir(decision, {
    depth: null,
  });

} catch (error) {
  const latency = performance.now() - start;

  console.error("\nJEV REQUEST FAILED");
  console.error("Latency:", latency.toFixed(2), "ms");
  console.error(error);
}
