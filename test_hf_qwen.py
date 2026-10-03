import os
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

# Load environment variables from backend/.env
load_dotenv("backend/.env")

token = os.getenv("HF_TOKEN")
model = os.getenv("HF_MODEL")
provider = os.getenv("HF_PROVIDER", "auto")

if not token:
    raise RuntimeError("HF_TOKEN not found")

if not model:
    raise RuntimeError("HF_MODEL not found")

print("Token configured:", bool(token))
print("Model:", model)
print("Provider:", provider)

# Create Hugging Face client
client = InferenceClient(
    api_key=token,
    provider=provider,
)

print("Sending test request...")

response = client.chat.completions.create(
    model=model,
    messages=[
        {
            "role": "system",
            "content": (
                "You are a strict API test assistant. "
                "After reasoning internally, output only the requested answer."
            ),
        },
        {
            "role": "user",
            "content": "Reply with exactly: SYCAUDIT_API_TEST_OK",
        },
    ],
    max_tokens=512,
)

print("\n=== FULL RESPONSE ===")
print(response)

print("\n=== CONTENT ===")
print(repr(response.choices[0].message.content))

print("\n=== REASONING CONTENT ===")
print(
    repr(
        getattr(
            response.choices[0].message,
            "reasoning_content",
            None,
        )
    )
)