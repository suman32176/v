import edge_tts
import logging

async def generate_audio(text, output_filename):
    try:
        communicate = edge_tts.Communicate(text, "en-AU-WilliamNeural")
        await communicate.save(output_filename)
        logging.info(f"Audio generated successfully: {output_filename}")
    except Exception as e:
        logging.error(f"Error generating audio: {str(e)}")
        raise
