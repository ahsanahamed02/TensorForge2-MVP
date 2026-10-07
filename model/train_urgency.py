import pandas as pd
import joblib

from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

train = pd.read_csv("data/train.csv")
val = pd.read_csv("data/validation.csv")

def build_text(df):
    return (
        "__CHANNEL_" + df["channel"].astype(str) + " "
        + df["subject"].fillna("") + " "
        + df["text"].fillna("")
    )

X_train = build_text(train)
X_val = build_text(val)

y_train = train["is_urgent"]
y_val = val["is_urgent"]

features = FeatureUnion([
    (
        "word",
        TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 2),
            min_df=2,
            sublinear_tf=True,
            max_features=50000
        )
    ),
    (
        "char",
        TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            min_df=2,
            sublinear_tf=True,
            max_features=60000
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

print("Training urgency classifier...")

model.fit(X_train, y_train)

joblib.dump(model, "model/urgency_model.joblib")
print("Saved: model/urgency_model.joblib")

pred = model.predict(X_val)

print("\n================================")
print(" TENSORFORGE URGENCY RESULTS")
print("================================")

print(f"\nAccuracy: {accuracy_score(y_val, pred):.4f}")

print("\nClassification Report:\n")
print(classification_report(y_val, pred, zero_division=0))

print("\nConfusion Matrix:")
print(confusion_matrix(y_val, pred))