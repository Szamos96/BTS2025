from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse, HTMLResponse
import numpy as np
from PIL import Image
import tensorflow as tf
import io
import os

app = FastAPI()
model = tf.keras.applications.mobilenet_v2.MobileNetV2(weights="imagenet")

# Decode predictions
decode_predictions = tf.keras.applications.mobilenet_v2.decode_predictions
preprocess_input = tf.keras.applications.mobilenet_v2.preprocess_input

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/", response_class=HTMLResponse)
def home_page():
    try:
        with open("index.html", 'r', encoding='utf-8') as file:
            content = file.read()
            return content
    except FileNotFoundError:
        return f"Error: The file was not found."
    except Exception as e:
        return f"An unexpected error occurred: {e}"


@app.post("/recognize")
async def recognize_fruit(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        return JSONResponse({"error": "Invalid image"}, status_code=400)

    # Load image
    image_bytes = await file.read()
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = img.resize((224, 224))

    # Preprocess and predict
    img_array = tf.keras.preprocessing.image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    img_array = preprocess_input(img_array)

    preds = model.predict(img_array)
    decoded = decode_predictions(preds, top=3)[0]

    return {"predictions": [{"label": label, "prob": float(prob)} for (_, label, prob) in decoded]}
