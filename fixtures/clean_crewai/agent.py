import logging
from crewai import Agent, Crew, Process

# uptocode: eval agent
agent = Agent(
    role="worker",
    goal="work",
    max_iter=8,
    max_execution_time=30,
    max_retry_limit=2,
)
crew = Crew(agents=[agent], process=Process.sequential)
logging.info("crew start")
crew.kickoff()
