import requests
from src import ai_service

def probar_gemini():
    print("--- PRUEBA 1: API DE GEMINI (IA Generativa) ---")
    descripcion_prueba = "El conductor reporta un choque frontal contra un poste a 80km/h. El cofre está destruido y hay líquido derramado en el piso."
    print(f"Enviando descripción a Gemini:\n '{descripcion_prueba}'\n")
    
    try:
        resultado = ai_service.analizar_evidencia_visual(descripcion=descripcion_prueba)
        print(" RESPUESTA DE GEMINI:")
        print("=======================================")
        print(resultado)
        print("=======================================\n")
    except Exception as e:
        print(f" Error con Gemini: {str(e)}\n")

def probar_random_forest():
    print("--- PRUEBA 2: RANDOM FOREST CLASSIFIER (Machine Learning) ---")
    payload = {
        "tipo_averia": "motor",
        "clima": "lluvia",
        "distancia_km": 15
    }
    print(f"Enviando JSON al endpoint FastAPI: {payload}\n")
    
    try:
        response = requests.post("http://localhost:8000/ia/clasificar-gravedad", json=payload)
        if response.status_code == 200:
            print(" RESPUESTA DE FASTAPI (Random Forest):")
            print("=======================================")
            print(response.json())
            print("=======================================\n")
        else:
            print(f" Error HTTP {response.status_code}: {response.text}\n")
    except Exception as e:
        print(f" Error de conexión con FastAPI: {str(e)}\n")

if __name__ == "__main__":
    probar_gemini()
    probar_random_forest()
