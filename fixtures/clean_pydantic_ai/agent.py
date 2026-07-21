import logging
from pydantic_ai import Agent, ModelSettings, UsageLimits

# uptocode: eval agent
agent = Agent("model")
limits = UsageLimits(request_limit=8, total_tokens_limit=2048)
settings = ModelSettings(timeout=10, max_retries=2)
logging.info("agent run")
agent.run_sync("work", usage_limits=limits, model_settings=settings)
