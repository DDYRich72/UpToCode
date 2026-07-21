from crewai import Agent, Crew

agent = Agent(role="worker", goal="work", max_iter=None)
crew = Crew(agents=[agent])
crew.kickoff()
