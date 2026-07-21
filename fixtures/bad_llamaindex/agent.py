from llama_index.core.agent.workflow import FunctionAgent

agent = FunctionAgent(tools=[])
agent.run("work")
