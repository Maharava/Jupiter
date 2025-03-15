import argparse
import os

# config.py
OPENWEATHER_API_KEY = 'your_api_key_here'
DEFAULT_LOCATION = 'Canberra'
conversation_file = r"C:\Users\rford\Local\HomeAI\AllInOne\info\conversation.json"

class Config:
    def __init__(self):
        self.jupiter = True
        self.ai_name = "Jupiter"
        self.AUTHORITY = True  # Default value, can be changed as needed

# Create a global instance of the Config class
config = Config()

def parse_args():
    parser = argparse.ArgumentParser(description='Running Home AI.')
    
    parser.add_argument(
        "--chunk_size",
        help="How much audio (in number of samples) to predict on at once",
        type=int,
        default=1280,
        required=False
    )
    parser.add_argument(
        "--model_path",
        help="The path of a specific model to load",
        type=str,
        default=os.path.join("myenv", "Lib", "site-packages", "openwakeword", "resources", "models", "hey_jarvis_v0.1.onnx"),
        required=False
    )
    parser.add_argument(
        "--inference_framework",
        help="The inference framework to use (either 'onnx' or 'tflite'",
        type=str,
        default='onnx',
        required=False
    )
    parser.add_argument(
        "personality",
        help="Enter the name 'Jupiter' or 'Saturn' for the AI you want",
        type=str
    )
    return parser.parse_args()
