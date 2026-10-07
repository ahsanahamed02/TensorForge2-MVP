import pandas as pd
import joblib

from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.metrics import accuracy_score, classification_report

train = pd.read_csv("data/train.csv")
val = pd.read_csv("data/validation.csv")

train = train.dropna(subset=["secondary_category"]).copy()
val = val.dropna(subset=["secondary_category"]).copy()

def build_text(df):
    return (
        "__PRIMARY_" + df["category"].astype(str) + " "
        "__CHANNEL_" + df["channel"].astype(str) + " "
        + df["subject"].fillna("") + " "
        + df["text"].fillna("")
    )

X_train = build_text(train)
X_val = build_text(val)

y_train = train["secondary_category"]
y_val = val["secondary_category"]

features = FeatureUnion([
    (
        "word",
        TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 2),
            min_df=2,
            sublinear_tf=True,
            max_features=30000
        )
    ),
    (
        "char",
        TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            min_df=2,
            sublinear_tf=True,
            max_features=40000
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

print("Training secondary-label classifier...")

model.fit(X_train, y_train)

joblib.dump(model, "model/secondary_label_model.joblib")
print("Saved: model/secondary_label_model.joblib")

pred = model.predict(X_val)

print("\n====================================")
print(" TENSORFORGE SECONDARY LABEL RESULTS")
print("====================================")

print(f"\nTraining rows: {len(train)}")
print(f"Validation rows: {len(val)}")
print(f"Accuracy: {accuracy_score(y_val, pred):.4f}")
print(f"Accuracy %: {accuracy_score(y_val, pred) * 100:.2f}%")

print("\nClassification Report:\n")
print(classification_report(y_val, pred, zero_division=0))