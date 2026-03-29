"""
Atlas VA — Intent Training Data (inline BIO annotation format)

Format: "word1 word2/B-SLOT word3/I-SLOT word4"
  - Words without a tag are automatically labeled "O" (outside)
  - B-SLOT = beginning of a slot span
  - I-SLOT = continuation of a slot span

Reused from Activity 2 where applicable. New intents marked with # NEW.
"""

# ===========================================================================
# BASIC INTENTS (reused from Activity 2)
# ===========================================================================

greetings_examples = [
    "hello",
    "hi",
    "hey",
    "good morning",
    "good evening",
    "hello there",
    "hi assistant",
    "hey there",
    "good afternoon",
    "hello assistant",
    "hi there",
    "hey assistant",
    "good day",
    "hello again",
    "hi again",
    "greetings",
    "howdy",
    "hey hey",
    "good to see you",
    "hello hello",
    "hi hi",
    "hey buddy",
    "hello friend",
    "hi friend",
    "morning",
    "evening",
    "yo",
    "nice to meet you",
    "hello how are you",
    "hey what is up",
]

goodbye_examples = [
    "bye",
    "goodbye",
    "see you",
    "talk to you later",
    "bye bye",
    "see you later",
    "good night",
    "catch you later",
    "farewell",
    "see you soon",
    "bye for now",
    "talk later",
    "have a good night",
    "goodbye assistant",
    "see you next time",
    "take care",
    "see you around",
    "have a nice day",
    "until next time",
    "later",
    "gotta go",
    "I am leaving",
    "have a good one",
    "peace",
    "goodbye for now",
    "so long",
    "until we meet again",
    "take it easy",
    "have a great day",
    "I will talk to you later",
]

oos_examples = [
    "open my email",
    "tell me a joke",
    "who is the president",
    "translate hello to french",
    "turn on the lights",
    "book a flight",
    "what time is it",
    "search for restaurants",
    "open youtube",
    "increase volume",
    "show my calendar",
    "what is machine learning",
    "what is the capital of france",
    "how tall is mount everest",
    "calculate 5 plus 3",
    "read me the news",
    "find a recipe for cookies",
    "how old is the earth",
    "send a text message",
    "navigate to the airport",
    "take a photo",
    "remind me to buy milk",
    "how do I tie a tie",
    "who invented the telephone",
    "show me the latest scores",
    "convert dollars to euros",
    "what is the meaning of life",
    "find the nearest gas station",
    "open the camera",
    "how many miles is a kilometer",
    # TODO (Task 3): Add ~20 more OOS examples relevant to our VA domain
    # e.g., things that sound movie/pet-related but are out of scope
]

# Adapted from Activity 2: removed /B-NAME tags (project timer has no name slot)
set_timer_examples = [
    "set a timer for 5/B-DURATION minutes/I-DURATION",
    "set timer for 10/B-DURATION minutes/I-DURATION",
    "start a timer for 30/B-DURATION seconds/I-DURATION",
    "start timer for 2/B-DURATION hours/I-DURATION",
    "set a timer for 45/B-DURATION minutes/I-DURATION",
    "timer for 15/B-DURATION minutes/I-DURATION",
    "set timer for 1/B-DURATION hour/I-DURATION",
    "start a timer for 20/B-DURATION minutes/I-DURATION",
    "please set a timer for 3/B-DURATION hours/I-DURATION",
    "set timer for 90/B-DURATION seconds/I-DURATION",
    "set a timer for 25/B-DURATION minutes/I-DURATION",
    "timer for 40/B-DURATION minutes/I-DURATION",
    "start timer for 50/B-DURATION seconds/I-DURATION",
    "set a timer for 6/B-DURATION hours/I-DURATION",
    "please start a timer for 12/B-DURATION minutes/I-DURATION",
    "set the potato timer for 2/B-DURATION minutes/I-DURATION",
    "start the egg timer for 5/B-DURATION minutes/I-DURATION",
    "set the pasta timer for 12/B-DURATION minutes/I-DURATION",
    "set a pizza timer for 15/B-DURATION minutes/I-DURATION",
    "start the laundry timer for 45/B-DURATION minutes/I-DURATION",
    "set the tea timer for 3/B-DURATION minutes/I-DURATION",
    "please set the chicken timer for 30/B-DURATION minutes/I-DURATION",
    "start a nap timer for 20/B-DURATION minutes/I-DURATION",
    "set the workout timer for 1/B-DURATION hour/I-DURATION",
    "set a cooking timer for 25/B-DURATION minutes/I-DURATION",
    "set the rice timer for 18/B-DURATION minutes/I-DURATION",
    "please start the study timer for 2/B-DURATION hours/I-DURATION",
    "start a baking timer for 40/B-DURATION minutes/I-DURATION",
    "set the coffee timer for 4/B-DURATION minutes/I-DURATION",
    "set the yoga timer for 10/B-DURATION minutes/I-DURATION",
]

