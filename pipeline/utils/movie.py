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
        url = "https://api.themoviedb.org/3/search/movie"
        response = requests.get(url, params=self._params(query=movie_title))

        if response.status_code != 200:
            return None
        results = response.json().get("results", [])
        if not results:
            return None
        return results[0]["id"]

    def get_movie_details(self, movie_title):
        movie_id = self.get_movie_id(movie_title)
        if movie_id is None:
            return None

        url = f"https://api.themoviedb.org/3/movie/{movie_id}"
        response = requests.get(url, params=self._params(append_to_response="credits,recommendations"))

        if response.status_code != 200:
            return None
        return response.json()

    def get_genre_id(self):
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
        if time_window.lower() not in ("day", "week"):
            return None
        url = f"https://api.themoviedb.org/3/trending/movie/{time_window.lower()}"
        response = requests.get(url, params=self._params())

        if response.status_code != 200:
            return None
        return response.json()

    def get_upcoming_movies(self):
        url = "https://api.themoviedb.org/3/movie/upcoming"
        response = requests.get(url, params=self._params())

        if response.status_code != 200:
            return None
        return response.json()
