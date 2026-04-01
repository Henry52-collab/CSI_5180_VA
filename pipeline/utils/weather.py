from dotenv import load_dotenv
import os
import requests


class WeatherAPIModule():
    def __init__(self):
        load_dotenv()
        self.OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')

    def get_coordinates(self, city, country=None):
        q = f"{city}"

        if country is not None:
            q += f",{country}"

        params = {}
        params["appid"] = self.OPENWEATHER_API_KEY
        params["q"] = q
        params["limit"] = 1

        headers = {"accept": "application/json"}
        url = f"http://api.openweathermap.org/geo/1.0/direct"

        response = requests.get(url, params=params, headers=headers)

        if response.status_code != 200:
            return None
        result = response.json()
        lat = result[0]['lat']
        lon = result[0]['lon']
        return (lat, lon)
    
    def get_weather(self, city, country=None):

        lat, lon = self.get_coordinates(city, country)
        params = {}
        params["appid"] = self.OPENWEATHER_API_KEY
        params["lat"] = lat
        params["lon"] = lon
        headers = {"accept": "application/json"}
        url = f"http://api.openweathermap.org/data/2.5/weather"

        response = requests.get(url, params=params, headers=headers)

        if response.status_code != 200:
            return None
        result = response.json()

        return result["weather"][0]


