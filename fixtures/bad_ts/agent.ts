import { run, tool } from "@openai/agents";

const erase = tool({name: "erase", parameters: {}});
while (true) {
  run(agent, {maxTurns: undefined});
}