# Adapted from Activity 2: removed /B-DAY /I-DAY tags (OpenWeatherMap = current weather only)
weather_examples = [
    "what is the weather",
    "is it cold outside",
    "do I need an umbrella",
    "is it going to rain",
    "how is the weather",
    "what is the weather in Ottawa/B-CITY",
    "is it going to snow in Toronto/B-CITY",
    "how is the weather in Tokyo/B-CITY",
    "what is the temperature in Paris/B-CITY",
    "check the weather for Montreal/B-CITY",
    "is it raining in Seattle/B-CITY",
    "check weather in Boston/B-CITY",
    "how cold is it in Moscow/B-CITY",
    "is it windy in San/B-CITY Francisco/I-CITY",
    "will it rain tomorrow",
    "is it sunny today",
    "what is the forecast for tomorrow",
    "will it snow next week",
    "will it be sunny on Friday",
    "how is the weather today",
    "what will the weather be next Monday",
    "will it rain in London/B-CITY",
    "weather in Vancouver/B-CITY",
    "forecast for Chicago/B-CITY",
    "will it rain in Miami/B-CITY",
    "temperature in Berlin/B-CITY",
    "what is the high in Denver/B-CITY",
    "will there be storms in Dallas/B-CITY",
    "weather forecast for New/B-CITY York/I-CITY",
    "is it snowing in Boston/B-CITY",
    "what is the temperature in London/B-CITY",
    "forecast for Tokyo/B-CITY",
]

# ===========================================================================
# MOVIE INTENTS (NEW — to be filled by Tasks 1, 2, 3)
# ===========================================================================

get_movie_cast_examples = [
    # TODO (Task 1): ~30 sentences with TITLE slot
    # "who is in Inception/B-TITLE"
    # "tell me the cast of The/B-TITLE Dark/I-TITLE Knight/I-TITLE"
]

get_similar_movies_examples = [
    # TODO (Task 1): ~30 sentences with TITLE slot
    # "recommend something like The/B-TITLE Matrix/I-TITLE"
]

get_movie_plot_examples = [
    # TODO (Task 1): ~30 sentences with TITLE slot
    # "what is Inception/B-TITLE about"
]

get_movies_by_genre_examples = [
    # TODO (Task 2): ~30 sentences with GENRE slot
    # "show me action/B-GENRE movies"
    # "I want to watch a science/B-GENRE fiction/I-GENRE film"
]

get_movie_rating_examples = [
    # TODO (Task 2): ~25 sentences with TITLE slot
    # "what is the rating of Inception/B-TITLE"
]

get_movie_director_examples = [
    # TODO (Task 2): ~25 sentences with TITLE slot
    # "who directed The/B-TITLE Dark/I-TITLE Knight/I-TITLE"
]

get_trending_movies_examples = [
    # TODO (Task 3): ~25 sentences with TIME_WINDOW slot
    # "what movies are trending this/B-TIME_WINDOW week/I-TIME_WINDOW"
]

get_upcoming_movies_examples = [
    # TODO (Task 3): ~20 sentences, no slots
    # "what new movies are coming out"
]

# ===========================================================================
# PET INTENTS (NEW — to be filled by Tasks 4, 5, 6)
# ===========================================================================

feed_pet_examples = [
    # TODO (Task 4): ~25 sentences with optional FOOD_TYPE slot
    # "feed the pet some fish/B-FOOD_TYPE"
    # "feed the pet"  (no slot is valid)
]

play_with_pet_examples = [
    # TODO (Task 4): ~25 sentences with optional TOY slot
    # "play with the pet using a ball/B-TOY"
]

pet_the_cat_examples = [
    # TODO (Task 4): ~20 sentences, no slots
    # "give the pet some cuddles"
]

wash_pet_examples = [
    # TODO (Task 5): ~20 sentences, no slots
    # "give the pet a bath"
]

put_to_sleep_examples = [
    # TODO (Task 5): ~20 sentences with optional DURATION slot
    # "put the pet to sleep for 2/B-DURATION hours/I-DURATION"
]

wake_up_pet_examples = [
    # TODO (Task 5): ~20 sentences, no slots
    # "wake the pet up"
]

give_treat_examples = [
    # TODO (Task 6): ~20 sentences with optional TREAT_TYPE slot
    # "give the pet a cookie/B-TREAT_TYPE"
]

check_status_examples = [
    # TODO (Task 6): ~20 sentences, no slots
    # "how is my pet doing"
]

rename_pet_examples = [
    # TODO (Task 6): ~20 sentences with NAME slot
    # "name the pet Mochi/B-NAME"
]

# ===========================================================================
# INTENT MAP — used by training script
# ===========================================================================

intent_map = {
    # Basic
    "greetings": greetings_examples,
    "goodbye": goodbye_examples,
    "oos": oos_examples,
    "set_timer": set_timer_examples,
    "weather": weather_examples,
    # Movie (specialized domain)
    "get_movie_cast": get_movie_cast_examples,
    "get_similar_movies": get_similar_movies_examples,
    "get_movie_plot": get_movie_plot_examples,
    "get_movies_by_genre": get_movies_by_genre_examples,
    "get_movie_rating": get_movie_rating_examples,
    "get_movie_director": get_movie_director_examples,
    "get_trending_movies": get_trending_movies_examples,
    "get_upcoming_movies": get_upcoming_movies_examples,
    # Pet (control system)
    "feed_pet": feed_pet_examples,
    "play_with_pet": play_with_pet_examples,
    "pet_the_cat": pet_the_cat_examples,
    "wash_pet": wash_pet_examples,
    "put_to_sleep": put_to_sleep_examples,
    "wake_up_pet": wake_up_pet_examples,
    "give_treat": give_treat_examples,
    "check_status": check_status_examples,
    "rename_pet": rename_pet_examples,
}


if __name__ == "__main__":
    total = 0
    for name, examples in intent_map.items():
        count = len(examples)
        status = "DONE" if count >= 20 else "TODO" if count == 0 else f"PARTIAL ({count})"
        print(f"  {name:.<30s} {count:>3d} examples  [{status}]")
        total += count
    print(f"\n  TOTAL: {total} examples")
