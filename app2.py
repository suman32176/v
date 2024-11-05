import os
import argparse
import asyncio
import json
import re
import requests
import tempfile
import platform
import subprocess
from datetime import datetime
from openai import OpenAI
import edge_tts
import whisper_timestamped as whisper
from moviepy.editor import (AudioFileClip, CompositeVideoClip, CompositeAudioClip, TextClip, VideoFileClip)

# Environment variables
OPENAI_API_KEY = os.getenv('OPENAI_KEY')
PEXELS_API_KEY = os.getenv('PEXELS_KEY')

# OpenAI client setup
client = OpenAI(api_key=OPENAI_API_KEY)

# Constants
LOG_TYPE_GPT = "GPT"
LOG_TYPE_PEXEL = "PEXEL"
DIRECTORY_LOG_GPT = ".logs/gpt_logs"
DIRECTORY_LOG_PEXEL = ".logs/pexel_logs"

# Utility functions
def log_response(log_type, query, response):
    log_entry = {
        "query": query,
        "response": response,
        "timestamp": datetime.now().isoformat()
    }
    if log_type == LOG_TYPE_GPT:
        directory = DIRECTORY_LOG_GPT
        filename = f'{datetime.now().strftime("%Y%m%d_%H%M%S")}_gpt3.txt'
    elif log_type == LOG_TYPE_PEXEL:
        directory = DIRECTORY_LOG_PEXEL
        filename = f'{datetime.now().strftime("%Y%m%d_%H%M%S")}_pexel.txt'
    else:
        return

    if not os.path.exists(directory):
        os.makedirs(directory)
    filepath = os.path.join(directory, filename)
    with open(filepath, "w") as outfile:
        outfile.write(json.dumps(log_entry) + '\n')

def fix_json(json_str):
    json_str = json_str.replace("'", "'")
    json_str = json_str.replace(""", "\"").replace(""", "\"").replace("'", "\"").replace("'", "\"")
    json_str = json_str.replace('"you didn"t"', '"you didn\'t"')
    return json_str

# Script generation
def generate_script(topic, video_type='short'):
    if video_type == 'short':
        prompt = """You are a seasoned content writer for a YouTube Shorts channel, specializing in facts videos. 
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

        Stictly output the script in a JSON format like below, and only provide a parsable JSON object with the key 'script'.

        # Output
        {"script": "Here is the script ..."}
        """
    else:
        prompt = """You are an expert content writer tasked with creating an in-depth, fact-based script for a YouTube video designed to captivate and inform viewers. Each script should present a thorough exploration of the topic, integrating rich, well-researched information in a continuous, engaging narrative. Aim to write a single, uninterrupted paragraph with around 1,200 to 1,400 words, providing approximately 10 minutes of content that flows seamlessly and logically.

        **Guidelines**:
        - Write in a continuous paragraph without section headers, dialogue, or phrases like "Hello and welcome" or "In conclusion."
        - Organize the facts in a clear, cohesive narrative, avoiding lists or bullet points.
        - Each fact should connect smoothly to the next, forming a cohesive storyline that keeps viewers engaged from start to finish.

        **Output Instructions**:
        - Output only a valid JSON object with the key 'script' containing the entire paragraph as shown in the example below.
        - Ensure the output is in strict JSON format without additional text.

        # Output Example
        {"script": "The full paragraph script goes here..."}
        """

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": topic}
            ]
        )
        
        content = response.choices[0].message.content
        print("Raw Response:", content)
        
        if not content or (not content.startswith('{') and not content.startswith('[')):
            print("Error: Invalid response received from API.")
            return "Error: Invalid response received from API."
        
        script = json.loads(content)["script"]
        return script
    except json.JSONDecodeError as e:
        print("JSON decoding error:", str(e))
        print("Response content was:", content)
        return "Error: Could not decode JSON response."
    except Exception as e:
        print("An error occurred:", str(e))
        return "Error: An unexpected error occurred."

# Audio generation
async def generate_audio(text, output_filename):
    communicate = edge_tts.Communicate(text, "en-AU-WilliamNeural")
    await communicate.save(output_filename)

# Timed captions generation
def generate_timed_captions(audio_filename, model_size="base"):
    WHISPER_MODEL = whisper.load_model(model_size)
    gen = whisper.transcribe_timestamped(WHISPER_MODEL, audio_filename, verbose=False, fp16=False)
    return get_captions_with_time(gen)

