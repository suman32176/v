import os
import argparse
from openai import OpenAI
import asyncio
from utility.script.script_generator import generate_script
from utility.audio.audio_generator import generate_audio
from utility.captions.timed_captions_generator import generate_timed_captions
from utility.video.background_video_generator import generate_video_url
from utility.render.render_engine import get_output_media
from utility.video.video_search_query_generator import getVideoSearchQueriesTimed, merge_empty_intervals
from moviepy.editor import concatenate_videoclips, VideoFileClip

OPENAI_API_KEY = os.getenv('OPENAI_KEY')
client = OpenAI(api_key=OPENAI_API_KEY)

def split_script(script, max_words=200):
    words = script.split()
    segments = []
    for i in range(0, len(words), max_words):
        segment = " ".join(words[i:i+max_words])
        segments.append(segment)
    return segments

def generate_short_video(segment, index):
    SAMPLE_FILE_NAME = f"audio_tts_{index}.wav"
    VIDEO_SERVER = "pexel"

    asyncio.run(generate_audio(segment, SAMPLE_FILE_NAME))

    timed_captions = generate_timed_captions(SAMPLE_FILE_NAME)
    search_terms = getVideoSearchQueriesTimed(segment, timed_captions)

    background_video_urls = None
    if search_terms is not None:
        background_video_urls = generate_video_url(search_terms, VIDEO_SERVER)
    
    background_video_urls = merge_empty_intervals(background_video_urls)

    if background_video_urls is not None:
        video = get_output_media(SAMPLE_FILE_NAME, timed_captions, background_video_urls, VIDEO_SERVER)
        return video
    else:
        print(f"No video generated for segment {index}")
        return None

def combine_videos(video_files):
    clips = [VideoFileClip(video) for video in video_files if video]
    final_clip = concatenate_videoclips(clips)
    final_clip.write_videofile("final_long_video.mp4")

def main():
    parser = argparse.ArgumentParser(description="Generate a video from a topic.")
    parser.add_argument("topic", type=str, help="The topic for the video")
    parser.add_argument("--video_type", type=str, choices=['short', 'long'], default='short', help="Type of video to generate")

    args = parser.parse_args()
    
    script = generate_script(args.topic, args.video_type)
    print("Generated Script:", script)

    if args.video_type == 'short':
        video = generate_short_video(script, 0)
        if video:
            print(f"Short video generated: {video}")
    else:
        segments = split_script(script)
        video_files = []
        for i, segment in enumerate(segments):
            print(f"Generating video for segment {i+1}/{len(segments)}")
            video = generate_short_video(segment, i)
            if video:
                video_files.append(video)
        
        if video_files:
            print("Combining short videos into a long video...")
            combine_videos(video_files)
            print("Long video generated: final_long_video.mp4")
        else:
            print("No videos were generated. Please check the logs for errors.")

if __name__ == "__main__":
    main()
