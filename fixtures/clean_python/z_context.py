import logging

from openai import OpenAI

logger = logging.getLogger(__name__)
client = OpenAI(timeout=30, max_retries=2)
history = []
RUN_BUDGET = 100

for item in work_items:
    logger.info("processing item")
    if requests_used >= RUN_BUDGET:
        break
    history.append(item)
    history[:] = history[-20:]
    client.responses.create(
        input=history,
        max_output_tokens=100,
        timeout=30,
    )
