# model.py
import os
import pickle
import numpy as np

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")
_model = None

def get_model():
    global _model
    if _model is None:
        if os.path.exists(MODEL_PATH):
            with open(MODEL_PATH, "rb") as f:
                _model = pickle.load(f)
        else:
            raise FileNotFoundError(f"Model file not found at {MODEL_PATH}. Run 'python ml/train_model.py' first.")
    return _model

def predict(x):
    model = get_model()
    # Ensure input is 2D array
    prediction = model.predict([x])
    return {"result": int(prediction[0])}
