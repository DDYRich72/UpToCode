from agents import Agent, Runner, function_tool
from openai import OpenAI
import subprocess

client = OpenAI()
agent = Agent(name="operator")
API_KEY = "sk-proj-abcdefghijklmnopqrstuvwxyz123456"


@function_tool
def delete_user(user_id: str) -> str:
    subprocess.run(user_id)
    return "deleted"


def save_result(value: str) -> None:
    open("result.txt", "w").write(value)


async def run(task: str) -> None:
    while True:
        response = client.responses.create(
            model="gpt-5.6",
            input=f"{task} secret={API_KEY}",
        )
        save_result(response.output_text)

