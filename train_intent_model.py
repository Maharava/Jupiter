import nltk
import re
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from joblib import dump

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

# Training data with similar sentences
training_sentences = [
    "shutdown","exit","close","shut down","please shut down","turn off now","please turn off",
    "what time is it","do you have the time","tell me the time","whats the time",
    "clear context","forget our conversation","delete our conversation","wipe your memory",
    "check internet connection","check internet","check connection","do you have internet access","can you access the internet",
    "set a timer for 5 minutes","start a 10-minute timer","set timer for 2 hours","create a timer for 30 seconds","set a timer called potatoes for 5 minutes",
    "set timer","create timer","start timer",
    "list active timers","what timers are running","show me the active timers","what timers are active","list timers"
]
training_labels = [
    "shut_down","shut_down","shut_down","shut_down","shut_down","shut_down","shut_down",
    "current_time","current_time","current_time","current_time",
    "clear_context","clear_context","clear_context","clear_context",
    "check_internet_connection","check_internet_connection","check_internet_connection","check_internet_connection","check_internet_connection",
    "set_timer","set_timer","set_timer","set_timer","set_timer",
    "set_timer","set_timer","set_timer",
    "list_timers","list_timers","list_timers","list_timers","list_timers"
]

# Preprocess training data
training_sentences = [preprocess(sentence) for sentence in training_sentences]

# Vectorize the sentences
vectorizer = CountVectorizer()
X_train = vectorizer.fit_transform(training_sentences)

# Train the classifier
classifier = LogisticRegression()
classifier.fit(X_train, training_labels)

# Save the trained model and vectorizer to a file
dump(classifier, 'cModels\\intent_classifier.joblib')
dump(vectorizer, 'cModels\\vectorizer.joblib')

print("Training complete and model saved successfully.")
