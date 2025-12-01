## **Self-Hosted AI Model (LLaMA 3) with Python + FastAPI**

#### Clone or fork the project

### CD to the project directory
```bash
docker compose up -d --build
```

```bash
docker exec -it ollama-cpu ollama pull llama3
```

```bash
curl -X POST http://localhost:8002/generate \
  -H "X-API-KEY: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"What is the latest tech as of this year?", "model": "llama3"}'
```

- Replace `your_api_key` with your generated key
