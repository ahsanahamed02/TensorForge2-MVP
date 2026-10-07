import pandas as pd
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix

train = pd.read_csv("data/train.csv")
val = pd.read_csv("data/validation.csv")

def build_text(df):
    return df["subject"].fillna("") + " " + df["text"].fillna("")

X_train = build_text(train)
X_val = build_text(val)

features = FeatureUnion([
    ("word", TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 2),
        min_df=2,
        sublinear_tf=True,
        max_features=50000
    )),
    ("char", TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
        min_df=2,
        sublinear_tf=True,
        max_features=70000
    ))
])

model = Pipeline([
    ("features", features),
    ("classifier", LogisticRegression(
        max_iter=3000,
        class_weight="balanced",
        C=2.0
    ))
])

model.fit(X_train, train["category"])
pred = model.predict(X_val)

labels = sorted(train["category"].unique())
cm = confusion_matrix(val["category"], pred, labels=labels)

errors = []

for i, actual in enumerate(labels):
    for j, predicted in enumerate(labels):
        if i != j and cm[i, j] > 0:
            errors.append((cm[i, j], actual, predicted))

errors.sort(reverse=True)

print("\n=== TOP CATEGORY CONFUSIONS ===\n")

for count, actual, predicted in errors[:15]:
    print(f"{actual:22} -> {predicted:22} : {count}")

print("\n=== MISCLASSIFIED EXAMPLES ===\n")

wrong = val.copy()
wrong["predicted"] = pred
wrong = wrong[wrong["category"] != wrong["predicted"]]

for _, row in wrong.head(15).iterrows():
    print("TEXT:", str(row["text"])[:180])
    print("ACTUAL:", row["category"])
    print("PREDICTED:", row["predicted"])
    print("LANGUAGE:", row["language"])
    print("-" * 70)