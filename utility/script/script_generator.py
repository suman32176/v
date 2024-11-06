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
from openai import OpenAI

if len(os.environ.get("GROQ_API_KEY", "")) > 30:
    from groq import Groq
    model = "mixtral-8x7b-32768"
    client = Groq(
        api_key=os.environ.get("GROQ_API_KEY"),
    )
else:
    OPENAI_API_KEY = os.getenv('OPENAI_KEY')
    model = "gpt-4"
    client = OpenAI(api_key=OPENAI_API_KEY)

def generate_script(topic, video_type='short'):
    if video_type == 'short':
        prompt = (
            """You are a seasoned content writer for a YouTube Shorts channel, specializing in facts videos. 
            Your facts shorts are concise, each lasting less than 50 seconds (approximately 140 words). 
            They are incredibly engaging and original. When a user requests a specific type of facts short, you will create it.
            ... (rest of the prompt remains the same) ...
            """
        )
    else:  # Long video script generation
        prompt = (
            """You are a skilled content writer for a YouTube channel, creating engaging and informative long videos. 
            These videos can be several minutes long, with rich content that captivates the audience. 
            When a user requests a specific type of long video, you will create it.
            The script should be at least 1000 words long, divided into clear sections or topics.
            Include engaging transitions between sections to maintain viewer interest.
            Incorporate storytelling elements, analogies, or examples to illustrate complex ideas.
            End with a strong conclusion that summarizes key points and encourages viewer engagement.
            """
        )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": topic}
        ]
    )
    content = response.choices[0].message.content
    try:
        script = json.loads(content)["script"]
    except Exception as e:
        # Fallback if JSON parsing fails
        json_start_index = content.find('{')
        json_end_index = content.rfind('}')
        content = content[json_start_index:json_end_index + 1]
        script = json.loads(content)["script"]
    return script

def split_script(script, words_per_segment=140):
    words = script.split()
    segments = []
    current_segment = []
    word_count = 0

    for word in words:
        current_segment.append(word)
        word_count += 1
        if word_count >= words_per_segment and word.endswith(('.', '!', '?')):
            segments.append(' '.join(current_segment))
            current_segment = []
            word_count = 0

    if current_segment:
        segments.append(' '.join(current_segment))

    return segments
