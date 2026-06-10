FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY models/ ./models/
COPY configs/ ./configs/
COPY data/sample_request.json ./data/sample_request.json
COPY reports/ ./reports/
COPY README.md ./README.md

RUN chown -R app:app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import json, urllib.request; r=urllib.request.urlopen(\"http://127.0.0.1:8000/health\", timeout=3); assert json.load(r)[\"status\"] == \"ok\""

CMD ["uvicorn", "financial_mlops.service:app", "--host", "0.0.0.0", "--port", "8000"]
