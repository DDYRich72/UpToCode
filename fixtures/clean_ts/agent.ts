import { run, tool } from "@openai/agents";
import { trace } from "@opentelemetry/api";
import { z } from "zod";

const lookup = tool({name: "lookup", parameters: z.object({query: z.string()})});
run(agent, {
  maxTurns: 8,
  maxTokens: 512,
  signal: AbortSignal.timeout(10_000),
  maxRetries: 2,
});
