import os
from pathlib import Path
from dotenv import load_dotenv

# Build the path to .env relative to THIS file, so it works on Windows and Mac
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH)

if not os.getenv("GEMINI_API_KEY"):
    raise SystemExit("GEMINI_API_KEY not found. Check your .env file.")

# import google GenAI SDK and test
from google import genai

MODEL = "gemini-3.5-flash-lite"

client = genai.Client()  # automatically picks up GEMINI_API_KEY from the environment

response = client.models.generate_content(
    model=MODEL,
    contents="In one sentence, what does a data analyst do?",
)

print(f"Model: {MODEL}")
print(f"Reply: {response.text}")

# checking that standard LLM API calls are stateless
client.models.generate_content(model=MODEL, contents='My name is Samad.')
r2 = client.models.generate_content(model=MODEL, contents='What is my name?')

print(r2.text)