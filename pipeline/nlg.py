"""
Answer Generation Module (Module 6)

Transforms fulfillment results (JSON) into natural language responses.
Supports two methods:
    - "template": rule-based templates with random variety
    - "llm": prompt-based generation using a HuggingFace decoder model

Pipeline interface:
    process(intent_data, api_response, method="template") → str
"""

import random

# ---------------------------------------------------------------------------
# Template-based generation
# ---------------------------------------------------------------------------

def _template_greetings(intent_data, api_response):
    templates = [
        "Hello! How can I help you today?",
        "Hi there! What can I do for you?",
        "Hey! I'm Atlas, your virtual assistant. What do you need?",
    ]
    return random.choice(templates)


def _template_goodbye(intent_data, api_response):
    templates = [
        "Goodbye! Have a great day!",
        "See you later! Take care.",
        "Bye! Feel free to come back anytime.",
    ]
    return random.choice(templates)


def _template_oos(intent_data, api_response):
    templates = [
        "Sorry, I can't help with that. Try asking about movies, weather, the pet, or setting a timer.",
        "That's outside what I can do. I can help with movies, weather, pet care, or timers.",
        "I don't understand that request. Would you like to try something else?",
    ]
    return random.choice(templates)


def _template_set_timer(intent_data, api_response):
    duration = api_response.get("duration", "unknown")
    templates = [
        f"Timer set for {duration}.",
        f"Got it! I've started a {duration} timer.",
        f"Your timer for {duration} is now running.",
    ]
    return random.choice(templates)


def _template_weather(intent_data, api_response):
    city = api_response.get("city", "your location")
    temp = api_response.get("temperature", "N/A")
    description = api_response.get("description", "unknown conditions")
    wind = api_response.get("windspeed", "N/A")
    templates = [
        f"The current weather in {city} is {description}. The temperature is {temp}°C with wind speed of {wind} km/h.",
        f"Right now in {city}, it's {temp}°C with {description}. Wind is blowing at {wind} km/h.",
        f"In {city}, expect {description} at {temp}°C. Current wind speed is {wind} km/h.",
    ]
    return random.choice(templates)


# --- Movie intents ---

def _template_get_movie_cast(intent_data, api_response):
    title = api_response.get("title", "that movie")
    cast = api_response.get("cast", [])
    if not cast:
        return f"Sorry, I couldn't find the cast for {title}."
    cast_str = ", ".join(cast[:5])
    templates = [
        f"The cast of {title} includes {cast_str}.",
        f"{title} stars {cast_str}.",
        f"Here are the main actors in {title}: {cast_str}.",
    ]
    return random.choice(templates)


def _template_get_similar_movies(intent_data, api_response):
    title = api_response.get("title", "that movie")
    similar = api_response.get("similar", [])
    if not similar:
        return f"Sorry, I couldn't find movies similar to {title}."
    similar_str = ", ".join(similar[:5])
    templates = [
        f"If you liked {title}, you might enjoy: {similar_str}.",
        f"Movies similar to {title}: {similar_str}.",
        f"Here are some recommendations based on {title}: {similar_str}.",
    ]
    return random.choice(templates)


def _template_get_movie_plot(intent_data, api_response):
    title = api_response.get("title", "that movie")
    plot = api_response.get("plot", "")
    if not plot:
        return f"Sorry, I couldn't find the plot for {title}."
    templates = [
        f"Here's the plot of {title}: {plot}",
        f"{title} — {plot}",
        f"The story of {title}: {plot}",
    ]
    return random.choice(templates)


def _template_get_movies_by_genre(intent_data, api_response):
    genre = api_response.get("genre", "that genre")
    movies = api_response.get("movies", [])
    if not movies:
        return f"Sorry, I couldn't find any {genre} movies."
    movies_str = ", ".join(movies[:5])
    templates = [
        f"Here are some {genre} movies: {movies_str}.",
        f"Popular {genre} movies include: {movies_str}.",
        f"If you're in the mood for {genre}, try: {movies_str}.",
    ]
    return random.choice(templates)


def _template_get_movie_rating(intent_data, api_response):
    title = api_response.get("title", "that movie")
    rating = api_response.get("rating", "N/A")
    templates = [
        f"{title} has a rating of {rating}/10.",
        f"The rating for {title} is {rating} out of 10.",
        f"{title} is rated {rating}/10.",
    ]
    return random.choice(templates)


def _template_get_movie_director(intent_data, api_response):
    title = api_response.get("title", "that movie")
    director = api_response.get("director", "unknown")
    templates = [
        f"{title} was directed by {director}.",
        f"The director of {title} is {director}.",
        f"{director} directed {title}.",
    ]
    return random.choice(templates)


