import os
import nltk
import re
import numpy as np
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from joblib import load

lemmatizer = WordNetLemmatizer()
stop_words = set(stopwords.words('english'))

def preprocess(text):
    words = word_tokenize(text.lower())
    words = [lemmatizer.lemmatize(word) for word in words if word.isalnum() and word not in stop_words]
    return ' '.join(words)

def load_recog_model():
    # Construct the correct paths to the joblib files
    base_path = os.path.dirname(os.path.dirname(__file__))
    classifier_path = os.path.join(base_path, 'cModels', 'intent_classifier.joblib')
    vectorizer_path = os.path.join(base_path, 'cModels', 'vectorizer.joblib')
    
    classifier = load(classifier_path)
    vectorizer = load(vectorizer_path)
    return classifier, vectorizer

def get_intent(text, classifier, vectorizer, threshold=0.5):
    processed_text = preprocess(text)
    X_test = vectorizer.transform([processed_text])
    predicted_probabilities = classifier.predict_proba(X_test)
    
    # Get the index of the highest probability
    max_prob_index = np.argmax(predicted_probabilities)
    max_prob = predicted_probabilities[0][max_prob_index]
    
    # Check if the highest probability is above the threshold
    if max_prob >= threshold:
        predicted_intent = classifier.classes_[max_prob_index]
    else:
        predicted_intent = None
    
    return predicted_intent

def parse_duration(duration):
    # Use regex to find all the duration parts
    duration_regex = re.findall(r'(\d+)\s*(seconds?|minutes?|hours?)|(half|a half)\s*(minute|hour)', duration)
    total_seconds = 0
    for match in duration_regex:
        if match[0]:
            num = int(match[0])
            unit = match[1]
        elif match[2]:
            num = 0.5
            unit = match[3]
        
        if unit.startswith("second"):
            total_seconds += num
        elif unit.startswith("minute"):
            total_seconds += num * 60
        elif unit.startswith("hour"):
            total_seconds += num * 3600
    
    return total_seconds

def extract_timer_details(transcription):
    # Use regex to extract duration parts
    duration_matches = re.findall(r'(\d+)\s*(seconds?|minutes?|hours?)|(half|a half)\s*(minute|hour)', transcription)
    duration = []
    for match in duration_matches:
        if match[0]:
            duration.append(f"{match[0]} {match[1]}")
        elif match[2]:
            duration.append(f"{match[2]} {match[3]}")
    duration = ' '.join(duration)
    
    timer_name_match = re.search(r'timer called (\w+)', transcription)
    timer_name = timer_name_match.group(1) if timer_name_match else None
    
    return duration, timer_name
