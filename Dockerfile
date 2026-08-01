FROM python:3.11-slim

WORKDIR /app

RUN useradd --create-home --uid 1000 appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
# Fallback embarque dans l'image (aucun grant reel) pour que le build marche
# meme sans policies.yaml local. docker-compose monte le vrai fichier par-dessus.
COPY policies.example.yaml ./policies.yaml

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