def _template_get_trending_movies(intent_data, api_response):
    movies = api_response.get("movies", [])
    if not movies:
        return "Sorry, I couldn't find any trending movies right now."
    movies_str = ", ".join(movies[:5])
    templates = [
        f"Here are the trending movies: {movies_str}.",
        f"Currently trending: {movies_str}.",
        f"The most popular movies right now are: {movies_str}.",
    ]
    return random.choice(templates)


def _template_get_upcoming_movies(intent_data, api_response):
    movies = api_response.get("movies", [])
    if not movies:
        return "Sorry, I couldn't find any upcoming movies."
    movies_str = ", ".join(movies[:5])
    templates = [
        f"Upcoming movies: {movies_str}.",
        f"Here's what's coming soon: {movies_str}.",
        f"Look out for these upcoming releases: {movies_str}.",
    ]
    return random.choice(templates)


# --- Pet intents ---

def _pet_status_str(status):
    """Format pet status bars as a short summary."""
    if not status:
        return ""
    parts = []
    for attr in ["hunger", "happiness", "energy", "cleanliness"]:
        val = status.get(attr)
        if val is not None:
            parts.append(f"{attr}: {val}/100")
    return " | ".join(parts)


def _template_feed_pet(intent_data, api_response):
    food = api_response.get("food_type", "food")
    name = api_response.get("pet_name", "your pet")
    status = api_response.get("status", {})
    templates = [
        f"You fed {name} some {food}. Yum!",
        f"{name} happily ate the {food}!",
        f"Feeding time! {name} enjoyed the {food}.",
    ]
    result = random.choice(templates)
    if status:
        result += f"\nStatus: {_pet_status_str(status)}"
    return result


def _template_play_with_pet(intent_data, api_response):
    toy = api_response.get("toy", "toy")
    name = api_response.get("pet_name", "your pet")
    status = api_response.get("status", {})
    templates = [
        f"You played with {name} using the {toy}. So fun!",
        f"{name} had a great time playing with the {toy}!",
        f"Play time with {name} and the {toy}!",
    ]
    result = random.choice(templates)
    if status:
        result += f"\nStatus: {_pet_status_str(status)}"
    return result


def _template_pet_the_cat(intent_data, api_response):
    name = api_response.get("pet_name", "your pet")
    status = api_response.get("status", {})
    templates = [
        f"You gave {name} some cuddles. {name} purrs happily!",
        f"{name} loves the attention! Purr purr.",
        f"You petted {name}. {name} is so happy!",
    ]
    result = random.choice(templates)
    if status:
        result += f"\nStatus: {_pet_status_str(status)}"
    return result


def _template_wash_pet(intent_data, api_response):
    name = api_response.get("pet_name", "your pet")
    status = api_response.get("status", {})
    templates = [
        f"You gave {name} a bath. All clean now!",
        f"{name} is squeaky clean after that bath!",
        f"Bath time is over. {name} looks fresh and clean!",
    ]
    result = random.choice(templates)
    if status:
        result += f"\nStatus: {_pet_status_str(status)}"
    return result


def _template_put_to_sleep(intent_data, api_response):
    name = api_response.get("pet_name", "your pet")
    duration = api_response.get("duration", "a while")
    status = api_response.get("status", {})
    templates = [
        f"{name} is now sleeping for {duration}. Sweet dreams!",
        f"Shh... {name} is taking a nap for {duration}.",
        f"Goodnight {name}! Sleeping for {duration}.",
    ]
    result = random.choice(templates)
    if status:
        result += f"\nStatus: {_pet_status_str(status)}"
    return result


def _template_wake_up_pet(intent_data, api_response):
    name = api_response.get("pet_name", "your pet")
    status = api_response.get("status", {})
    templates = [
        f"{name} is now awake and ready to play!",
        f"Good morning {name}! Rise and shine!",
        f"You woke up {name}. {name} stretches and yawns.",
    ]
    result = random.choice(templates)
    if status:
        result += f"\nStatus: {_pet_status_str(status)}"
    return result


def _template_give_treat(intent_data, api_response):
    treat = api_response.get("treat_type", "treat")
    name = api_response.get("pet_name", "your pet")
    status = api_response.get("status", {})
    templates = [
        f"You gave {name} a {treat}. {name} loved it!",
        f"{name} happily munched on the {treat}!",
        f"Treat time! {name} devoured the {treat}.",
    ]
    result = random.choice(templates)
    if status:
        result += f"\nStatus: {_pet_status_str(status)}"
    return result


