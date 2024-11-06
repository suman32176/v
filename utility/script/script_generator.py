import os
from openai import OpenAI
import json

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
            Provide the script as plain text, without any JSON formatting.
            """
        )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Create a {video_type} video script about {topic}"}
        ]
    )
    script = response.choices[0].message.content.strip()
    
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
