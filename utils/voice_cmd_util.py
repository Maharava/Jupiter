import re
import os
import json
import sys
import datetime
import requests
import threading
import time
from datetime import datetime
from config import *
from utils.intent_recog_util import parse_duration
from utils.convo_util import *
from utils.intent_recog_util import preprocess, load_recog_model, get_intent
from utils.ollama_util import send_to_ollama
from utils.piper_util import llm_speak

class Command:
    CHECK_AUTH = False

    def __init__(self, core_prompt, context):
        self.core_prompt = core_prompt
        self.context = context

    def execute(self):
        if self.CHECK_AUTH and not config.AUTHORITY:
            llm_speak("Unauthorized command.")
            print("Unauthorized.")
            return
        self.run()

    def run(self):
        raise NotImplementedError("Subclasses should implement this method.")

class ShutDown(Command):
    CHECK_AUTH = True

    def run(self):
        # Call the log_conversation function
        log_conversation(conversation_file, f"{config.ai_name} shutdown", self.context)

        response = send_to_ollama(self.core_prompt, "", "The user is signing off now. Please say goodbye. Keep it short..")
        llm_speak(response)
        sys.exit(0)

class CurrentTime(Command):
    def run(self):
        current_time = datetime.now().strftime("%H:%M:%S")
        message = f"The user wants to know the time. The current time is: {current_time}. Tell them the time in a regular way - instead of 11:42 say 'eleven forty' and so forth. Keep it short."
        response = llm_speak(send_to_ollama(self.core_prompt, "", message))

class ClearContext(Command):
    CHECK_AUTH = True

    def run(self):
        base_path = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_path, '..', 'info', 'conversation.json')  # Adjust the path to point to the 'info' folder in the root directory
        print(f"File path: {file_path}")  # Debug print to check the file path
        
        if os.path.exists(file_path):
            print("File exists.")  # Debug print to confirm file existence
            directory, filename = os.path.split(file_path)
            name, ext = os.path.splitext(filename)
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"{name}_{current_time}{ext}"
            new_file_path = os.path.join(directory, new_filename)
            os.rename(file_path, new_file_path)
            print(f"{file_path} has been renamed to {new_file_path}.")
            llm_speak(send_to_ollama(self.core_prompt, "", "You have renamed the conversation file. Inform the user the chat history has been saved elsewhere and you now have a blank slate. Keep it short and factual."))
            # Create a new blank JSON file to reset the conversation
            with open(file_path, 'w') as file:
                json.dump([], file)
        else:
            print("File does not exist.")  # Debug print to confirm file non-existence
            llm_speak(send_to_ollama(self.core_prompt, "", "The user has asked for you to rename the chat history. Inform them you can't find any chat history."))


class GetWeather(Command):
    def run(self, location=DEFAULT_LOCATION):
        url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={c801b6572b981cb5e513689c637170bb}&units=metric"
        response = requests.get(url).json()
        if response["cod"] != 200:
            weather_info = "The user asked for weather information, but you are unable to get it."
        else:
            main = response['main']
            weather = response['weather'][0]
            temp = main['temp']
            description = weather['description']
            weather_info = f"The current temperature in {location} is {temp}°C with {description}."
        message = f"The user asked for the weather. Here is the weather information: {weather_info}"
        response = llm_speak(send_to_ollama(self.core_prompt, "", message+" Keep it concise."))

class CheckInternetConnection(Command):
    def run(self, url='http://www.google.com/', timeout=5):
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                llm_speak(send_to_ollama(self.core_prompt, "", "The user requested a connection check. Let them know you have internet connection concisely."))
                print("Internet connected")
                return True
            else:
                llm_speak(send_to_ollama(self.core_prompt, "", "The user requested a connection check. Let them know you do not have internet connection concisely."))
                print("No internet")
                return False
        except requests.ConnectionError:
            llm_speak(send_to_ollama(self.core_prompt, "", "The user requested a connection check. Let them know you do not have internet connection concisely."))
            print("No internet")
            return False


class SetTimer(Command):
    timers = {}

    def __init__(self, core_prompt, context, duration, timer_name=None):
        super().__init__(core_prompt, context)
        self.duration = parse_duration(duration)
        if timer_name:
            self.timer_name = timer_name
        else:
            # Set the name of the timer to its duration if no name is provided
            self.timer_name = duration

    def format_duration(self, duration):
        hours, remainder = divmod(duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        parts = []
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if seconds > 0:
            parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
        return ' '.join(parts)

    def run(self):
        if self.duration > 0:
            end_time = time.time() + self.duration
            formatted_duration = self.format_duration(self.duration)
            if isinstance(self.timer_name, str) and self.timer_name.isdigit():
                message = f"A timer is set for {formatted_duration}. The timer has started."
            else:
                message = f"The '{self.timer_name}' timer is set for {formatted_duration}. The timer has started."
            llm_speak(message)
            timer_thread = threading.Thread(target=self.timer_end)
            SetTimer.timers[self.timer_name] = {"end_time": end_time, "duration": self.duration, "thread": timer_thread}
            timer_thread.start()
        else:
            llm_speak("Invalid timer duration.")
            print("Invalid timer duration")

    def timer_end(self):
        time.sleep(self.duration)
        llm_speak(f"The timer '{self.timer_name}' has ended.")
        print(f"Timer '{self.timer_name}' ended")
        del SetTimer.timers[self.timer_name]

class ListTimers(Command):
    def run(self):
        if SetTimer.timers:
            message = ""
            for timer_name, timer_info in SetTimer.timers.items():
                remaining_time = int(timer_info["end_time"] - time.time())
                message += f"- {timer_name}: {remaining_time} seconds remaining\n"
            llm_speak(f"You have the following timers: {message}")
        else:
            llm_speak("There are no active timers.")
            print("No active timers")



# Mapping intents to actions
intent_functions = {
    "shut_down": ShutDown,
    "current_time": CurrentTime,
    "clear_context": ClearContext,
    "get_weather": GetWeather,
    "check_internet_connection": CheckInternetConnection,
    "set_timer":SetTimer,
    "list_timers":ListTimers
}

def handle_intent(intent, core_prompt, context):
    if intent in intent_functions:
        command = intent_functions[intent](core_prompt, context)
        command.execute()
    else:
        llm_speak(send_to_ollama(core_prompt, "", "Unknown command. Inform the user that the command is not recognized."))
