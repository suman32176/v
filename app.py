from openai import OpenAI
import os
import edge_tts
import json
import asyncio
import whisper_timestamped as whisper
from utility.script.script_generator import generate_script
from utility.audio.audio_generator import generate_audio
from utility.captions.timed_captions_generator import generate_timed_captions
from utility.video.background_video_generator import generate_video_url
from utility.render.render_engine import get_output_media
from utility.video.video_search_query_generator import getVideoSearchQueriesTimed, merge_empty_intervals
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a video from a topic or use a pre-generated script.")
    parser.add_argument("--topic", type=str, help="The topic for the video")
    parser.add_argument("--video_type", type=str, choices=['short', 'long'], default='short', help="Type of video to generate")
    parser.add_argument("--script", type=str, help="Pre-generated script to use instead of generating a new one")

    args = parser.parse_args()
    SAMPLE_FILE_NAME = "audio_tts.wav"
    VIDEO_SERVER = "pexel"

    # Check if a pre-generated script is provided
    if args.script:
        try:
            with open(args.script, 'r') as script_file:
                response = script_file.read().strip()
            print("Using pre-generated script:", response)
        except FileNotFoundError:
            print(f"Error: Script file '{args.script}' not found.")
            exit(1)
    elif args.topic:
        # Generate the script based on the video type
        response = generate_script(args.topic, args.video_type)
        print("Generated Script:", response)
    else:
        print("Error: Either --topic or --script must be provided.")
        parser.print_help()
        exit(1)

    if "Error" in response:
        print("Exiting due to script generation error.")
    else:
        asyncio.run(generate_audio(response, SAMPLE_FILE_NAME))

        timed_captions = generate_timed_captions(SAMPLE_FILE_NAME)
        print("Timed Captions:", timed_captions)

        search_terms = getVideoSearchQueriesTimed(response, timed_captions)
        print("Search Terms:", search_terms)

        background_video_urls = None
        if search_terms is not None:
            background_video_urls = generate_video_url(search_terms, VIDEO_SERVER)
            print("Background Video URLs:", background_video_urls)
        else:
            print("No background video")

        background_video_urls = merge_empty_intervals(background_video_urls)

        if background_video_urls is not None:
            video = get_output_media(SAMPLE_FILE_NAME, timed_captions, background_video_urls, VIDEO_SERVER)
            print("Output Video:", video)
        else:
            print("No video")
