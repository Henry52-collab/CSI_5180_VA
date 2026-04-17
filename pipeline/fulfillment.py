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
import re
import time
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
    # Natural decay (points per second). Tuned so changes are visible
    # over a few minutes of demo time without being hectic.
    DECAY_PER_SEC = {
        "hunger":      2 / 30,    # -2/min  (gets hungry)
        "happiness":   1 / 30,    # -1/min  (gets bored)
        "energy":      0.5 / 30,  # -0.5/min (slowly tired)
        "cleanliness": 1 / 30,    # -1/min  (slowly dirty)
    }

    # action -> (stat, "max"|"min", threshold). When violated, the
    # action is refused and a cap_warning is returned instead.
    CAP_RULES = {
        "feed_pet":      ("hunger",      "max", 95),
        "play_with_pet": ("energy",      "min",  5),
        "pet_the_cat":   ("happiness",   "max", 95),
        "wash_pet":      ("cleanliness", "max", 95),
        "put_to_sleep":  ("energy",      "max", 95),
        "wake_up_pet":   ("energy",      "min",  5),
        "give_treat":    ("happiness",   "max", 95),
    }

    def __init__(self, system_state=None):
        self.name = "Doro"
        self.hunger = 50
        self.happiness = 50
        self.energy = 50
        self.cleanliness = 50
        self.last_tick = time.time()
        self._system_state = system_state

    def _apply_decay(self):
        """Idempotent: decay all stats by elapsed seconds since last_tick.
        Only decays when the system is AWAKE — Doro sleeps when nobody is home."""
        now = time.time()
        if self._system_state and not self._system_state.get("awake"):
            self.last_tick = now
            return
        elapsed = now - self.last_tick
        if elapsed <= 0:
            return
        self.hunger      = max(0, self.hunger      - elapsed * self.DECAY_PER_SEC["hunger"])
        self.happiness   = max(0, self.happiness   - elapsed * self.DECAY_PER_SEC["happiness"])
        self.energy      = max(0, self.energy      - elapsed * self.DECAY_PER_SEC["energy"])
        self.cleanliness = max(0, self.cleanliness - elapsed * self.DECAY_PER_SEC["cleanliness"])
        self.last_tick = now

    def _check_cap(self, action):
        """Return None if action is allowed, else a cap_warning dict."""
        rule = self.CAP_RULES.get(action)
        if not rule:
            return None
        stat, direction, threshold = rule
        current = getattr(self, stat)
        if direction == "max" and current >= threshold:
            return {"stat": stat, "level": "max",
                    "current": round(current), "threshold": threshold}
        if direction == "min" and current <= threshold:
            return {"stat": stat, "level": "min",
                    "current": round(current), "threshold": threshold}
        return None

    def apply(self, action, slots):
        """Apply action. Returns (before, after, old_name, cap_warning)."""
        random.seed()
        self._apply_decay()
        before = self.to_dict()

        cap_warning = self._check_cap(action)
        if cap_warning:
            return before, before, None, cap_warning

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
            return before, self.to_dict(), old_name, None

        return before, self.to_dict(), None, None

    def to_dict(self):
        self._apply_decay()
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
            if intent != "rename_pet":
                wrong = self._check_pet_name(intent_data.get("transcript", ""))
                if wrong:
                    return {"type": "pet", "action": intent, "error": "wrong_name",
                            "pet_name": self.pet_state.name, "spoken_name": wrong}
            return self.process_pet(intent, slots)

        return {"type": "oos"}

    # ------------------------------------------------------------------
    # Pet name validation (keyword matching against ASR transcript)
    # ------------------------------------------------------------------
    _GENERIC_REFS = {"pet", "cat", "dog", "kitty", "doggy", "kitten", "puppy",
                     "it", "him", "her", "them", "the", "my", "our"}

    def _check_pet_name(self, transcript):
        """Return the wrong name if user addressed a different pet, else None."""
        m = re.search(
            r"(?:play with|feed|pet|wash|give .{0,15} to|put .{0,10} to sleep|"
            r"wake up|treat)\s+(?:the|my|a)?\s*([a-z]+)",
            transcript.lower(),
        )
        if not m:
            return None
        obj = m.group(1)
        pet_name = self.pet_state.name.lower()
        if obj == pet_name or obj in self._GENERIC_REFS:
            return None
        return obj

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

        before, after, old_name, cap_warning = self.pet_state.apply(intent, slots)

        response = {
            "type": "pet",
            "action": intent,
            "pet_name": self.pet_state.name,
            "status": after,
            "before": before,
        }

        if cap_warning:
            response["cap_warning"] = cap_warning
            return response

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
            response["toy"] = _clean_slot(slots.get("toy"), "toy")
        elif intent == "give_treat":
            response["treat_type"] = _clean_slot(slots.get("treat_type"), "treat")
        elif intent == "rename_pet" and old_name:
            response["old_name"] = old_name
            response["new_name"] = self.pet_state.name

        return response