def split_words_by_size(words, max_caption_size):
    half_caption_size = max_caption_size / 2
    captions = []
    while words:
        caption = words[0]
        words = words[1:]
        while words and len(caption + ' ' + words[0]) <= max_caption_size:
            caption += ' ' + words[0]
            words = words[1:]
            if len(caption) >= half_caption_size and words:
                break
        captions.append(caption)
    return captions

def get_timestamp_mapping(whisper_analysis):
    index = 0
    location_to_timestamp = {}
    for segment in whisper_analysis['segments']:
        for word in segment['words']:
            new_index = index + len(word['text']) + 1
            location_to_timestamp[(index, new_index)] = word['end']
            index = new_index
    return location_to_timestamp

def clean_word(word):
    return re.sub(r'[^\w\s\-_"\'\']', '', word)

def interpolate_time_from_dict(word_position, d):
    for key, value in d.items():
        if key[0] <= word_position <= key[1]:
            return value
    return None

def get_captions_with_time(whisper_analysis, max_caption_size=15, consider_punctuation=False):
    word_location_to_time = get_timestamp_mapping(whisper_analysis)
    position = 0
    start_time = 0
    captions_pairs = []
    text = whisper_analysis['text']
    
    if consider_punctuation:
        sentences = re.split(r'(?<=[.!?]) +', text)
        words = [word for sentence in sentences for word in split_words_by_size(sentence.split(), max_caption_size)]
    else:
        words = text.split()
        words = [clean_word(word) for word in split_words_by_size(words, max_caption_size)]
    
    for word in words:
        position += len(word) + 1
        end_time = interpolate_time_from_dict(position, word_location_to_time)
        if end_time and word:
            captions_pairs.append(((start_time, end_time), word))
            start_time = end_time

    return captions_pairs

# Video search query generation
def get_video_search_queries_timed(script, captions_timed):
    end = captions_timed[-1][0][1]
    try:
        out = [[[0,0],""]]
        while out[-1][0][1] != end:
            content = call_OpenAI(script, captions_timed).replace("'",'"')
            try:
                out = json.loads(content)
            except Exception as e:
                print("content: \n", content, "\n\n")
                print(e)
                content = fix_json(content.replace("```json", "").replace("```", ""))
                out = json.loads(content)
        return out
    except Exception as e:
        print("error in response", e)
    return None

def call_OpenAI(script, captions_timed):
    user_content = f"""Script: {script}
Timed Captions:{"".join(map(str,captions_timed))}
"""
    print("Content", user_content)
    
    response = client.chat.completions.create(
        model="gpt-4",
        temperature=1,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_content}
        ]
    )
    
    text = response.choices[0].message.content.strip()
    text = re.sub('\s+', ' ', text)
    print("Text", text)
    log_response(LOG_TYPE_GPT, script, text)
    return text

def merge_empty_intervals(segments):
    merged = []
    i = 0
    while i < len(segments):
        interval, url = segments[i]
        if url is None:
            j = i + 1
            while j < len(segments) and segments[j][1] is None:
                j += 1
            
            if i > 0:
                prev_interval, prev_url = merged[-1]
                if prev_url is not None and prev_interval[1] == interval[0]:
                    merged[-1] = [[prev_interval[0], segments[j-1][0][1]], prev_url]
                else:
                    merged.append([interval, prev_url])
            else:
                merged.append([interval, None])
            
            i = j
        else:
            merged.append([interval, url])
            i += 1
    
    return merged

