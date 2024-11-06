from openai import OpenAI
import os
import edge_tts
import json
import asyncio
import whisper_timestamped as whisper
from utility.script.script_generator import generate_script, split_script
from utility.audio.audio_generator import generate_audio
from utility.captions.timed_captions_generator import generate_timed_captions
from utility.video.background_video_generator import generate_video_url
from utility.render.render_engine import get_output_media, combine_video_segments
from utility.video.video_search_query_generator import getVideoSearchQueriesTimed, merge_empty_intervals
import argparse

async def process_segment(segment, segment_index):
    print(f"Processing segment {segment_index}...")
    
    audio_filename = f"audio_segment_{segment_index}.wav"
    await generate_audio(segment, audio_filename)

    timed_captions = generate_timed_captions(audio_filename)

    search_terms = getVideoSearchQueriesTimed(segment, timed_captions)

    background_video_urls = None
    if search_terms is not None:
        background_video_urls = generate_video_url(search_terms, "pexel")
        background_video_urls = merge_empty_intervals(background_video_urls)
    
    if background_video_urls is not None:
        video_filename = get_output_media(audio_filename, timed_captions, background_video_urls, "pexel")
        print(f"Segment {segment_index} video generated: {video_filename}")
        return video_filename
    else:
        print(f"No background video for segment {segment_index}")
        return None

async def main(topic, video_type):
    script = generate_script(topic, video_type)
    print("Generated script:", script)

    segments = split_script(script)
    print(f"Script split into {len(segments)} segments")

    segment_videos = []
    for i, segment in enumerate(segments):
        video_filename = await process_segment(segment, i)
        if video_filename:
            segment_videos.append(video_filename)

    if segment_videos:
        final_video = combine_video_segments(segment_videos)
        print(f"Final video generated: {final_video}")
    else:
        print("No videos were generated for any segments.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a video from a topic.")
    parser.add_argument("topic", type=str, help="The topic for the video")
    parser.add_argument("--video_type", type=str, choices=['short', 'long'], default='short', help="Type of video to generate")

    args = parser.parse_args()

    asyncio.run(main(args.topic, args.video_type))
