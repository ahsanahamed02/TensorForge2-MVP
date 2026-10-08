import re
import pandas as pd
import joblib

from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    classification_report,
    confusion_matrix
)

# =========================================================
# LOAD DATA
# =========================================================
train = pd.read_csv("data/train.csv")
val = pd.read_csv("data/validation.csv")


# =========================================================
# INTENT FEATURE BUILDER
# IMPORTANT:
# If this model becomes production model,
# the SAME function must be used in predictor.py.
# =========================================================
def add_intent_hints(text):
    original = str(text)
    lower = original.lower()

    hints = []

    # -----------------------------------------------------
    # ORDER MISSING / WRONG
    # -----------------------------------------------------
    order_issue_patterns = [
        r"\bmissing\b",
        r"\bwrong item\b",
        r"\bwrong order\b",
        r"\bwrong food\b",
        r"\bnot included\b",
        r"\bnot in (the )?(bag|parcel|package|order)\b",
        r"\bwithout\b",
        r"\bshort\b",
        r"\bmissing item\b",
        r"\bmissing food\b",
        r"\bmissing drink\b",
        r"\bmissing beverage\b",
        r"\bmissing dessert\b",
        r"\bitem.*not.*arrived\b",
        r"\badd[- ]?on.*not\b",
        r"\bcombo.*without\b",
        r"\bpackage count.*short\b",
        r"\bnever selected\b",

        # Tanglish
        r"\bparcel la vaikkala\b",
        r"\bparcel la illa\b",
        r"\border la illa\b",
        r"\bitem varala\b",
        r"\bitem missing\b",
        r"\bwrong item\b",
        r"\bfood missing\b",
        r"\bdrink missing\b",

        # Tamil phrases seen in dataset style
        r"பொட்டலத்தில் வைக்கவில்லை",
        r"பார்சலில் இல்லை",
        r"ஆர்டரில் இல்லை",
        r"தவறான உணவு",

        # Sinhala style
        r"පාර්සලයට දාලා නැහැ",
        r"ඇණවුමේ නැහැ",
    ]

    # -----------------------------------------------------
    # PAYMENT / REFUND
    # -----------------------------------------------------
    payment_patterns = [
        r"\brefund\b",
        r"\brefunded\b",
        r"\brefund me\b",
        r"\bcharged twice\b",
        r"\bcharged again\b",
        r"\bdouble charged\b",
        r"\bduplicate charge\b",
        r"\bduplicate payment\b",
        r"\bpayment failed\b",
        r"\bpayment issue\b",
        r"\bwrong amount\b",
        r"\bovercharged\b",
        r"\bcredit back\b",
        r"\bmoney back\b",
        r"\btransaction\b",
        r"\bcharged\b",

        # Tanglish
        r"\brefund venum\b",
        r"\bmoney return\b",
        r"\bkaasu thiruppi\b",
        r"\bamount thiruppi\b",
        r"\btwice charge\b",

        # Tamil
        r"பணம்.*திருப்ப",
        r"கட்டணம்",
        r"பணம் திரும்ப",

        # Sinhala
        r"මුදල්.*ආපසු",
        r"ගෙවීම",
    ]

    # -----------------------------------------------------
    # DELIVERY DELAY
    # -----------------------------------------------------
    delivery_patterns = [
        r"\bdelivery delay\b",
        r"\blate delivery\b",
        r"\border.*late\b",
        r"\bfood.*late\b",
        r"\bnot arrived\b",
        r"\bnot delivered\b",
        r"\bstill waiting\b",
        r"\bwhere is my order\b",
        r"\bdelivery.*taking\b",
        r"\bdriver.*late\b",

        # Tanglish
        r"\border varala\b",
        r"\bfood varala\b",
        r"\blate ah varuthu\b",
        r"\bdelivery late\b",

        # Tamil
        r"இன்னும் வரவில்லை",
        r"தாமத",
        r"டெலிவரி.*வரவில்லை",

        # Sinhala
        r"තවම.*ආවේ නැහැ",
        r"ප්‍රමාද",
    ]

    # -----------------------------------------------------
    # APP / TECHNICAL
    # -----------------------------------------------------
    technical_patterns = [
        r"\bcannot log ?in\b",
        r"\bcan't log ?in\b",
        r"\bcant log ?in\b",
        r"\blogin problem\b",
        r"\blogin issue\b",
        r"\bapp crash\b",
        r"\bapp crashed\b",
        r"\bapplication crash\b",
        r"\bnot opening\b",
        r"\bapp not working\b",
        r"\btechnical issue\b",
        r"\berror message\b",
        r"\bserver error\b",
        r"\bbug\b",
        r"\bglitch\b",
        r"\bfreeze\b",
        r"\bfrozen\b",

        # Tanglish
        r"\bapp work aagala\b",
        r"\bapp open aagala\b",
        r"\blogin panna mudiyala\b",
        r"\berror varuthu\b",

        # Tamil
        r"உள்நுழைய முடியவில்லை",
        r"செயலி.*வேலை செய்யவில்லை",
        r"பிழை",

        # Sinhala
        r"ලොග්.*වෙන්න බැහැ",
        r"ඇප්.*වැඩ කරන්නේ නැහැ",
    ]

    # -----------------------------------------------------
    # FOOD QUALITY
    # -----------------------------------------------------
    food_quality_patterns = [
        r"\bcold food\b",
        r"\bfood.*cold\b",
        r"\bstale\b",
        r"\bspoiled\b",
        r"\bbad taste\b",
        r"\btastes bad\b",
        r"\bpoor quality\b",
        r"\bfood quality\b",
        r"\bburnt\b",
        r"\bburned\b",
        r"\braw food\b",
        r"\bundercooked\b",
        r"\bovercooked\b",
        r"\bsmells bad\b",

        # Tanglish
        r"\bfood cold\b",
        r"\btaste sari illa\b",
        r"\bfood nalla illa\b",
        r"\bquality sari illa\b",

        # Tamil
        r"உணவு.*குளிர",
        r"சுவை.*சரியில்லை",
        r"உணவு.*கெட்ட",

        # Sinhala
        r"කෑම.*සීතල",
        r"රස.*නැහැ",
    ]

    # -----------------------------------------------------
    # LOST ITEM
    # -----------------------------------------------------
    lost_item_patterns = [
        r"\blost my\b",
        r"\bleft my\b",
        r"\bforgot my\b",
        r"\bitem.*left\b",
        r"\bphone.*left\b",
        r"\bbag.*left\b",
        r"\bwallet.*left\b",
        r"\bkeys.*left\b",
        r"\bbelonging\b",
        r"\blost item\b",

        # Tanglish
        r"\bphone vittuten\b",
        r"\bbag vittuten\b",
        r"\bitem maranthuten\b",
        r"\blost aachu\b",
    ]

    # -----------------------------------------------------
    # SAFETY / CONDUCT
    # -----------------------------------------------------
    safety_patterns = [
        r"\bunsafe\b",
        r"\bharassment\b",
        r"\bharassed\b",
        r"\bthreat\b",
        r"\bthreatened\b",
        r"\babusive\b",
        r"\binappropriate\b",
        r"\brude driver\b",
        r"\bdriver.*rude\b",
        r"\bdriver.*behav",
        r"\bviolence\b",
        r"\bdanger\b",
        r"\bsafety\b",
    ]

    # -----------------------------------------------------
    # ACCOUNT / PROMO
    # -----------------------------------------------------
    account_patterns = [
        r"\bpromo\b",
        r"\bpromotion\b",
        r"\bcoupon\b",
        r"\bvoucher\b",
        r"\bdiscount\b",
        r"\baccount\b",
        r"\bprofile\b",
        r"\bphone number.*change\b",
        r"\bemail.*change\b",
    ]

    # -----------------------------------------------------
    # RIDE / TRIP
    # -----------------------------------------------------
    ride_patterns = [
        r"\bride\b",
        r"\btrip\b",
        r"\bdriver\b",
        r"\bpickup\b",
        r"\bdrop.?off\b",
        r"\bvehicle\b",
        r"\btaxi\b",
        r"\bfare\b",
    ]

    # -----------------------------------------------------
    # MATCH HELPER
    # -----------------------------------------------------
    def matches(patterns):
        return any(
            re.search(pattern, lower, re.IGNORECASE)
            for pattern in patterns
        )

    if matches(order_issue_patterns):
        hints.append("__ORDER_ISSUE_HINT")

    if matches(payment_patterns):
        hints.append("__PAYMENT_HINT")

    if matches(delivery_patterns):
        hints.append("__DELIVERY_HINT")

    if matches(technical_patterns):
        hints.append("__TECHNICAL_HINT")

    if matches(food_quality_patterns):
        hints.append("__FOOD_QUALITY_HINT")

    if matches(lost_item_patterns):
        hints.append("__LOST_ITEM_HINT")

    if matches(safety_patterns):
        hints.append("__SAFETY_HINT")

    if matches(account_patterns):
        hints.append("__ACCOUNT_HINT")

    if matches(ride_patterns):
        hints.append("__RIDE_HINT")

    # Useful interaction features
    if (
        "__ORDER_ISSUE_HINT" in hints
        and "__PAYMENT_HINT" in hints
    ):
        hints.append("__ORDER_AND_PAYMENT")

    if (
        "__ORDER_ISSUE_HINT" in hints
        and "__DELIVERY_HINT" not in hints
    ):
        hints.append("__ORDER_CONTENT_PROBLEM")

    if (
        "__DELIVERY_HINT" in hints
        and "__ORDER_ISSUE_HINT" not in hints
    ):
        hints.append("__PURE_DELIVERY_PROBLEM")

    return " ".join(hints)


