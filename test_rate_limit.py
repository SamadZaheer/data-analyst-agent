"""Fault injection for rate limits: fake 429 errors and check call_gemini/ask handle them."""
from google.genai import errors
import agent

agent.RETRY_DELAYS = [1, 2, 3]   # short waits for testing


class FlakyModels:
    """Wraps the real client.models: raises fake errors a set number of times, then works."""
    def __init__(self, real_models, failures, message):
        self.real = real_models
        self.failures_left = failures
        self.message = message

    def generate_content(self, **kwargs):
        if self.failures_left > 0:
            self.failures_left -= 1
            raise errors.ClientError(429, {"error": {
                "code": 429, "status": "RESOURCE_EXHAUSTED", "message": self.message}})
        return self.real.generate_content(**kwargs)

class FakeClient:
    def __init__(self, models):
        self.models = models

real_client = agent.CLIENT          
real_models = real_client.models

print("=== Test 1: per-minute limit twice, then OK (expect 2 waits, then 273) ===")
agent.CLIENT = FakeClient(FlakyModels(real_models, failures=2,
                                      message="Quota exceeded: GenerateRequestsPerMinutePerProjectPerModel-FreeTier"))
r1 = agent.ask("How many fatal crashes were there in 2024?")
print("ANSWER:", r1.answer)

assert r1.status == "answered", f"status was {r1.status}"
assert "273" in r1.answer, "wrong final answer"
assert r1.seconds >= 3, "expected ~3s of waiting (1s + 2s): did the retries happen?"
print("✅ Test 1 passed")

print("\n=== Test 2: daily limit (expect NO waits, friendly message) ===")
agent.CLIENT = FakeClient(FlakyModels(real_models, failures=99,
                                      message="Quota exceeded: GenerateRequestsPerDayPerProjectPerModel-FreeTier"))
r2 = agent.ask("How many fatal crashes were there in 2024?")
print("ANSWER:", r2.answer)

assert r2.status == "api_error", f"status was {r2.status}"
assert r2.error_code == 429
assert r2.steps == 0, "no request should have succeeded"
assert r2.seconds < 1, "daily limit should fail instantly, not wait"
print("✅ Test 2 passed")