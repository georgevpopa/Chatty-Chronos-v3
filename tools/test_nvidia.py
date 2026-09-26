import os
import httpx
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("NVIDIA_API_KEY")
if not API_KEY:
    print("Eroare: Nu ai NVIDIA_API_KEY in fisierul .env")
    exit(1)

CATALOG_URL = "https://integrate.api.nvidia.com/v1/models"
CHAT_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

print("Descarc catalogul brut de la NVIDIA...")
try:
    with httpx.Client(timeout=15) as client:
        resp = client.get(CATALOG_URL, headers=headers)
        resp.raise_for_status()
        all_models = [m["id"] for m in resp.json().get("data", [])]
except Exception as e:
    print(f"Eroare la descarcarea catalogului: {e}")
    exit(1)

print(f"Am gasit {len(all_models)} modele in total. Incep validarea pentru /chat/completions...\n")

valid_chat_models = []

with httpx.Client(timeout=10) as client:
    for model_id in all_models:
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 5
        }
        
        try:
            res = client.post(CHAT_URL, json=payload, headers=headers)
            if res.status_code == 200:
                print(f"[ OK ] {model_id}")
                valid_chat_models.append(model_id)
            else:
                print(f"[FAIL] {model_id} (Status: {res.status_code})")
        except Exception as e:
            print(f"[ ERR] {model_id} a picat la request.")

print("\nValidare completa! Acestea sunt modelele pe care le poti folosi in aplicatie:")
for v in valid_chat_models:
    print(v)