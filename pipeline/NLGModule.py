from data.response.response_template import intents_to_answer
import random

class NLGModule():
    def __init__(self):
        pass

    def convert_to_str(self, arr):
        sentence = ""

        for i in range(0, len(arr)):
            sentence += arr[i] 
            if i < len(arr) - 2:
                sentence += ", "
            if i == len(arr) - 2:
                sentence += "and "
        return sentence
    def process_movie_answer(self, intent_data, api_response):
        # assuming we have good api resposne

        intent = intent_data["intent"]
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

        if movie_title:
            plot_overview = api_response["overview"]
            rating = api_response["vote_average"]
            cast = [actor["original_name"] for actor in api_response["credits"]["cast"]][:5]
            director = [crew["original_name"] for crew in api_response["credits"]["crew"] if crew["job"] == "Director"][:5]
            recommendations = [movie["original_title"] for movie in api_response["recommendations"]["results"]][:5]

            cast_str = self.convert_to_str(cast)
            director_str = self.convert_to_str(director)
            recommendations_str = self.convert_to_str(recommendations)
            


            answer = intents_to_answer[intent]
            answer.format(movie_title=movie_title, plot_overview=plot_overview, rating=rating, cast_list=cast_str, movies_list=recommendations_str, directors=director_str)

        if genre:
            movies = [movie["original_title"] for movie in api_response["results"]][:5]

            movies_str = self.convert_to_str(movies)

            answer = intents_to_answer[intent]
            answer.format(genre=genre, movies_list=movies_str)
        
        if time_window:
            movies = [movie["original_title"] for movie in api_response["results"]][:5]

            movies_str = self.convert_to_str(movies)
            answer = intents_to_answer[intent]
            answer.format(time_window=time_window, movies_list=movies_str)
        return answer
    def process(self, intent_data, api_response, method="template"|"llm"):

        if api_response is None:
            return random.choice(intents_to_answer["api_error"])

        if "movie" in intent_data["intent"] and api_response is not None:
            return self.process_movie_answer(intent_data, api_response)
        if "weather" in intent_data["intent"] and api_response is not None:
            return 