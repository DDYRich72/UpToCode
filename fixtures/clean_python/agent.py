import logging
import os
from pathlib import Path

from agents import Agent, Runner, function_tool
from openai import OpenAI
from pydantic import BaseModel

logger = logging.getLogger(__name__)
client = OpenAI(timeout=30, max_retries=3)
agent = Agent(name="operator")
API_KEY = os.environ["OPENAI_API_KEY"]
TOKEN_BUDGET = 10_000
ALLOWED_ROOT = Path("safe").resolve()


class SafeResult(BaseModel):
    text: str


@function_tool(needs_approval=True)
def delete_user(user_id: str) -> str:
    if not user_id.isalnum():
        raise ValueError("invalid user id")
    logger.info("approved delete", extra={"user_id": user_id})
    return "deleted"


def save_result(value: SafeResult) -> None:
    target = (ALLOWED_ROOT / "result.txt").resolve()
    if ALLOWED_ROOT not in target.parents:
        raise ValueError("unsafe path")
    target.write_text(value.text)


async def run(task: str) -> None:
    spent_tokens = 0
    logger.info("agent run started")
    result = await Runner.run(agent, task)
    response = client.responses.create(
        model="gpt-5.6",
        input=task,
        max_output_tokens=500,
        timeout=30,
    )
    spent_tokens += response.usage.total_tokens
    if spent_tokens >= TOKEN_BUDGET:
        logger.warning("token budget reached")
    save_result(SafeResult.model_validate({"text": result.final_output}))

