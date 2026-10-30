"""Settings shared by every agent. Change the model here (or in .env), nowhere else."""

import os

from dotenv import load_dotenv
from google.adk.models import Gemini
from google.genai import types

load_dotenv()  # finds the .env in the repo root

MODEL_NAME = os.getenv("MODEL", "gemini-3.8-flash")

# Many agents at once can hit rate limits: retry 429s with backoff.
MODEL = Gemini(
    model=MODEL_NAME,
    retry_options=types.HttpRetryOptions(attempts=5, initial_delay=2, max_delay=30),
)

# Appended to every instruction. Attendees type Turkish, so agents answer in the user's language.
HOUSE_RULES = """
House rules:
- Answer in the language the user writes in (Turkish question, Turkish answer).
- Every number you state must come from a tool result or an earlier report in this conversation.
- Keep every number with its scope: "last 10 matches" and "league season" figures are different numbers.
- If a tool says "not available", say it is not available. Never guess or estimate a number.
- Be brief and concrete: short bullet points, the numbers that matter, no filler.
"""
