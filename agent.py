# agent.py
from openai import OpenAI
import json

SYSTEM_PROMPT = """You must respond with valid JSON only. No explanations, no text outside JSON.
IMPORTANT: Escape double quotes inside strings with backslash.

Output format:
{
  "action": "shell" | "respond",
  "command": "shell command",
  "content": "response message"
}

Examples:
- User: "list files" → {"action": "shell", "command": "ls -la"}
- User: "create hello.txt with 'hi'" → {"action": "shell", "command": "echo hi > hello.txt"}
- User: "show file content" → {"action": "shell", "command": "cat hello.txt"}
- User: "create python file" → {"action": "shell", "command": "echo 'print(\\\"Hello\\\")' > test.py"}
- User: "hello" → {"action": "respond", "content": "Hello! How can I help?"}"""

class Agent:
    def __init__(self):
        self.client = OpenAI(
            base_url="http://127.0.0.1:1234/v1",
            api_key="lm-studio"
        )

    def think(self, user_input: str) -> dict:
        prompt = f"""{SYSTEM_PROMPT}

User request: {user_input}

Respond with JSON only:"""
        
        response = self.client.chat.completions.create(
            model="microsoft/phi-3-mini-4k-instruct",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        content = response.choices[0].message.content.strip()

        # Remove markdown code blocks se existirem
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        # 🔒 Parser defensivo
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            # Tenta corrigir aspas não escapadas
            import re
            # Encontra strings entre aspas simples que contém aspas duplas
            fixed = re.sub(r"'([^']*\"[^']*)'", lambda m: f"'{m.group(1).replace('\"', '\\\"')}'", content)
            try:
                return json.loads(fixed)
            except:
                pass
            raise ValueError(f"Resposta não é JSON válido:\n{content}\nErro: {e}")
