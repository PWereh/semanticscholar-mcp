FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

ENV HOST=0.0.0.0
ENV S2_API_KEY=""

# Shell-form CMD so $PORT is expanded at runtime from Railway's injected env var
CMD uvicorn server:asgi_app --host 0.0.0.0 --port ${PORT:-8000}
