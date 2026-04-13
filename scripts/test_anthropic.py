import os
import anthropic
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("ANTHROPIC_API_KEY")
client = anthropic.Anthropic(api_key=api_key)

try:
    # Try a very basic call with the most common model
    # If this fails, we ask the user what models they see in their Anthropic Console
    message = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=10,
        messages=[{"role": "user", "content": "Hello"}]
    )
    print("Success with sonnet-20240620")
except Exception as e:
    print(f"Failed with sonnet-20240620: {e}")
    try:
        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=10,
            messages=[{"role": "user", "content": "Hello"}]
        )
        print("Success with haiku-20240307")
    except Exception as e2:
        print(f"Failed with haiku-20240307: {e2}")
