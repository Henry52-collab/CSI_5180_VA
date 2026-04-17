"""Weather API wrapper using OpenWeatherMap.

Two-step process:
  1. Geocode city name → (lat, lon) via /geo/1.0/direct
  2. Fetch current weather via /data/2.5/weather using coords

All methods return {"ok": True/False, ...} for uniform error handling.
"""

from dotenv import load_dotenv
import os
import requests


class WeatherAPIModule():
    def __init__(self):
        load_dotenv()
        self.OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')

    def _ok(self, **data):
        return {"ok": True, **data}

    def _error(self, error, message, **data):
        return {"ok": False, "error": error, "message": message, **data}

    def get_coordinates(self, city, country=None):
        """Geocode a city name to (lat, lon). Returns top match from OpenWeatherMap."""
        if not self.OPENWEATHER_API_KEY:
            return self._error(
                "missing_api_key",
                "Weather service is not configured.",
                city=city,
                country=country,
            )

        q = f"{city}"
        if country is not None:
            q += f",{country}"

        params = {
            "appid": self.OPENWEATHER_API_KEY,
            "q": q,
            "limit": 1,
        }
        headers = {"accept": "application/json"}
        url = "https://api.openweathermap.org/geo/1.0/direct"

        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
        except requests.RequestException:
            return self._error(
                "request_failed",
                "I couldn't reach the weather service right now.",
                city=city,
                country=country,
            )

        if response.status_code != 200:
            return self._error(
                "service_error",
                "The weather service returned an unexpected response.",
                city=city,
                country=country,
                status_code=response.status_code,
            )

        try:
            result = response.json()
        except ValueError:
            return self._error(
                "invalid_response",
                "The weather service returned unreadable data.",
                city=city,
                country=country,
            )

        if not result:
            return self._error(
                "city_not_found",
                f"I couldn't find weather data for {city}.",
                city=city,
                country=country,
            )

        location = result[0]
        lat = location.get("lat")
        lon = location.get("lon")
        if lat is None or lon is None:
            return self._error(
                "invalid_response",
                "The weather service did not return valid coordinates.",
                city=city,
                country=country,
            )

        return self._ok(
            lat=lat,
            lon=lon,
            city=location.get("name", city),
            country=location.get("country", country),
        )

    def get_weather(self, city, country=None):
        """Full pipeline: geocode city → fetch weather. Returns metric units (°C, m/s)."""
        coords = self.get_coordinates(city, country)
        if not coords.get("ok"):
            return coords

        params = {
            "appid": self.OPENWEATHER_API_KEY,
            "lat": coords["lat"],
            "lon": coords["lon"],
            "units": "metric",
        }
        headers = {"accept": "application/json"}
        url = "https://api.openweathermap.org/data/2.5/weather"

        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
        except requests.RequestException:
            return self._error(
                "request_failed",
                "I couldn't reach the weather service right now.",
                city=coords.get("city", city),
                country=coords.get("country", country),
            )

        if response.status_code != 200:
            return self._error(
                "service_error",
                "The weather service returned an unexpected response.",
                city=coords.get("city", city),
                country=coords.get("country", country),
                status_code=response.status_code,
            )

        try:
            result = response.json()
        except ValueError:
            return self._error(
                "invalid_response",
                "The weather service returned unreadable data.",
                city=coords.get("city", city),
                country=coords.get("country", country),
            )

        return self._ok(
            city=coords.get("city", city),
            country=coords.get("country", country),
            data=result,
        )
