from flask import Flask
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array
from PIL import Image
import numpy as np
import os
import gradio as gr
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

app = Flask(__name__)

# Ruta al archivo del modelo desde variables de entorno
model_path = os.getenv('MODEL_PATH')
model = load_model(model_path)

# Ruta al archivo de etiquetas desde variables de entorno
labels_file_path = os.getenv('LABELS_FILE_PATH')

def load_labels(file_path):
    """Carga las etiquetas desde un archivo de texto."""
    with open(file_path, 'r') as f:
        return [line.strip() for line in f.readlines()]

# Cargar etiquetas desde el archivo
labels = load_labels(labels_file_path)

# Verificar número de etiquetas
print(f"Number of labels: {len(labels)}")

# Verificar el número de salidas del modelo
num_outputs = model.output_shape[1]
print(f"Number of model outputs: {num_outputs}")

# Asegurarse de que el número de etiquetas y salidas del modelo coinciden
if len(labels) != num_outputs:
    raise ValueError(f"El número de etiquetas ({len(labels)}) no coincide con el número de salidas del modelo ({num_outputs})")

# Tamaño de imagen
image_size = (224, 224)  # Tamaño al que quieres reescalar las imágenes

# Carpeta para guardar imágenes subidas
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def prepare_image(image, target_size):
    """Prepara la imagen para la predicción del modelo."""
    if image.mode != "RGB":
        image = image.convert("RGB")
    image = image.resize(target_size)
    image = img_to_array(image)
    image = np.expand_dims(image, axis=0)
    return image

def clean_predictions(preds):
    """Limpia las predicciones reemplazando NaN con 0 y normaliza."""
    preds = np.nan_to_num(preds)  # Reemplaza NaN con 0
    total = np.sum(preds)
    if total > 0:
        preds = preds / total  # Normaliza las predicciones
    return preds

def convert_predictions_to_grams(preds, labels, total_weight=1000, min_grams_threshold=50):
    """Convierte las predicciones del modelo en gramos y filtra las menos relevantes."""
    preds = clean_predictions(preds)
    total_prob = np.sum(preds)
    if total_prob > 0:
        preds = preds / total_prob * total_weight  # Convertir a gramos

    # Filtrar categorías con valores significativos
    filtered_predictions = {labels[i]: round(float(preds[i]), 2) for i in range(len(preds)) if preds[i] >= min_grams_threshold}
    
    return filtered_predictions

def predict(image):
    """Realiza una predicción sobre la imagen proporcionada."""
    try:
        # Preparar la imagen para la predicción
        image = prepare_image(image, target_size=image_size)
        
        # Realizar la predicción
        preds = model.predict(image)[0]
        print(f"Raw predictions: {preds}")  # Depuración

        # Convertir las predicciones a gramos y filtrar las menos relevantes
        predictions_in_grams = convert_predictions_to_grams(preds, labels)
        print(f"Filtered predictions: {predictions_in_grams}")  # Depuración
        
        return predictions_in_grams

    except Exception as e:
        print(f"Error occurred: {str(e)}")  # Depuración
        return {'error': str(e)}

# Crear interfaz de Gradio
iface = gr.Interface(fn=predict, inputs=gr.Image(type="pil"), outputs=gr.JSON())

if __name__ == '__main__':
    iface.launch(share=True)
    app.run(debug=True, host='0.0.0.0', port=5000)
