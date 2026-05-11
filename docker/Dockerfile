FROM python:3.10-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
	PIP_NO_CACHE_DIR=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000 8501

CMD ["uvicorn", "ml.inference:app", "--host", "0.0.0.0", "--port", "8000"]
