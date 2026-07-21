import logging
import anthropic

# uptocode: eval agent
client = anthropic.Anthropic(timeout=10, max_retries=2)
tools = [{"name": "lookup", "description": "Look up a record", "input_schema": {"type": "object"}}]
messages = []
budget = 10
response = client.messages.create(model="claude", max_tokens=256, messages=messages, tools=tools)
while response.stop_reason == "tool_use":
    if budget <= 0:
        break
    budget -= 1
    logging.info("tool turn")
    response = client.messages.create(model="claude", max_tokens=256, messages=messages, tools=tools)