# =========================================================
# BUILD MODEL TEXT
# =========================================================
def build_text(df):
    subject = df["subject"].fillna("").astype(str)
    body = df["text"].fillna("").astype(str)
    channel = df["channel"].fillna("unknown").astype(str)

    output = []

    for ch, sub, txt in zip(channel, subject, body):
        combined = f"{sub} {txt}"

        hints = add_intent_hints(combined)

        model_text = (
            f"__CHANNEL_{ch} "
            f"{hints} "
            f"{sub} "
            f"{txt}"
        )

        output.append(model_text)

    return pd.Series(output, index=df.index)


X_train = build_text(train)
X_val = build_text(val)

y_train = train["category"]
y_val = val["category"]


# =========================================================
# MODELS TO TEST
# =========================================================
configs = [
    {
        "name": "v3_C1.0",
        "C": 1.0
    },
    {
        "name": "v3_C1.25",
        "C": 1.25
    },
    {
        "name": "v3_C1.5",
        "C": 1.5
    },
    {
        "name": "v3_C1.75",
        "C": 1.75
    },
    {
        "name": "v3_C2.0",
        "C": 2.0
    },
]


best_model = None
best_pred = None
best_accuracy = 0
best_macro_f1 = 0
best_name = None

results = []


# =========================================================
# TRAIN
# =========================================================
for config in configs:

    print("\n=================================================")
    print(f"Training: {config['name']}")
    print("=================================================")

    features = FeatureUnion([
        (
            "word",
            TfidfVectorizer(
                analyzer="word",
                ngram_range=(1, 2),
                min_df=2,
                sublinear_tf=True,
                max_features=80000
            )
        ),

        (
            "char",
            TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(3, 5),
                min_df=2,
                sublinear_tf=True,
                max_features=120000
            )
        )
    ])

    model = Pipeline([
        ("features", features),

        (
            "classifier",
            LinearSVC(
                C=config["C"],
                class_weight="balanced"
            )
        )
    ])

    model.fit(X_train, y_train)

    pred = model.predict(X_val)

    accuracy = accuracy_score(
        y_val,
        pred
    )

    macro_f1 = f1_score(
        y_val,
        pred,
        average="macro",
        zero_division=0
    )

    print(
        f"Accuracy : {accuracy * 100:.2f}%"
    )

    print(
        f"Macro F1 : {macro_f1:.4f}"
    )

    results.append({
        "experiment": config["name"],
        "C": config["C"],
        "accuracy": accuracy,
        "accuracy_percent": accuracy * 100,
        "macro_f1": macro_f1
    })

    if (
        accuracy > best_accuracy
        or (
            accuracy == best_accuracy
            and macro_f1 > best_macro_f1
        )
    ):
        best_accuracy = accuracy
        best_macro_f1 = macro_f1
        best_model = model
        best_pred = pred
        best_name = config["name"]


