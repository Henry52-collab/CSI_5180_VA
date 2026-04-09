"""
Test script for the NLG module.
Tests all 22 intents with both template and LLM methods.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.nlg import process


# Sample API responses for each intent
TEST_CASES = {
    # --- Basic ---
    "greetings": ({}, {}),
    "goodbye": ({}, {}),
    "oos": ({}, {}),
    "set_timer": (
        {"duration": "5 minutes"},
        {"duration": "5 minutes"},
    ),
    "weather": (
        {"city": "Ottawa"},
        {"city": "Ottawa", "temperature": -3, "description": "partly cloudy", "windspeed": 15},
    ),

    # --- Movie ---
    "get_movie_cast": (
        {"title": "Inception"},
        {"title": "Inception", "cast": ["Leonardo DiCaprio", "Tom Hardy", "Elliot Page"]},
    ),
    "get_similar_movies": (
        {"title": "Inception"},
        {"title": "Inception", "similar": ["Interstellar", "The Matrix", "Shutter Island"]},
    ),
    "get_movie_plot": (
        {"title": "Inception"},
        {"title": "Inception", "plot": "A thief who steals corporate secrets through dream-sharing technology is given the task of planting an idea into the mind of a C.E.O."},
    ),
    "get_movies_by_genre": (
        {"genre": "action"},
        {"genre": "action", "movies": ["John Wick", "Mad Max", "The Dark Knight"]},
    ),
    "get_movie_rating": (
        {"title": "Inception"},
        {"title": "Inception", "rating": 8.8},
    ),
    "get_movie_director": (
        {"title": "Inception"},
        {"title": "Inception", "director": "Christopher Nolan"},
    ),
    "get_trending_movies": (
        {},
        {"movies": ["Oppenheimer", "Barbie", "Killers of the Flower Moon"]},
    ),
    "get_upcoming_movies": (
        {},
        {"movies": ["Dune Part 3", "Avatar 4", "The Batman 2"]},
    ),

    # --- Pet ---
    "feed_pet": (
        {"food_type": "fish"},
        {"food_type": "fish", "pet_name": "Mochi", "status": {"hunger": 80, "happiness": 60, "energy": 50, "cleanliness": 70}},
    ),
    "play_with_pet": (
        {"toy": "ball"},
        {"toy": "ball", "pet_name": "Mochi", "status": {"hunger": 70, "happiness": 85, "energy": 40, "cleanliness": 65}},
    ),
    "pet_the_cat": (
        {},
        {"pet_name": "Mochi", "status": {"hunger": 70, "happiness": 90, "energy": 40, "cleanliness": 65}},
    ),
    "wash_pet": (
        {},
        {"pet_name": "Mochi", "status": {"hunger": 70, "happiness": 75, "energy": 35, "cleanliness": 100}},
    ),
    "put_to_sleep": (
        {"duration": "2 hours"},
        {"duration": "2 hours", "pet_name": "Mochi", "status": {"hunger": 60, "happiness": 75, "energy": 90, "cleanliness": 95}},
    ),
    "wake_up_pet": (
        {},
        {"pet_name": "Mochi", "status": {"hunger": 50, "happiness": 70, "energy": 100, "cleanliness": 90}},
    ),
    "give_treat": (
        {"treat_type": "cookie"},
        {"treat_type": "cookie", "pet_name": "Mochi", "status": {"hunger": 85, "happiness": 95, "energy": 100, "cleanliness": 90}},
    ),
    "check_status": (
        {},
        {"pet_name": "Mochi", "status": {"hunger": 85, "happiness": 95, "energy": 100, "cleanliness": 90}},
    ),
    "rename_pet": (
        {"name": "Luna"},
        {"old_name": "Mochi", "new_name": "Luna"},
    ),
}


def test_templates():
    print("=" * 60)
    print("TEMPLATE-BASED GENERATION")
    print("=" * 60)
    for intent, (slots, api_response) in TEST_CASES.items():
        intent_data = {"intent": intent, "slots": slots}
        result = process(intent_data, api_response, method="template")
        print(f"\n[{intent}]")
        print(f"  {result}")
    print(f"\nAll {len(TEST_CASES)} intents tested.")


def test_llm():
    print("\n" + "=" * 60)
    print("LLM-BASED GENERATION")
    print("=" * 60)
    # Test a few representative intents (LLM is slow)
    sample_intents = ["weather", "get_movie_cast", "feed_pet", "check_status"]
    for intent in sample_intents:
        slots, api_response = TEST_CASES[intent]
        intent_data = {"intent": intent, "slots": slots}
        result = process(intent_data, api_response, method="llm")
        print(f"\n[{intent}]")
        print(f"  {result}")
    print(f"\n{len(sample_intents)} intents tested with LLM.")


def main():
    test_templates()

    choice = input("\nAlso test LLM? (downloads distilgpt2 ~300MB first time) [y/n]: ").strip().lower()
    if choice == "y":
        test_llm()

    print("\nDone!")


if __name__ == "__main__":
    main()
