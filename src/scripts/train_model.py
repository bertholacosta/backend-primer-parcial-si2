import os
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import joblib

def create_mock_data():
    """Crea datos ficticios de incidentes para entrenar el modelo inicial."""
    data = [
        {"tipo_averia": "motor", "clima": "lluvia", "distancia_km": 15, "gravedad": "Alta"},
        {"tipo_averia": "llanta", "clima": "despejado", "distancia_km": 2, "gravedad": "Baja"},
        {"tipo_averia": "choque", "clima": "lluvia", "distancia_km": 20, "gravedad": "Alta"},
        {"tipo_averia": "bateria", "clima": "despejado", "distancia_km": 5, "gravedad": "Baja"},
        {"tipo_averia": "frenos", "clima": "nublado", "distancia_km": 10, "gravedad": "Media"},
        {"tipo_averia": "choque", "clima": "despejado", "distancia_km": 30, "gravedad": "Alta"},
        {"tipo_averia": "llanta", "clima": "nublado", "distancia_km": 8, "gravedad": "Baja"},
        {"tipo_averia": "motor", "clima": "despejado", "distancia_km": 12, "gravedad": "Media"},
        {"tipo_averia": "frenos", "clima": "lluvia", "distancia_km": 25, "gravedad": "Alta"},
    ]
    return pd.DataFrame(data)

def train_and_save_model():
    print("Iniciando entrenamiento del modelo Random Forest...")
    df = create_mock_data()
    
    # Preprocesamiento (Convertir texto a números)
    # En producción, guardarías estos encoders también.
    le_averia = LabelEncoder()
    df['tipo_averia_enc'] = le_averia.fit_transform(df['tipo_averia'])
    
    le_clima = LabelEncoder()
    df['clima_enc'] = le_clima.fit_transform(df['clima'])
    
    X = df[['tipo_averia_enc', 'clima_enc', 'distancia_km']]
    y = df['gravedad']
    
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X, y)
    
    # Crear directorio para modelos si no existe
    os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'ml_models'), exist_ok=True)
    
    model_path = os.path.join(os.path.dirname(__file__), '..', 'ml_models', 'modelo_gravedad.joblib')
    encoders_path = os.path.join(os.path.dirname(__file__), '..', 'ml_models', 'encoders.joblib')
    
    joblib.dump(clf, model_path)
    joblib.dump({'averia': le_averia, 'clima': le_clima}, encoders_path)
    
    print(f"Modelo entrenado y guardado en {model_path}")

if __name__ == "__main__":
    train_and_save_model()
