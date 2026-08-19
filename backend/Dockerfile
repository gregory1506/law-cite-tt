FROM python:3.13-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/scraper ./scraper
COPY backend/api ./api
COPY backend/scripts ./scripts
COPY templates ./templates
COPY graphify-out/case_edges.json ./case_edges.json

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
