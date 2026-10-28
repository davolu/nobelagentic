"""Handoffs between agents — the seed of the Crew API."""
from swarmagents import Agent

spanish = Agent("You only speak Spanish. Answer briefly.", name="spanish")
french = Agent("You only speak French. Answer briefly.", name="french")

triage = Agent(
    "Route the user to the right language agent. Hand off immediately; do not answer yourself.",
    name="triage",
    handoffs=[spanish, french],
)

result = triage.run("Bonjour, comment allez-vous?")
print(result.agent, "→", result.output)
