"""
Fulfillment Module (Module 5)

Routes intents to the correct handler:
  - Movie queries → TMDB API
  - Weather queries → OpenWeatherMap API
  - Timer → parse duration
  - Pet actions → update PetState
  - Basic intents (greetings/goodbye/oos) → pass-through

Original movie/weather/timer code by Laura (abo).
Pet state + integration by Fengshou.
"""

from dotenv import load_dotenv
import os
from pytimeparse import parse as parse_duration

from pipeline.utils.weather import WeatherAPIModule
from pipeline.utils.movie import MovieAPIModule
import random
from typing import Any


# ============================================================================
# PetState — the only stateful part of the entire VA
# ============================================================================

def random_float(min_val = -0.25, max_val = 0.25):
    return 1 + random.uniform(min_val, max_val)


class PetState:
    def __init__(self):
        self.name = "Doro"
        self.hunger = 50
        self.happiness = 50
        self.energy = 50
        self.cleanliness = 50

    def apply(self, action, slots):
        random.seed()
        before = self.to_dict()

        if action == "feed_pet":
            self.hunger = min(100, self.hunger + 25 * random_float())
        elif action == "play_with_pet":
            self.happiness = min(100, self.happiness + 20 * random_float())
            self.energy = max(0, self.energy - 10 * random_float())
        elif action == "pet_the_cat":
            self.happiness = min(100, self.happiness + 10 * random_float())
        elif action == "wash_pet":
            self.cleanliness = min(100, self.cleanliness + 30 * random_float())
        elif action == "put_to_sleep":
            self.energy = min(100, self.energy + 30 * random_float())
        elif action == "wake_up_pet":
            self.energy = max(0, self.energy - 5 * random_float())
        elif action == "give_treat":
            self.happiness = min(100, self.happiness + 15 * random_float())
            self.hunger = min(100, self.hunger + 5 * random_float())
        elif action == "rename_pet":
            new_name = slots.get("name", self.name)
            old_name = self.name
            self.name = new_name
            return before, self.to_dict(), old_name

        return before, self.to_dict(), None

    def to_dict(self):
        return {
            "name": self.name,
            "hunger": round(self.hunger),
            "happiness": round(self.happiness),
            "energy": round(self.energy),
            "cleanliness": round(self.cleanliness),
        }


# ============================================================================
# FulfillmentModule
# ============================================================================

