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
print(agent.ask("How many fatal crashes were there in 2024?"))

print("\n=== Test 2: daily limit (expect NO waits, friendly message) ===")
agent.CLIENT = FakeClient(FlakyModels(real_models, failures=99,
                                      message="Quota exceeded: GenerateRequestsPerDayPerProjectPerModel-FreeTier"))
print(agent.ask("How many fatal crashes were there in 2024?"))