greetings_answer = [
    "Hello!",
    "Hey!",
    "Hey there!"
]

goodbye_answer = [
    "Bye!",
    "See you later!",
    "Goodbye!"
]

oos_answer = [
    "Sorry, this is out of my capabilities.",
    "Sorry, I didn't quite get that.",
    "I don't understand that"
]

set_timer_answer = [
    "Setting timer for {seconds}",
    "Got it. Timer started for {seconds}",
    "Counting down from {seconds}"
]

# MAY CHANGE
weather_answer = [
    "The weather is {weather}",
    "It is {weather} now",
    "Sure! It's currently {weather}"
]

get_movie_plot_answer = [
    "{movie_title} follows {plot_overview}",
    "Great choice! Here's a quick rundown of {movie_title}: {plot_overview}",
    "Here's the plot for {movie_title}: {plot_overview}"
]

get_movie_cast_answer = [
    "The cast of '{movie_title}' includes {cast_list}",
    "Here's who stars in '{movie_title}': {cast_list}",
    "'{movie_title}' features the following cast: {cast_list}"
]

get_similar_movies_answer = [
    "If you enjoyed '{movie_title}', you might also like: {similar_movies}",
    "Here are some movies similar to '{movie_title}': {similar_movies}",
    "Based on '{movie_title}', we recommend: {similar_movies}"
]

get_movies_by_genre_answer = [
    "Here are some great {genre} movies you might enjoy: {movies_list}",
    "Looking for {genre} films? Check these out: {movies_list}",
    "Top picks in the {genre} genre: {movies_list}"
]

get_movie_rating_answer = [
    "'{movie_title}' has a rating of {rating}",
    "Here's the rating for '{movie_title}': {rating}",
    "'{movie_title}' scored {rating} from viewers and critics"
]

get_movie_director_answer = [
    "'{movie_title}' was directed by {directors}",
    "The director(s) of '{movie_title}': {directors}",
    "'{movie_title}' was brought to life by director(s) {directors}"
]

get_trending_movies_answer = [
    "Here are the trending movies for {time_window}: {movies_list}",
    "These are the hottest movies this {time_window}: {movies_list}",
    "Top trending movies for {time_window}: {movies_list}"
]

get_upcoming_movies_answer = [
    "Here are the upcoming movies to look out for: {movies_list}",
    "Get excited! These movies are coming soon: {movies_list}",
    "Here's what's hitting theaters soon: {movies_list}"
]

api_error_answer = [
    "It seems like I could not complete your request. Please try again later.",
    "Something went wrong with the API. Try again later.",
    "Hmm, I don't know why I can answer this right now. Try again later."
]

missing_data_answer = [
    "It seems like you're missing some things in your query.",
    "I couldn't complete the request because you're missing data.",
    "I'm missing some data. Please ask again."
]

intents_to_answer = {
    "greetings": greetings_answer,
    "goodbye": goodbye_answer,
    "oos": oos_answer,
    "set_timer": set_timer_answer,
    "weather": weather_answer,
    # Movie (specialized domain)
    "get_movie_cast": get_movie_cast_answer,
    "get_similar_movies": get_similar_movies_answer,
    "get_movie_plot": get_movie_plot_answer,
    "get_movies_by_genre": get_movies_by_genre_answer,
    "get_movie_rating": get_movie_rating_answer,
    "get_movie_director": get_movie_director_answer,
    "get_trending_movies": get_trending_movies_answer,
    "get_upcoming_movies": get_upcoming_movies_answer,
    "api_error": api_error_answer,
    "missing_data": missing_data_answer
}