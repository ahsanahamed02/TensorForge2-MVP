import pandas as pd

from sklearn.pipeline import FeatureUnion
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.pipeline import Pipeline

train = pd.read_csv("data/train.csv")
validation = pd.read_csv("data/validation.csv")

def build_text(df):
    subject = df["subject"].fillna("")
    text = df["text"].fillna("")
    return subject + " " + text

X_train = build_text(train)
X_val = build_text(validation)

y_train = train["category"]
y_val = validation["category"]

features = FeatureUnion([
    (
        "word_tfidf",
        TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 2),
            min_df=2,
            sublinear_tf=True,
            max_features=50000
        )
    ),
    (
        "char_tfidf",
        TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            min_df=2,
            sublinear_tf=True,
            max_features=70000
        )
    )
])

model = Pipeline([
    ("features", features),
    (
        "classifier",
        LogisticRegression(
            max_iter=3000,
            class_weight="balanced",
            C=2.0
        )
    )
])

print("Training hybrid multilingual model...")

model.fit(X_train, y_train)

predictions = model.predict(X_val)

accuracy = accuracy_score(y_val, predictions)

print("\n====================================")
print(" TENSORFORGE HYBRID MODEL RESULTS")
print("====================================")

print(f"\nAccuracy: {accuracy:.4f}")
print(f"Accuracy %: {accuracy * 100:.2f}%")

print("\nClassification Report:\n")
print(classification_report(y_val, predictions, zero_division=0))