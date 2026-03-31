from dotenv import load_dotenv
import os
import requests
import json
import pprint

class FulfillmentModule():
    def __init__(self):
        load_dotenv()
        TMDB_API_KEY = os.getenv('TMDB_API_KEY')
    
    
    
    def process(self, intent_data):
        if "movie" in intent_data["intent"].lower():
            self.process_movies(intent_data)
    
    def get_movie_id(self, params, headers):
        url = "https://api.themoviedb.org/3/search/movie"

        response = requests.get(url, headers=headers, params=params)
        return response.json()["results"][0]["id"]
    
    def get_movie_details(self, movie_id, params, headers):
        url = f"https://api.themoviedb.org/3/movie/{movie_id}"

        response = requests.get(url, headers=headers, params=params)
        return response.json()

    def find_movie(self, params, headers):
        url = f"https://api.themoviedb.org/3/discover/movie"

        response = requests.get(url, headers=headers, params=params)
        return response.json()

    def get_trending_movie(self, time_window, params, headers):
        url = f"https://api.themoviedb.org/3/trending/movie/{time_window}"
        response = requests.get(url, headers=headers, params=params)
        return response.json()
    def get_genre_id(self, params, headers):
        url = "https://api.themoviedb.org/3/genre/movie/list"

        response = requests.get(url, headers=headers, params=params)
        result = response.json()
        genre_to_id = {}

        for genre in result["genres"]:
            genre_to_id[genre["name"].lower()] = genre["id"]
        return genre_to_id
    
    def process_movies(self, intent_data):
        # get movie cast (title)
        # get similar movies (title)
        # get movie plot (title)
        # get / find movie by genre (genre)
        # get movie ratings (title)
        # get movie director (title)
        # get trending movies (time window)
        # get upcoming movies (no slot)

        slots = intent_data["slots"]
        movie_title = None
        genre = None
        time_window = None

        if "title" in slots:
            movie_title = slots["title"]

        if "genre" in slots:
            genre = slots["genre"]

        if "time_window" in slots:
            time_window = slots["time_window"]
        
        # Stuff by title
        # - get movie cast - movie credits - cast
        # - get similar movies - movies - recommendations
        # - get movie plot - movie details overview
        # - get movie ratings
        # - get movie director
        if movie_title:
            params = {}
            params["api_key"] = TMDB_API_KEY
            params["query"] = movie_title

            headers = {"accept": "application/json"}

            movie_id = self.get_movie_id(params, headers)
            del params["query"]
            params["append_to_response"] = "credits,recommendations"

            result = self.get_movie_details(movie_id, params, headers)

            overview = result['overview']
            ratings = result['vote_average']
            cast = [actor['original_name'] for actor in result['credits']['cast']][:5]
            director = [crew['original_name'] for crew in result['credits']['crew'] if crew['job'] == 'Director'][:5]
            recommendations = [movie['original_title'] for movie in result['recommendations']['results']][:5]




        # Stuff by genre
        if genre:
            params = {}
            params["api_key"] = TMDB_API_KEY

            headers = {"accept": "application/json"}
            genre_to_id = self.get_genre_id(params, headers)

            if genre.lower() not in genre_to_id:
                print("ERROR: Genre not found")
                return
            
            genre_id = genre_to_id[genre.lower()]

            params["with_genres"] = genre_id

            result = self.find_movie(params, headers)

            movies = [movie['original_title'] for movie in result['results']][:5]
            print(movies)

        # Stuff by tiem window
        if time_window:
            params = {}
            params["api_key"] = TMDB_API_KEY
            headers = {"accept": "application/json"}

            if time_window.lower() != "day" and time_window.lower() != "week":
                return
            time_window = time_window.lower()

            result = self.get_trending_movie(time_window, params, headers)


            movies = [movie['original_title'] for movie in result['results']][:5]

            print(movies)

load_dotenv()
TMDB_API_KEY = os.getenv('TMDB_API_KEY')

fulfillment = FulfillmentModule()

fulfillment.process_movies({"intent": "blah", "slots": {"time_window": "day"}})


# def get_movie_credits(movie_id, params, headers):
#     url = f"https://api.themoviedb.org/3/movie/{movie_id}/credits"

#     response = requests.get(url, params=params, headers=headers)
#     pprint.pprint(response.json()["cast"])

# def get_movie_details(movie_id, params, headers):
#     url = f"https://api.themoviedb.org/3/movie/{movie_id}"

#     response = requests.get(url, params=params, headers=headers)

# params = {}
# params["api_key"] = TMDB_API_KEY
# params["query"] = "Spiderman"

# url = "https://api.themoviedb.org/3/search/movie"


# response = requests.get(url, headers=headers, params=params)

# results = response.json()["results"][0]

# movie_id = get_movie_id(params, headers)

# get_movie_credits(movie_id, params, headers)