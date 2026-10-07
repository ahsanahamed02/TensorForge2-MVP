import pandas as pd

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

model = Pipeline([
    (
        "tfidf",
        TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=2,
            sublinear_tf=True
        )
    ),
    (
        "classifier",
        LogisticRegression(
            max_iter=2000,
            class_weight="balanced"
        )
    )
])

print("Training baseline model...")

model.fit(X_train, y_train)

predictions = model.predict(X_val)

accuracy = accuracy_score(y_val, predictions)

print("\n==============================")
print(" TENSORFORGE BASELINE RESULTS")
print("==============================")

print(f"\nAccuracy: {accuracy:.4f}")
print(f"Accuracy %: {accuracy * 100:.2f}%")

print("\nClassification Report:\n")
print(classification_report(y_val, predictions, zero_division=0))