# =========================================================
# RESULTS TABLE
# =========================================================
results_df = pd.DataFrame(results)

results_df = results_df.sort_values(
    ["accuracy", "macro_f1"],
    ascending=False
)

results_df.to_csv(
    "model/category_v3_experiments.csv",
    index=False
)


print("\n\n=================================================")
print("V3 EXPERIMENT SUMMARY")
print("=================================================")

print(
    results_df[
        [
            "experiment",
            "accuracy_percent",
            "macro_f1",
            "C"
        ]
    ].to_string(index=False)
)


# =========================================================
# SAVE BEST V3 MODEL
# =========================================================
joblib.dump(
    best_model,
    "model/category_model_v3.joblib"
)

print("\n=================================================")
print("BEST V3 MODEL")
print("=================================================")

print(
    f"Experiment : {best_name}"
)

print(
    f"Accuracy   : {best_accuracy * 100:.2f}%"
)

print(
    f"Macro F1   : {best_macro_f1:.4f}"
)

print(
    "\nSaved: model/category_model_v3.joblib"
)


# =========================================================
# CLASSIFICATION REPORT
# =========================================================
print("\n=================================================")
print("CLASSIFICATION REPORT")
print("=================================================\n")

print(
    classification_report(
        y_val,
        best_pred,
        zero_division=0
    )
)


