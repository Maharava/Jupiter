from ollama import chat
import re
from num2words import num2words

def send_to_ollama(core_prompt, context, stt_result):
    ollama_response = chat(
        model='llama3.2',
        stream=False,
        messages=[
            {
                'role': 'system',
                'content': core_prompt,
            },
            {
                'role': 'system',
                'content': "Here is the past conversations: " + context,
            },
            {
                'role': 'user',
                'content': stt_result,
            },
        ]
    )
    text = normalize_text(ollama_response['message']['content'])
    return text

def normalize_text(text):
    text = re.sub(r'\d+', lambda x: num2words(int(x.group())), text)
    text = text.replace('$', ' dollars ')
    text = re.sub(r'[\n\t\r\*]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.replace(r"G'day", "gaday")
    return text
