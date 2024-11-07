import os
import json
import asyncio
import argparse
from openai import OpenAI
import edge_tts
import whisper_timestamped as whisper
from utility.script.script_generator import generate_script
from utility.audio.audio_generator import generate_audio
from utility.captions.timed_captions_generator import generate_timed_captions
from utility.video.background_video_generator import generate_video_url
from utility.render.render_engine import get_output_media
from utility.video.video_search_query_generator import getVideoSearchQueriesTimed, merge_empty_intervals

# Determine which API client to use
if len(os.environ.get("GROQ_API_KEY", "")) > 30:
    from groq import Groq
    model = "mixtral-8x7b-32768"
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
else:
    OPENAI_API_KEY = os.getenv('OPENAI_KEY')
    model = "gpt-4"
    client = OpenAI(api_key=OPENAI_API_KEY)

async def process_script(script, video_type):
    SAMPLE_FILE_NAME = "audio_tts.wav"
    VIDEO_SERVER = "pexel"

    print("Processing script:", script[:100] + "..." if len(script) > 100 else script)

    # Generate audio from the script
    await generate_audio(script, SAMPLE_FILE_NAME)

    # Generate timed captions
    timed_captions = generate_timed_captions(SAMPLE_FILE_NAME)
    print("Timed Captions:", timed_captions)

    # Generate search terms for background videos
    search_terms = getVideoSearchQueriesTimed(script, timed_captions)
    print("Search Terms:", search_terms)

    # Generate background video URLs
    background_video_urls = None
    if search_terms is not None:
        background_video_urls = generate_video_url(search_terms, VIDEO_SERVER)
        print("Background Video URLs:", background_video_urls)
    else:
        print("No background video")

    background_video_urls = merge_empty_intervals(background_video_urls)

    # Generate the final video
    if background_video_urls is not None:
        video = get_output_media(SAMPLE_FILE_NAME, timed_captions, background_video_urls, VIDEO_SERVER)
        print("Output Video:", video)
    else:
        print("No video generated")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a video from a topic or use a pre-generated script.")
    parser.add_argument("--topic", type=str, help="The topic for the video")
    parser.add_argument("--video_type", type=str, choices=['short', 'long'], default='short', help="Type of video to generate")
    parser.add_argument("--script", type=str, help="Path to a pre-generated script file")

    args = parser.parse_args()

    if args.script:
        try:
            with open(args.script, 'r') as script_file:
                script = script_file.read().strip()
            print(f"Using pre-generated script from file: {args.script}")
            asyncio.run(process_script(script, args.video_type))
        except FileNotFoundError:
            print(f"Error: Script file '{args.script}' not found.")
            exit(1)
    elif args.topic:
        script = generate_script(args.topic, args.video_type)
        if isinstance(script, str) and script.startswith("Error"):
            print("Exiting due to script generation error:", script)
            exit(1)
        print("Generated Script:", script)
        asyncio.run(process_script(script, args.video_type))
    else:
        print("Error: Either --topic or --script must be provided.")
        parser.print_help()
        exit(1)
