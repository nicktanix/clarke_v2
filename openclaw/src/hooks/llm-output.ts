/**
 * llm_output hook — feed interactions back to CLARKE for learning.
 *
 * Fires after the LLM responds. Submits positive feedback to CLARKE
 * so the learning loop can track which retrieval plans worked. This
 * is fire-and-forget (parallel hook) — it never blocks the response.
 *
 * Combined with user corrections via /clarke-teach, this creates the
 * full feedback loop: every interaction either reinforces or corrects
 * CLARKE's retrieval patterns.
 */

import { getClarkeConfig, submitFeedback } from "../clarke-client.js";
import { lastQueryResult } from "../index.js";

export async function handleLlmOutput(_event: any): Promise<void> {
  const config = getClarkeConfig();
  if (!config) return;

  // If we queried CLARKE for this interaction, submit implicit positive feedback
  // (the user didn't correct it, so it was presumably acceptable)
  const { requestId } = lastQueryResult;
  if (requestId) {
    await submitFeedback(
      config,
      requestId,
      true,
      "Implicit positive — user did not correct the response."
    );

    // Clear for next interaction
    lastQueryResult.requestId = "";
    lastQueryResult.query = "";
  }
}