def _template_check_status(intent_data, api_response):
    name = api_response.get("pet_name", "your pet")
    status = api_response.get("status", {})
    if not status:
        return f"I couldn't get {name}'s status right now."
    templates = [
        f"Here's how {name} is doing:\n{_pet_status_str(status)}",
        f"{name}'s current status:\n{_pet_status_str(status)}",
        f"Let me check on {name}...\n{_pet_status_str(status)}",
    ]
    return random.choice(templates)


def _template_rename_pet(intent_data, api_response):
    old_name = api_response.get("old_name", "your pet")
    new_name = api_response.get("new_name", "the pet")
    templates = [
        f"Done! {old_name} is now called {new_name}.",
        f"Your pet has been renamed from {old_name} to {new_name}!",
        f"Say hello to {new_name}! (formerly {old_name})",
    ]
    return random.choice(templates)


# --- Template dispatch ---

TEMPLATE_MAP = {
    "greetings": _template_greetings,
    "goodbye": _template_goodbye,
    "oos": _template_oos,
    "set_timer": _template_set_timer,
    "weather": _template_weather,
    "get_movie_cast": _template_get_movie_cast,
    "get_similar_movies": _template_get_similar_movies,
    "get_movie_plot": _template_get_movie_plot,
    "get_movies_by_genre": _template_get_movies_by_genre,
    "get_movie_rating": _template_get_movie_rating,
    "get_movie_director": _template_get_movie_director,
    "get_trending_movies": _template_get_trending_movies,
    "get_upcoming_movies": _template_get_upcoming_movies,
    "feed_pet": _template_feed_pet,
    "play_with_pet": _template_play_with_pet,
    "pet_the_cat": _template_pet_the_cat,
    "wash_pet": _template_wash_pet,
    "put_to_sleep": _template_put_to_sleep,
    "wake_up_pet": _template_wake_up_pet,
    "give_treat": _template_give_treat,
    "check_status": _template_check_status,
    "rename_pet": _template_rename_pet,
}


def _generate_template(intent_data, api_response):
    intent = intent_data.get("intent", "")
    handler = TEMPLATE_MAP.get(intent)
    if handler is None:
        return f"I'm not sure how to respond to the intent '{intent}'."
    try:
        return handler(intent_data, api_response)
    except Exception as e:
        return f"Sorry, I had trouble generating a response: {e}"


# ---------------------------------------------------------------------------
# LLM-based generation
# ---------------------------------------------------------------------------

_llm_cache = {}


def _load_llm():
    """Load distilgpt2 model and tokenizer (cached)."""
    if "model" not in _llm_cache:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        model_name = "distilgpt2"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name)
        model.eval()
        _llm_cache["model"] = model
        _llm_cache["tokenizer"] = tokenizer
    return _llm_cache["model"], _llm_cache["tokenizer"]


def _build_prompt(intent_data, api_response):
    """Build a prompt that instructs the LLM to generate a natural language response."""
    intent = intent_data.get("intent", "unknown")
    slots = intent_data.get("slots", {})

    prompt = (
        f"The user asked about '{intent}'"
    )
    if slots:
        slot_str = ", ".join(f"{k}={v}" for k, v in slots.items())
        prompt += f" with parameters: {slot_str}"
    prompt += ".\n"

    prompt += f"The system returned this data: {api_response}\n"
    prompt += "Write a short, friendly response to the user:\n"
    return prompt


def _generate_llm(intent_data, api_response):
    """Generate a response using distilgpt2."""
    import torch

    model, tokenizer = _load_llm()
    prompt = _build_prompt(intent_data, api_response)

    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=256)
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=80,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            pad_token_id=tokenizer.eos_token_id,
        )

    full_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    # Extract only the generated part (after the prompt)
    response = full_text[len(prompt):].strip()

    # Take only the first sentence/line to keep it clean
    for sep in ["\n", ". ", "! ", "? "]:
        if sep in response:
            response = response[:response.index(sep) + len(sep.strip())]
            break

    return response if response else _generate_template(intent_data, api_response)


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def process(intent_data, api_response, method="template"):
    """Generate a natural language response.

    Args:
        intent_data: dict with "intent" (str) and "slots" (dict).
        api_response: dict with the fulfillment result (API JSON or state change).
        method: "template" for rule-based, "llm" for model-based generation.

    Returns:
        str — the generated natural language response.
    """
    if api_response is None:
        api_response = {}

    if method == "llm":
        try:
            return _generate_llm(intent_data, api_response)
        except Exception as e:
            # Fall back to template if LLM fails
            print(f"LLM generation failed ({e}), falling back to template.")
            return _generate_template(intent_data, api_response)
    else:
        return _generate_template(intent_data, api_response)
