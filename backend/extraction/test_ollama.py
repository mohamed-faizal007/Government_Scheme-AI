from openai import OpenAI


# ==========================================================
# OLLAMA LOCAL CLIENT
# ==========================================================

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)


# ==========================================================
# TEST REQUEST
# ==========================================================

print("=" * 80)
print("TESTING PYTHON -> OLLAMA -> QWEN")
print("=" * 80)

print("\nSending request to Qwen 2.5 3B...\n")

response = client.chat.completions.create(
    model="qwen2.5:3b",
    messages=[
        {
            "role": "user",
            "content": (
                "What is a government welfare scheme? "
                "Explain it in one simple sentence."
            ),
        }
    ],
)


# ==========================================================
# RESPONSE
# ==========================================================

answer = response.choices[0].message.content

print("QWEN RESPONSE")
print("-" * 80)
print(answer)

print("\n" + "=" * 80)
print("TEST SUCCESSFUL")
print("=" * 80)