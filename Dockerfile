FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

ENV HOST=0.0.0.0
ENV PORT=8000
# S2_API_KEY is injected at runtime via platform env var — never bake into image
ENV S2_API_KEY="SVsbhZ2ZIF58wiCdfJajl9umjV2H6J2s6xmcTvS4"

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/ || exit 1

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
