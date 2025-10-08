import ollama
client = ollama.Client()  # 預設 http://127.0.0.1:11434
resp = client.chat(model="qwen2.5:7b", messages=[{"role":"user","content":"hi"}])
print(resp["message"]["content"])
