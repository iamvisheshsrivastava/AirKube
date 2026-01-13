FROM python:3.10

WORKDIR /app
COPY ml/ ./ml/

RUN pip install fastapi uvicorn scikit-learn joblib

CMD ["uvicorn", "ml.inference:app", "--host", "0.0.0.0", "--port", "8000"]
