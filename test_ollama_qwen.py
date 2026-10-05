import json
import sys
import requests


# ============================================================
# SycAudit — Local Ollama / Qwen3:30B Connectivity Test
# ============================================================

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen3:30b"

TEST_PROMPT = "Reply with exactly: SYCAUDIT_OLLAMA_TEST_OK"


def main():
    print("=" * 60)
    print("SYCAUDIT — LOCAL OLLAMA QWEN TEST")
    print("=" * 60)

    print(f"Ollama URL : {OLLAMA_URL}")
    print(f"Model      : {MODEL}")
    print()

    # --------------------------------------------------------
    # 1. Check whether Ollama is reachable
    # --------------------------------------------------------
    print("[1/3] Checking Ollama connection...")

    try:
        response = requests.get(
            "http://localhost:11434/api/tags",
            timeout=10,
        )

        response.raise_for_status()

        print("[PASS] Ollama server is reachable.")

    except requests.exceptions.ConnectionError:
        print("[FAIL] Could not connect to Ollama.")
        print()
        print("Make sure Ollama is running.")
        print("Try:")
        print("    ollama serve")
        sys.exit(1)

    except requests.exceptions.RequestException as exc:
        print(f"[FAIL] Ollama connection error: {exc}")
        sys.exit(1)

    # --------------------------------------------------------
    # 2. Check that qwen3:30b exists locally
    # --------------------------------------------------------
    print()
    print("[2/3] Checking local model...")

    try:
        tags_response = requests.get(
            "http://localhost:11434/api/tags",
            timeout=10,
        )

        tags_response.raise_for_status()
        tags_data = tags_response.json()

        models = tags_data.get("models", [])

        model_names = [
            model.get("name", "")
            for model in models
        ]

        if MODEL not in model_names:
            print(f"[FAIL] Model '{MODEL}' was not found.")
            print()
            print("Available local models:")

            for name in model_names:
                print(f"    - {name}")

            print()
            print("If necessary, run:")
            print(f"    ollama pull {MODEL}")

            sys.exit(1)

        print(f"[PASS] Local model found: {MODEL}")

    except (requests.exceptions.RequestException, ValueError) as exc:
        print(f"[FAIL] Could not inspect Ollama models: {exc}")
        sys.exit(1)

    # --------------------------------------------------------
    # 3. Actually call Qwen3:30B
    # --------------------------------------------------------
    print()
    print("[3/3] Sending test request to Qwen3:30B...")
    print()
    print(f"Prompt: {TEST_PROMPT}")
    print()

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a strict API test assistant. "
                    "Follow the user's instruction exactly."
                ),
            },
            {
                "role": "user",
                "content": TEST_PROMPT,
            },
        ],
        "stream": False,
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=300,
        )

        response.raise_for_status()

    except requests.exceptions.Timeout:
        print("[FAIL] Ollama request timed out.")
        sys.exit(1)

    except requests.exceptions.ConnectionError:
        print("[FAIL] Lost connection to Ollama.")
        sys.exit(1)

    except requests.exceptions.HTTPError as exc:
        print(f"[FAIL] Ollama returned an HTTP error: {exc}")
        print()
        print("Raw response:")
        print(response.text)
        sys.exit(1)

    except requests.exceptions.RequestException as exc:
        print(f"[FAIL] Ollama request failed: {exc}")
        sys.exit(1)

    # --------------------------------------------------------
    # Parse response
    # --------------------------------------------------------
    try:
        data = response.json()

    except ValueError:
        print("[FAIL] Ollama returned invalid JSON.")
        print()
        print("Raw response:")
        print(response.text)
        sys.exit(1)

    print("=== FULL OLLAMA RESPONSE ===")
    print(json.dumps(data, indent=2, ensure_ascii=False))

    # --------------------------------------------------------
    # Extract model message
    # --------------------------------------------------------
    message = data.get("message")

    if not isinstance(message, dict):
        print()
        print("[FAIL] Response does not contain a valid 'message' object.")
        sys.exit(1)

    content = message.get("content")

    if not isinstance(content, str):
        print()
        print("[FAIL] Response does not contain message content.")
        sys.exit(1)

    print()
    print("=== MODEL CONTENT ===")
    print(repr(content))

    # --------------------------------------------------------
    # Final validation
    # --------------------------------------------------------
    expected = "SYCAUDIT_OLLAMA_TEST_OK"

    if content.strip() == expected:
        print()
        print("=" * 60)
        print("[PASS] LOCAL OLLAMA QWEN TEST SUCCESSFUL")
        print("=" * 60)
        print()
        print("Verified:")
        print("  Python")
        print("    ↓")
        print("  localhost:11434")
        print("    ↓")
        print("  Ollama")
        print("    ↓")
        print("  qwen3:30b")
        print("    ↓")
        print("  Model response")
        print()
    else:
        print()
        print("[FAIL] Qwen responded, but the output was not exactly:")
        print(expected)
        print()
        print("Actual output:")
        print(repr(content))
        sys.exit(1)


if __name__ == "__main__":
    main()