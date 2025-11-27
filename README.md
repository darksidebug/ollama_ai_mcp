<!-- docker compose --build
docker run -it -p 11434:11434 ollama/ollama:latest serve -->
docker compose up -d --build
docker exec -it ollama-cpu ollama pull llama3

curl -X POST http://localhost:8002/generate \
  -H "X-API-KEY: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"What is the latest tech as of this year?", "model": "llama3"}'
