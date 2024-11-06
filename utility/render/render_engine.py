import os
import tempfile
import platform
import subprocess
from moviepy.editor import (AudioFileClip, CompositeVideoClip, CompositeAudioClip,
                            TextClip, VideoFileClip, concatenate_videoclips)
import requests

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
        os.environ['IMAGEMAGICK_BINARY'] = '/usr/bin/convert'
    
    visual_clips = []
    for (t1, t2), video_url in background_video_data:
        if video_url:
            video_filename = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
            download_file(video_url, video_filename)
            
            video_clip = VideoFileClip(video_filename).subclip(0, t2-t1)
            video_clip = video_clip.set_start(t1).set_end(t2)
            visual_clips.append(video_clip)
    
    audio_clip = AudioFileClip(audio_file_path)

    for (t1, t2), text in timed_captions:
        text_clip = TextClip(txt=text, fontsize=50, color="white", stroke_width=2, stroke_color="black", method='caption', size=(1920, 1080))
        text_clip = text_clip.set_start(t1).set_end(t2).set_position(('center', 'bottom'))
        visual_clips.append(text_clip)

    video = CompositeVideoClip(visual_clips, size=(1920, 1080))
    video = video.set_audio(audio_clip)
    video = video.set_duration(audio_clip.duration)

    video.write_videofile(OUTPUT_FILE_NAME, codec='libx264', audio_codec='aac', fps=30)
    
    # Clean up downloaded files
    for clip in visual_clips:
        if isinstance(clip, VideoFileClip) and os.path.exists(clip.filename):
            os.remove(clip.filename)

    return OUTPUT_FILE_NAME

def combine_video_segments(segment_videos):
    clips = [VideoFileClip(video) for video in segment_videos]
    final_clip = concatenate_videoclips(clips)
    final_clip.write_videofile("final_video.mp4", codec='libx264', audio_codec='aac')
    return "final_video.mp4"
