from openai import OpenAI
import os
import json
import re
from datetime import datetime
from utility.utils import log_response, LOG_TYPE_GPT

if len(os.environ.get("GROQ_API_KEY", "")) > 30:
    from groq import Groq
    model = "llama3-70b-8192"
    client = Groq(
        api_key=os.environ.get("GROQ_API_KEY"),
    )
else:
    model = "gpt-4"
    OPENAI_API_KEY = os.environ.get('OPENAI_KEY')
    client = OpenAI(api_key=OPENAI_API_KEY)

log_directory = ".logs/gpt_logs"

prompt = """# Instructions

Given the following video script and timed captions, extract three visually concrete and specific keywords for each time segment that can be used to search for background videos. The keywords should be short and capture the main essence of the sentence. They can be synonyms or related terms. If a caption is vague or general, consider the next timed caption for more context. If a keyword is a single word, try to return a two-word keyword that is visually concrete. If a time frame contains two or more important pieces of information, divide it into shorter time frames with one keyword each. Ensure that the time periods are strictly consecutive and cover the entire length of the video. Each keyword should cover between 2-4 seconds.

For example, if the caption is 'The cheetah is the fastest land animal, capable of running at speeds up to 75 mph', the keywords should include 'cheetah running', 'fastest animal', and '75 mph'. Similarly, for 'The Great Wall of China is one of the most iconic landmarks in the world', the keywords should be 'Great Wall of China', 'iconic landmark', and 'China landmark'.

Important Guidelines:

Use only English in your text queries.
Each search string must depict something visual.
The depictions have to be extremely visually concrete, like rainy street, or cat sleeping.
'emotional moment' <= BAD, because it doesn't depict something visually.
'crying child' <= GOOD, because it depicts something visual.
The list must always contain the most relevant and appropriate query searches.
['Car', 'Car driving', 'Car racing', 'Car parked'] <= BAD, because it's 4 strings.
['Fast car'] <= GOOD, because it's 1 string.
['Un chien', 'une voiture rapide', 'une maison rouge'] <= BAD, because the text query is NOT in English.

Note: Your response should be the response only and no extra text or data.

Output the result as a Python list of lists, where each inner list contains a time range and a list of keywords. For example:
[[0, 5], ["keyword1", "keyword2", "keyword3"]], [[5, 10], ["keyword4", "keyword5", "keyword6"]], ...
"""

def fix_json(json_str):
    json_str = json_str.replace("'", '"')
    json_str = json_str.replace(""", '"').replace(""", '"').replace("'", '"').replace("'", '"')
    json_str = json_str.replace('"you didn"t"', '"you didn\'t"')
    return json_str

def getVideoSearchQueriesTimed(script, captions_timed):
    try:
        content = call_OpenAI(script, captions_timed)
        print("Content", content)
        
        # Remove any leading/trailing whitespace and non-list characters
        content = content.strip()
        content = re.sub(r'^[^\[]+', '', content)
        content = re.sub(r'[^\]]+$', '', content)
        
        # Evaluate the string as a Python expression
        out = eval(content)
        
        if not isinstance(out, list) or not all(isinstance(item, list) and len(item) == 2 for item in out):
            raise ValueError("Invalid format in API response")
        
        return out
    except Exception as e:
        print("Error in response", str(e))
        return None

def call_OpenAI(script, captions_timed):
    user_content = f"""Script: {script}
Timed Captions: {captions_timed}"""
    print("User Content", user_content)
    
    response = client.chat.completions.create(
        model=model,
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