class FulfillmentModule:
    def __init__(self, pet_state=None):
        load_dotenv()
        self.weather_api = WeatherAPIModule()
        self.movie_api = MovieAPIModule()
        self.pet_state = pet_state or PetState()

    def process(self, intent_data):
        intent = intent_data.get("intent", "")
        slots = intent_data.get("slots", {})

        if intent in ("greetings", "goodbye", "oos"):
            return {"type": intent}

        if "movie" in intent:
            return self.process_movies(intent, slots)

        if intent == "weather":
            return self.process_weather(slots)

        if intent == "set_timer":
            return self.process_timer(slots)

        if intent in ("feed_pet", "play_with_pet", "pet_the_cat", "wash_pet",
                       "put_to_sleep", "wake_up_pet", "give_treat",
                       "check_status", "rename_pet"):
            return self.process_pet(intent, slots)

        return {"type": "oos"}

    # ------------------------------------------------------------------
    # Timer
    # ------------------------------------------------------------------
    def process_timer(self, slots):
        duration_str = slots.get("duration", "")
        seconds = -1
        try:
            seconds = parse_duration(duration_str) or -1
        except Exception:
            pass
        return {
            "type": "timer",
            "duration": seconds,
            "duration_str": duration_str,
        }

    # ------------------------------------------------------------------
    # Weather (by Laura; hardened with structured error handling)
    # ------------------------------------------------------------------
    def process_weather(self, slots):
        city = slots.get("city", "Ottawa")
        country = slots.get("country")

        result = self.weather_api.get_weather(city, country)

        # weather module now returns {"ok": bool, ...} with error metadata on failure
        if not result.get("ok"):
            return {
                "type": "weather",
                "city": result.get("city", city),
                "country": result.get("country", country),
                "error": result.get("error", "request_failed"),
                "message": result.get("message", "I couldn't get the weather right now."),
            }

        data = result.get("data", {})
        try:
            description = data["weather"][0]["description"]
            temperature = data["main"]["temp"]
            windspeed  = data["wind"]["speed"]
        except (KeyError, IndexError, TypeError):
            return {
                "type": "weather",
                "city": result.get("city", city),
                "country": result.get("country", country),
                "error": "invalid_response",
                "message": "The weather service returned incomplete data.",
            }

        return {
            "type": "weather",
            "city": result.get("city", city),
            "country": result.get("country", country),
            "description": description,
            "temperature": temperature,
            "windspeed": windspeed,
        }

    # ------------------------------------------------------------------
    # Movies (by Laura)
    # ------------------------------------------------------------------
    def process_movies(self, intent, slots):
        title = slots.get("title")
        genre = slots.get("genre")
        time_window = slots.get("time_window")

        response: dict[str, Any] = {"type": "movie"}

        if title:
            details = self.movie_api.get_movie_details(title)
            if details is None:
                return {"type": "movie", "error": f"Movie '{title}' not found"}

            response["title"] = title
            response["plot"] = details.get("overview", "")
            response["rating"] = details.get("vote_average", "N/A")
            response["cast"] = [
                a.get("name") or a.get("original_name", "")
                for a in details.get("credits", {}).get("cast", [])
            ][:5]
            response["director"] = [
                c.get("name") or c.get("original_name", "")
                for c in details.get("credits", {}).get("crew", [])
                if c.get("job") == "Director"
            ]
            response["similar"] = [
                m.get("title") or m.get("original_title", "")
                for m in details.get("recommendations", {}).get("results", [])
                if (m.get("title") or m.get("original_title", "")).isascii()
            ][:5]

        if genre:
            genre_results = self.movie_api.find_movie(genre)
            if genre_results:
                response["genre"] = genre
                response["movies"] = [
                    m.get("title") or m.get("original_title", "")
                    for m in genre_results.get("results", [])
                    if (m.get("title") or m.get("original_title", "")).isascii()
                ][:5]

        if time_window:
            trending = self.movie_api.get_trending_movie(time_window)
            if trending:
                response["movies"] = [
                    m.get("title") or m.get("original_title", "")
                    for m in trending.get("results", [])
                    if (m.get("title") or m.get("original_title", "")).isascii()
                ][:5]

        if intent == "get_upcoming_movies":
            upcoming = self.movie_api.get_upcoming_movies()
            if not upcoming:
                return {"type": "movie", "error": "Could not fetch upcoming movies"}
            response["movies"] = [
                m.get("title") or m.get("original_title", "")
                for m in upcoming.get("results", [])
                if (m.get("title") or m.get("original_title", "")).isascii()
            ][:5]

        if intent == "get_trending_movies" and "movies" not in response:
            trending = self.movie_api.get_trending_movie("day")
            if trending:
                response["movies"] = [
                    m.get("title") or m.get("original_title", "")
                    for m in trending.get("results", [])
                    if (m.get("title") or m.get("original_title", "")).isascii()
                ][:5]

        return response

    # ------------------------------------------------------------------
    # Pet (by Fengshou)
    # ------------------------------------------------------------------
    def process_pet(self, intent, slots):
        if intent == "check_status":
            return {
                "type": "pet",
                "action": intent,
                "pet_name": self.pet_state.name,
                "status": self.pet_state.to_dict(),
            }

        before, after, old_name = self.pet_state.apply(intent, slots)

        response = {
            "type": "pet",
            "action": intent,
            "pet_name": self.pet_state.name,
            "status": after,
            "before": before,
        }

        pet_name_lower = self.pet_state.name.lower()

        def _clean_slot(value, default):
            """If the slot value is just the pet's name (e.g. user said
            'feed Doro' and the model extracted 'doro' as food_type),
            treat it as absent and return the default."""
            if not value or value.strip().lower() == pet_name_lower:
                return default
            return value

        if intent == "feed_pet":
            response["food_type"] = _clean_slot(slots.get("food_type"), "food")
        elif intent == "play_with_pet":
            response["toy"] = _clean_slot(slots.get("toy"), "a toy")
        elif intent == "give_treat":
            response["treat_type"] = _clean_slot(slots.get("treat_type"), "a treat")
        elif intent == "rename_pet" and old_name:
            response["old_name"] = old_name
            response["new_name"] = self.pet_state.name

        return response
