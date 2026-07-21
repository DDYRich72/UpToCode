import anthropic

client = anthropic.Anthropic()
response = client.messages.create(model="claude", messages=[], tools=[{"name": "delete", "description": "Delete data"}])
turns = 0
while turns < 3:
    turns += 1
    if "DONE" in str(response.content):
        break
    response = client.messages.create(model="claude", messages=[])
