from fastapi import FastAPI
from ml.model import predict  

app = FastAPI()

@app.get("/predict")
def run(x: int):
    return predict(x)