# =========================================================
# CONFUSION MATRIX
# =========================================================
labels = sorted(
    y_val.unique()
)

cm = confusion_matrix(
    y_val,
    best_pred,
    labels=labels
)

cm_df = pd.DataFrame(
    cm,
    index=labels,
    columns=labels
)

cm_df.to_csv(
    "model/category_v3_confusion_matrix.csv"
)

print(
    "Saved: model/category_v3_confusion_matrix.csv"
)


# =========================================================
# WRONG PREDICTIONS
# =========================================================
wrong = val.copy()

wrong["predicted_category"] = best_pred

wrong["intent_hints"] = [
    add_intent_hints(
        f"{subject} {text}"
    )
    for subject, text in zip(
        val["subject"].fillna(""),
        val["text"].fillna("")
    )
]

wrong = wrong[
    wrong["category"]
    != wrong["predicted_category"]
]

wrong.to_csv(
    "model/category_v3_errors.csv",
    index=False
)

print(
    "Saved: model/category_v3_errors.csv"
)


# =========================================================
# WEAK CLASS SUMMARY
# =========================================================
print("\n=================================================")
print("WEAK CLASS CHECK")
print("=================================================")

report = classification_report(
    y_val,
    best_pred,
    output_dict=True,
    zero_division=0
)

weak_classes = [
    "order_missing_wrong",
    "food_quality",
    "app_technical",
    "payment_refund",
    "lost_item"
]

for label in weak_classes:

    metrics = report.get(
        label,
        {}
    )

    print(
        f"{label:22s} "
        f"Precision={metrics.get('precision', 0):.3f} "
        f"Recall={metrics.get('recall', 0):.3f} "
        f"F1={metrics.get('f1-score', 0):.3f}"
    )


print("\n=================================================")
print("DONE")
print("=================================================")

print(
    "Production category_model.joblib was NOT overwritten."
)