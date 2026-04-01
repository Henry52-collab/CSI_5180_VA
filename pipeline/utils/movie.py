from dotenv import load_dotenv
import os
import requests

class MovieAPIModule():
    def __init__(self):
        load_dotenv()
        self.TMDB_API_KEY = os.getenv('TMDB_API_KEY')


    def get_movie_id(self, movie_title):

        params = {}
        params["api_key"] = self.TMDB_API_KEY
        params["query"] = movie_title

        headers = {"accept": "application/json"}
        url = "https://api.themoviedb.org/3/search/movie"

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            return None
        return response.json()["results"][0]["id"]
    
    def get_movie_details(self, movie_title):

        movie_id = self.get_movie_id(movie_title)

        if movie_id is None:
            return None 

        params = {}
        params["api_key"] = self.TMDB_API_KEY
        params["append_to_response"] = "credits,recommendations"

        headers = {"accept": "application/json"}
        url = f"https://api.themoviedb.org/3/movie/{movie_id}"

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            return None
        
        return response.json()

    def get_genre_id(self):

        params = {}
        params["api_key"] = self.TMDB_API_KEY
        headers = {"accept": "application/json"}
        url = "https://api.themoviedb.org/3/genre/movie/list"

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            return None 
        result = response.json()
        genre_to_id = {}

        for genre in result["genres"]:
            genre_to_id[genre["name"].lower()] = genre["id"]
        return genre_to_id

    def find_movie(self, genre):

        genre_to_id = self.get_genre_id()

        if genre.lower() not in genre_to_id:
                print("ERROR: Genre not found")
                return
            
        genre_id = genre_to_id[genre.lower()]

        params = {}
        params["api_key"] = self.TMDB_API_KEY

        params["with_genres"] = genre_id

        headers = {"accept": "application/json"}

        url = f"https://api.themoviedb.org/3/discover/movie"

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            return None
        
        return response.json()

    def get_trending_movie(self, time_window):

        params = {}
        params["api_key"] = self.TMDB_API_KEY

        headers = {"accept": "application/json"}

        if time_window.lower() != "day" and time_window.lower() != "week":
            return None
        url = f"https://api.themoviedb.org/3/trending/movie/{time_window.lower()}"
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            return None
        return response.json()
