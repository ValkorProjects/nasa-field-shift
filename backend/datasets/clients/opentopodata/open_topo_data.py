from datetime import datetime
import requests

def get_topoData(latitude : float, longitude : float) -> dict[str, any]:
    #Serving NASA SRTM with 30m height
    #https://api.opentopodata.org/v1/srtm30m?locations=
    try:
        response = requests.get(f"https://api.opentopodata.org/v1/srtm30m?locations={latitude},{longitude}", timeout=30)
        if response.status_code == 200:
            dados_dict = response.json()
            return dados_dict["elevation"]
        else:
            print(f"Erro na requisição. Status Code: {response.status_code} - {response.text[:300]}")
    except Exception as e:
        print(f"Ocorreu um erro: {e}")