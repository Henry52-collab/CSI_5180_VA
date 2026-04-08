from dotenv import load_dotenv
import os
import requests
import json
import pprint
from pytimeparse import parse

from utils.weather import WeatherAPIModule
from utils.movie import MovieAPIModule

class FulfillmentModule():
    def __init__(self):
        
        self.weather_api = WeatherAPIModule()
        self.movie_api = MovieAPIModule()

        load_dotenv()
        TMDB_API_KEY = os.getenv('TMDB_API_KEY')
    
    
    def process(self, intent_data):
        if "movie" in intent_data["intent"].lower():
            self.process_movies(intent_data)
        if "weather" in intent_data["intent"].lower():
            self.process_weather(intent_data)
        if "timer" in intent_data["intent"].lower():
            self.process_timer(intent_data)

    def process_timer(self, intent_data):
        duration = intent_data["slots"]["duration"]
        seconds = -1
        intent_response = {}
        intent_response["type"] = "timer"
        try:
            seconds = parse(duration)
        except:
            pass
        intent_response["duration"] = seconds
        return intent_response
    
    
    def process_weather(self, intent_data):
        city = intent_data["slots"]["city"]
        country = None

        if "country" in intent_data["slots"]:
            country = intent_data["slots"]["country"]

        
        intent_response = {}
        intent_response["type"] = "weather"
        result = self.weather_api.get_weather(city, country)

        if result is None:
            return None # Error
        
        intent_response["description"] = result["weather"][0]["description"]
        intent_response["current_temp"] = result["main"]["temp"]
        intent_response["feels_like"] = result["main"]["feels_like"]

        # intent_response["description"] = result["description"]
        return intent_response
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

        intent_response = {}

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

            result = self.movie_api.get_movie_details(movie_title)

            if result is None:
                return None 

            # overview = result['overview']
            # ratings = result['vote_average']
            # cast = [actor['original_name'] for actor in result['credits']['cast']][:5]
            # director = [crew['original_name'] for crew in result['credits']['crew'] if crew['job'] == 'Director'][:5]
            # recommendations = [movie['original_title'] for movie in result['recommendations']['results']][:5]

            # print(overview)

            intent_response["type"] = "movie_title"

            intent_response["plot_overview"] = result["overview"]
            intent_response["ratings"] = result["vote_average"]
            intent_response["cast"] = [actor['original_name'] for actor in result['credits']['cast']][:5]
            intent_response["director"] = [crew['original_name'] for crew in result['credits']['crew'] if crew['job'] == 'Director'][:5]
            intent_response["recommendations"] = [movie['original_title'] for movie in result['recommendations']['results']][:5]

        # Stuff by genre
        if genre:
            
            result = self.movie_api.find_movie(genre)

            if result is None:
                return None 

            intent_response["type"] = "movie_genre"

            intent_response["movies"] = [movie['original_title'] for movie in result['results']][:5]

            # movies = [movie['original_title'] for movie in result['results']][:5]
            # print(movies)

        # Stuff by tiem window
        if time_window:
            result = self.movie_api.get_trending_movie(time_window)

            if result is None:
                return None

            intent_response["type"] = "movie_time_window"
            intent_response["movies"] = [movie['original_title'] for movie in result['results']][:5]


            # movies = [movie['original_title'] for movie in result['results']][:5]

            # print(movies)
        return intent_response


# fulfillment = FulfillmentModule()

# response = fulfillment.process_weather({"intent": "blah", "slots": {"city": "Beijing"}})
# print(response)


