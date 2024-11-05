import os
import json
import edge_tts
import asyncio
import whisper_timestamped as whisper
from utility.audio.audio_generator import generate_audio
from utility.captions.timed_captions_generator import generate_timed_captions
from utility.video.background_video_generator import generate_video_url
from utility.render.render_engine import get_output_media
from utility.video.video_search_query_generator import getVideoSearchQueriesTimed, merge_empty_intervals
import argparse
import os
import json
from openai import OpenAI

OPENAI_API_KEY = os.getenv('OPENAI_KEY')
client = OpenAI(api_key=OPENAI_API_KEY)

def generate_script(topic, video_type='short'):
    if video_type == 'short':
        prompt = """
        You are a seasoned content writer for a YouTube Shorts channel, specializing in facts videos. 
        Your facts shorts are concise, each lasting less than 50 seconds (approximately 140 words). 
        They are incredibly engaging and original. When a user requests a specific type of facts short, you will create it.

        For instance, if the user asks for:
        Weird facts
        You would produce content like this:

        Weird facts you don't know:
        - Bananas are berries, but strawberries aren't.
        - A single cloud can weigh over a million pounds.
        - There's a species of jellyfish that is biologically immortal.
        - Honey never spoils; archaeologists have found pots of honey in ancient Egyptian tombs that are over 3,000 years old and still edible.
        - The shortest war in history was between Britain and Zanzibar on August 27, 1896. Zanzibar surrendered after 38 minutes.
        - Octopuses have three hearts and blue blood.

        You are now tasked with creating the best short script based on the user's requested type of 'facts'.

        Keep it brief, highly interesting, and unique.
        """
    else:
        prompt = """
        You are an expert content writer tasked with creating an in-depth, fact-based script for a YouTube video designed to captivate and inform viewers. 
        Each script should present a thorough exploration of the topic, integrating rich, well-researched information in a continuous, engaging narrative. 
        Aim to write a single, uninterrupted paragraph with around 1,200 to 1,400 words, providing approximately 10 minutes of content that flows seamlessly and logically.

        Guidelines:
        - Write in a continuous paragraph without section headers, dialogue, or phrases like "Hello and welcome" or "In conclusion."
        - Organize the facts in a clear, cohesive narrative, avoiding lists or bullet points.
        - Each fact should connect smoothly to the next, forming a cohesive storyline that keeps viewers engaged from start to finish.
        """

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": topic}
            ]
        )
        
        script = response.choices[0].message.content.strip()
        return script
    except Exception as e:
        print("An error occurred:", str(e))
        return "Error: An unexpected error occurred."

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate a video script from a topic.")
    parser.add_argument("topic", type=str, help="The topic for the video")
    parser.add_argument("--video_type", type=str, choices=['short', 'long'], default='short', help="Type of video to generate")

    args = parser.parse_args()
    script = generate_script(args.topic, args.video_type)
    print(script)
