# agent.py
from openai import OpenAI
import json

BASE_URL = "http://127.0.0.1:1234/v1"
MODEL_NAME = "tanto_faz"
MAX_HISTORY = 20  # Número máximo de mensagens no histórico

SYSTEM_PROMPT = """You are a file system assistant. Respond ONLY with valid JSON, no explanations.

Actions: list_files, read_file, write_file, edit_file, delete_file, shell, respond

Format: {"action": "ACTION", "path": "FILE", "content": "TEXT"}

CRITICAL RULES:
1. NEVER use triple quotes in JSON strings
2. Use \\n for newlines inside "content"
3. Escape quotes with \\"
4. Return ONLY the JSON object, nothing else

Examples:

User: list files
Assistant: {"action": "list_files", "path": "."}

User: create hello.py with print hello
Assistant: {"action": "write_file", "path": "hello.py", "content": "print('hello')"}

User: create test.py that asks name and prints it
Assistant: {"action": "write_file", "path": "test.py", "content": "name = input('Name: ')\\nprint(f'Hello {name}')"}

User: edit hello.py to add a function
Assistant: {"action": "edit_file", "path": "hello.py", "content": "def greet():\\n    print('hello')\\n\\ngreet()"}

User: read config.json
Assistant: {"action": "read_file", "path": "config.json"}

User: delete old.txt
Assistant: {"action": "delete_file", "path": "old.txt"}

User: run ls command
Assistant: {"action": "shell", "command": "ls -la"}

User: thanks
Assistant: {"action": "respond", "content": "Done!"}

User: what time is it
Assistant: {"action": "respond", "content": "I can only manage files, not tell time"}

User: create app.py with input and length check
Assistant: {"action": "write_file", "path": "app.py", "content": "name = input('Your name: ')\\nprint(f'Length: {len(name)}')"}

User: edit app.py to add greeting
Assistant: {"action": "edit_file", "path": "app.py", "content": "name = input('Your name: ')\\nprint(f'Hello {name}!')\\nprint(f'Length: {len(name)}')"}

REMEMBER: Use \\n for newlines, NEVER use triple quotes!"""

class Agent:
    def __init__(self):
        self.client = OpenAI(
            base_url=BASE_URL,
            api_key="lm-studio"
        )
        self.history = []

    def think(self, user_input: str) -> dict:
        # Adiciona mensagem do usuário ao histórico
        self.history.append({"role": "user", "content": user_input})
        
        # Mantém apenas as últimas MAX_HISTORY mensagens
        if len(self.history) > MAX_HISTORY:
            self.history = self.history[-MAX_HISTORY:]
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "list files"},
            {"role": "assistant", "content": '{"action": "list_files", "path": "."}'},
            {"role": "user", "content": "create test.txt with hello"},
            {"role": "assistant", "content": '{"action": "write_file", "path": "test.txt", "content": "hello"}'},
            {"role": "user", "content": "thanks"},
            {"role": "assistant", "content": '{"action": "respond", "content": "You\'re welcome!"}'}
        ] + self.history
        
        response = self.client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0,
            max_tokens=2000
        )

        content = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks
        if "```" in content:
            # Extrai conteúdo entre ``` ou ```json e ```
            import re
            match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if match:
                content = match.group(1)
            else:
                # Se não achou padrão completo, tenta pegar primeira linha com {
                lines = [l.strip() for l in content.split("\n") if l.strip()]
                for line in lines:
                    if line.startswith("{"):
                        content = line
                        break
        
        # Adiciona resposta do assistente ao histórico
        self.history.append({"role": "assistant", "content": content})

        # Remove tags <think> do DeepSeek R1
        if "<think>" in content:
            parts = content.split("</think>")
            if len(parts) > 1:
                content = parts[1].strip()
            else:
                content = content.split("<think>")[0].strip()
                if not content:
                    raise ValueError("Modelo retornou apenas raciocínio, sem JSON")

        # 🔒 Parser defensivo
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            import re
            
            # Fix: Remove triple quotes dentro de strings JSON
            if '"""' in content:
                # Substitui """ por aspas simples escapadas
                content = content.replace('"""', '')
            
            # Tenta novamente após limpeza
            try:
                return json.loads(content)
            except:
                pass
            
            # Procura por padrão {"action": ...}
            match = re.search(r'\{[^}]*"action"[^}]*\}', content)
            if match:
                try:
                    return json.loads(match.group(0))
                except:
                    pass
            
            # 🧠 Parser inteligente: detecta intenção de criar arquivo
            # Padrão: # Arquivo: nome.ext seguido de código
            file_match = re.search(r'#\s*Arquivo:\s*(\S+)\s*\n+(.*)', content, re.DOTALL)
            if file_match:
                filename = file_match.group(1)
                code = file_match.group(2)
                
                # Remove blocos markdown do código
                code = re.sub(r'```\w*\n?', '', code).strip()
                # Remove texto explicativo após o código
                code = re.split(r'\n\nTo run this', code)[0].strip()
                
                return {
                    "action": "write_file",
                    "path": filename,
                    "content": code
                }
            
            # Se falhou, retorna resposta como texto
            return {"action": "respond", "content": f"Erro: modelo retornou texto ao invés de JSON:\n{content}"}
