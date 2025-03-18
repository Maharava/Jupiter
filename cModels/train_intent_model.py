import nltk
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
    "what time is it","do you have the time","tell me the time","whats the time","play some music","I want some music"
]
training_labels = [
    "tell_time","tell_time","tell_time","tell_time","play_music","play_music"
]

# Vectorize the sentences
vectorizer = CountVectorizer()
X_train = vectorizer.fit_transform(training_sentences)

# Train the classifier
classifier = LogisticRegression()
classifier.fit(X_train, training_labels)

# Save the trained model and vectorizer to a file
dump(classifier, 'intent_classifier.joblib')
dump(vectorizer, 'vectorizer.joblib')

print("Training complete and model saved successfully.")
