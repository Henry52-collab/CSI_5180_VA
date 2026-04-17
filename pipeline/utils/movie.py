"""Movie API wrapper using TMDB (The Movie Database).

Provides methods for searching movies, fetching details (with credits
and recommendations appended), discovering by genre, and getting
trending/upcoming lists. All responses are raw TMDB JSON.
"""

from dotenv import load_dotenv
import os
import requests


class MovieAPIModule():
    def __init__(self):
        load_dotenv()
        self.TMDB_API_KEY = os.getenv('TMDB_API_KEY')

    def _params(self, **extra):
        p = {"api_key": self.TMDB_API_KEY}
        p.update(extra)
        return p

    def get_movie_id(self, movie_title):
        """Search TMDB by title and return the ID of the top result."""
        url = "https://api.themoviedb.org/3/search/movie"
        response = requests.get(url, params=self._params(query=movie_title))

        if response.status_code != 200:
            return None
        results = response.json().get("results", [])
        if not results:
            return None
        return results[0]["id"]

    def get_movie_details(self, movie_title):
        """Fetch full movie details including credits and recommendations."""
        movie_id = self.get_movie_id(movie_title)
        if movie_id is None:
            return None

        url = f"https://api.themoviedb.org/3/movie/{movie_id}"
        response = requests.get(url, params=self._params(append_to_response="credits,recommendations"))

        if response.status_code != 200:
            return None
        return response.json()

    def get_genre_id(self):
        """Fetch TMDB genre list and return {genre_name_lower: genre_id} mapping."""
        url = "https://api.themoviedb.org/3/genre/movie/list"
        response = requests.get(url, params=self._params())

        if response.status_code != 200:
            return None
        result = response.json()
        genre_to_id = {}
        for genre in result["genres"]:
            genre_to_id[genre["name"].lower()] = genre["id"]
        return genre_to_id

    def find_movie(self, genre):
        """Discover movies filtered by genre name (e.g. "action", "comedy")."""
        genre_to_id = self.get_genre_id()
        if not genre_to_id or genre.lower() not in genre_to_id:
            return None

        genre_id = genre_to_id[genre.lower()]
        url = "https://api.themoviedb.org/3/discover/movie"
        response = requests.get(url, params=self._params(with_genres=genre_id))

        if response.status_code != 200:
            return None
        return response.json()

    def get_trending_movie(self, time_window):
        """Get trending movies for a time window ("day" or "week")."""
        if time_window.lower() not in ("day", "week"):
            return None
        url = f"https://api.themoviedb.org/3/trending/movie/{time_window.lower()}"
        response = requests.get(url, params=self._params())

        if response.status_code != 200:
            return None
        return response.json()

    def get_upcoming_movies(self):
        """Get list of upcoming movie releases."""
        url = "https://api.themoviedb.org/3/movie/upcoming"
        response = requests.get(url, params=self._params())

        if response.status_code != 200:
            return None
        return response.json()
