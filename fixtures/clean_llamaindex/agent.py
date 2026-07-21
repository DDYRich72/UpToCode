import logging
from llama_index.core.agent.workflow import ReActAgent

# uptocode: eval agent
agent = ReActAgent(tools=[], max_iterations=8, timeout=10, max_retries=2, token_limit=2048)
logging.info("agent run")
agent.run("work")
