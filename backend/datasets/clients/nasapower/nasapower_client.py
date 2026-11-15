# This script implements NASAPOWER API interfacing
# Allows the extraction of the following data:
# - Temperature at 2 meters
# - Humidity at 2 meters
# - Wind speed at 10 meters
# - Heating Degree Days Below 18.3 °C
# - Cooling Degree Days Above 10 °C

# TEMPORARY: ENDPOINTS
# Simple point
# /api/projection/daily/point?parameters=T2M&community=SB&longitude=-104.99&latitude=39.74&start=20500101&end=20501231&format=JSON&time-standard=UTC

# Daily plot
# /api/projection/daily/plot?parameters=T2M&community=SB&longitude=-104.99&latitude=39.74&start=20500101&end=20501231&format=JSON&time-standard=UTC
from .nasapower_typedef import Plot
from datetime import datetime
import requests

class Parameters:
    T2M                 = "T2M"                     # Temperature at 2 Meters
    T2M_MAX             = "T2M_MAX"                 # Temperature at 2 Meters Maximum
    T2M_MIN             = "T2M_MIN"                 # Temperature at 2 Meters Minimum
    RH2M                = "RH2M"                    # Relative Humidity at 2 Meters
    QV2M                = "QV2M"                    # Specific Humidity at 2 Meters
    PRECTOTCORR         = "PRECTOTCORR"             # Precipitation Corrected
    WS10M               = "WS10M"                   # Wind Speed at 10 Meters
    ALLSKY_SFC_SW_DWN   = "ALLSKY_SFC_SW_DWN"       # All Sky Surface Shortwave Downward Irradiance 	
    ALLSKY_SFC_LW_DWN   = "ALLSKY_SFC_LW_DWN"       # All Sky Surface Longwave Downward Irradiance 	
    HDD18_3             = "HDD18_3"                 # Heating Degree Days Below 18.3 °C
    CDD10               = "CDD10"                   # Cooling Degree Days Above 10 °C

def get_simplePoint(
        parameter : str,
        longitude : float, 
        latitude : float, 
        year_start : int = 2050,
        year_end : int = 2050, 
        month_start : int = 1,
        month_end : int = 12,
        day_start : int = 1,
        day_end : int = 31
        ) -> Plot:

    date_start_formatted = datetime(year_start, month_start, day_start).strftime("%Y%m%d")
    date_end_formatted = datetime(year_end, month_end, day_end).strftime("%Y%m%d")

    try:
        response = requests.get(f"https://power.larc.nasa.gov/api/projection/daily/point?parameters={parameter}&community=SB&longitude={longitude}&latitude={latitude}&start={date_start_formatted}&end={date_end_formatted}&format=JSON&time-standard=UTC")
        if response.status_code == 200:
        
            dados_dict = response.json()
            plot = Plot.from_dict(dados_dict)
        
            print("Tipo do objeto:", type(dados_dict))
            print("Conteúdo do dicionário:", dados_dict)
            print("Acessando uma chave específica (Título):", dados_dict.get("title"))
            return plot
        else:
            print(f"Erro na requisição. Status Code: {response.status_code}")
    except  requests.exceptions.RequestException as e:
        print(f"Ocorreu um erro: {e}")

def get_dailyPlot(
        parameter : str,
        longitude : float, 
        latitude : float, 
        year_start : int = 2050,
        year_end : int = 2050, 
        month_start : int = 1,
        month_end : int = 12,
        day_start : int = 1,
        day_end : int = 31
        ) -> Plot:

    date_start_formatted = datetime(year_start, month_start, day_start).strftime("%Y%m%d")
    date_end_formatted = datetime(year_end, month_end, day_end).strftime("%Y%m%d")

    try:
        response = requests.get(f"https://power.larc.nasa.gov/api/projection/daily/plot?parameters={parameter}&community=SB&longitude={latitude}&latitude={longitude}&start={date_start_formatted}&end={date_end_formatted}&format=JSON&time-standard=UTC")
        if response.status_code == 200:
        
            dados_dict = response.json()
            plot = Plot.from_dict(dados_dict)
        
            print("Tipo do objeto:", type(dados_dict))
            print("Conteúdo do dicionário:", dados_dict)
            print("Acessando uma chave específica (Título):", dados_dict.get("title"))
            return plot
        else:
            print(f"Erro na requisição. Status Code: {response.status_code}")
    except  requests.exceptions.RequestException as e:
        print(f"Ocorreu um erro: {e}")
