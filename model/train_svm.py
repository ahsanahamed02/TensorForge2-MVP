import pandas as pd
import joblib

from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.metrics import accuracy_score, classification_report

train = pd.read_csv("data/train.csv")
val = pd.read_csv("data/validation.csv")

def build_text(df):
    subject = df["subject"].fillna("")
    text = df["text"].fillna("")

    return (
        "__CHANNEL_" + df["channel"].astype(str) + " "
        + subject + " "
        + text
    )

X_train = build_text(train)
X_val = build_text(val)

y_train = train["category"]
y_val = val["category"]

features = FeatureUnion([
    (
        "word",
        TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 2),
            min_df=2,
            sublinear_tf=True,
            max_features=60000
        )
    ),
    (
        "char",
        TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            min_df=2,
            sublinear_tf=True,
            max_features=80000
        )
    )
])

model = Pipeline([
    ("features", features),
    (
        "classifier",
        LinearSVC(
            C=1.5,
            class_weight="balanced"
        )
    )
])

print("Training multilingual hybrid SVM...")

model.fit(X_train, y_train)

joblib.dump(model, "model/category_model.joblib")
print("Saved: model/category_model.joblib")

pred = model.predict(X_val)

accuracy = accuracy_score(y_val, pred)

print("\n================================")
print(" TENSORFORGE HYBRID SVM RESULTS")
print("================================")

print(f"\nAccuracy: {accuracy:.4f}")
print(f"Accuracy %: {accuracy * 100:.2f}%")

print("\nClassification Report:\n")
print(classification_report(y_val, pred, zero_division=0))