# Background video generation
def search_videos(query_string, orientation_landscape=True):
    url = "https://api.pexels.com/videos/search"
    headers = {
        "Authorization": PEXELS_API_KEY,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    params = {
        "query": query_string,
        "orientation": "landscape" if orientation_landscape else "portrait",
        "per_page": 15
    }

    response = requests.get(url, headers=headers, params=params)
    json_data = response.json()
    log_response(LOG_TYPE_PEXEL, query_string, response.json())
   
    return json_data

def get_best_video(query_string, orientation_landscape=True, used_vids=[]):
    vids = search_videos(query_string, orientation_landscape)
    videos = vids['videos']

    if orientation_landscape:
        filtered_videos = [video for video in videos if video['width'] >= 1920 and video['height'] >= 1080 and video['width']/video['height'] == 16/9]
    else:
        filtered_videos = [video for video in videos if video['width'] >= 1080 and video['height'] >= 1920 and video['height']/video['width'] == 16/9]

    sorted_videos = sorted(filtered_videos, key=lambda x: abs(15-int(x['duration'])))

    for video in sorted_videos:
        for video_file in video['video_files']:
            if orientation_landscape:
                if video_file['width'] == 1920 and video_file['height'] == 1080:
                    if not (video_file['link'].split('.hd')[0] in used_vids):
                        return video_file['link']
            else:
                if video_file['width'] == 1080 and video_file['height'] == 1920:
                    if not (video_file['link'].split('.hd')[0] in used_vids):
                        return video_file['link']
    print("NO LINKS found for this round of search with query :", query_string)
    return None

def generate_video_url(timed_video_searches, video_server):
    timed_video_urls = []
    if video_server == "pexel":
        used_links = []
        for (t1, t2), search_terms in timed_video_searches:
            url = ""
            for query in search_terms:
                url = get_best_video(query, orientation_landscape=True, used_vids=used_links)
                if url:
                    used_links.append(url.split('.hd')[0])
                    break
            timed_video_urls.append([[t1, t2], url])
    return timed_video_urls

# Video rendering
def download_file(url, filename):
    with open(filename, 'wb') as f:
        headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        f.write(response.content)

def search_program(program_name):
    try: 
        search_cmd = "where" if platform.system() == "Windows" else "which"
        return subprocess.check_output([search_cmd, program_name]).decode().strip()
    except subprocess.CalledProcessError:
        return None

def get_program_path(program_name):
    program_path = search_program(program_name)
    return program_path

def get_output_media(audio_file_path, timed_captions, background_video_data, video_server):
    OUTPUT_FILE_NAME = "rendered_video.mp4"
    magick_path = get_program_path("magick")
    print(magick_path)
    if magick_path:
        os.environ['IMAGEMAGICK_BINARY'] = magick_path
    else:
        os.environ['IMAGEMAGICK_BINARY'] = 

 '/usr/bin/convert'
    
    visual_clips = []
    for (t1, t2), video_url in background_video_data:
        video_filename = tempfile.NamedTemporaryFile(delete=False).name
        download_file(video_url, video_filename)
        
        video_clip = VideoFileClip(video_filename)
        video_clip = video_clip.set_start(t1)
        video_clip = video_clip.set_end(t2)
        visual_clips.append(video_clip)
    
    audio_clips = []
    audio_file_clip = AudioFileClip(audio_file_path)
    audio_clips.append(audio_file_clip)

    for (t1, t2), text in timed_captions:
        text_clip = TextClip(txt=text, fontsize=100, color="white", stroke_width=3, stroke_color="black", method="label")
        text_clip = text_clip.set_start(t1)
        text_clip = text_clip.set_end(t2)
        text_clip = text_clip.set_position(["center", 800])
        visual_clips.append(text_clip)

    video = CompositeVideoClip(visual_clips)
    
    if audio_clips:
        audio = CompositeAudioClip(audio_clips)
        video.duration = audio.duration
        video.audio = audio

    video.write_videofile(OUTPUT_FILE_NAME, codec='libx264', audio_codec='aac', fps=25, preset='veryfast')
    
    for (t1, t2), video_url in background_video_data:
        video_filename = tempfile.NamedTemporaryFile(delete=False).name
        os.remove(video_filename)

    return OUTPUT_FILE_NAME

# Main execution
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a video from a topic.")
    parser.add_argument("topic", type=str, help="The topic for the video")
    parser.add_argument("--video_type", type=str, choices=['short', 'long'], default='short', help="Type of video to generate")

    args = parser.parse_args()
    SAMPLE_TOPIC = args.topic
    SAMPLE_FILE_NAME = "audio_tts.wav"
    VIDEO_SERVER = "pexel"

    # Generate the script based on the video type
    response = generate_script(SAMPLE_TOPIC, args.video_type)
    print("script: {}".format(response))

    asyncio.run(generate_audio(response, SAMPLE_FILE_NAME))

    timed_captions = generate_timed_captions(SAMPLE_FILE_NAME)
    print(timed_captions)

    search_terms = get_video_search_queries_timed(response, timed_captions)
    print(search_terms)

    background_video_urls = None
    if search_terms is not None:
        background_video_urls = generate_video_url(search_terms, VIDEO_SERVER)
        print(background_video_urls)
    else:
        print("No background video")

    background_video_urls = merge_empty_intervals(background_video_urls)

    if background_video_urls is not None:
        video = get_output_media(SAMPLE_FILE_NAME, timed_captions, background_video_urls, VIDEO_SERVER)
        print(video)
    else:
        print("No video")
