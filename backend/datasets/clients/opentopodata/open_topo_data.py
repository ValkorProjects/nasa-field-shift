import requests

# Returns the elevations (meters relative to sea level) of the given
# (latitude, longitude) points, in the same order, using ONE batched request
# (the public API is rate limited to ~1 request/second).
# An entry is None when the dataset has no value for that point.
# Returns None if the request fails.
def get_topoData(points : list[tuple[float, float]]) -> list[float | None] | None:
    #Serving NASA SRTM with 30m height
    #https://api.opentopodata.org/v1/srtm30m?locations=lat,lng|lat,lng
    locations = "|".join(f"{lat},{lng}" for lat, lng in points)
    try:
        response = requests.get(f"https://api.opentopodata.org/v1/srtm30m?locations={locations}", timeout=10)
        if response.status_code == 200:
            return [r["elevation"] for r in response.json()["results"]]
        else:
            print(f"Erro na requisição. Status Code: {response.status_code} - {response.text[:300]}")
    except Exception as e:
        print(f"Ocorreu um erro: {e}")
    return None
