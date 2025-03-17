import os
import nltk
import numpy as np
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from joblib import load

# Initialize NLP components
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')

lemmatizer = WordNetLemmatizer()
stop_words = set(stopwords.words('english'))

def preprocess(text):
    words = word_tokenize(text.lower())
    words = [lemmatizer.lemmatize(word) for word in words if word.isalnum() and word not in stop_words]
    return ' '.join(words)

def load_model():
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
