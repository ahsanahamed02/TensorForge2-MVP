from pathlib import Path
import re

import joblib
import numpy as np
import pandas as pd

from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    classification_report,
    confusion_matrix,
)

from model.intent_hints_v3 import add_intent_hints


ROOT = Path(__file__).resolve().parents[1]

TRAIN_PATH = ROOT / "data" / "train.csv"
VAL_PATH = ROOT / "data" / "validation.csv"

MODEL_DIR = ROOT / "model"

OUTPUT_MODEL = MODEL_DIR / "category_model_v8.joblib"
OUTPUT_ERRORS = MODEL_DIR / "category_v8_errors.csv"
OUTPUT_MATRIX = MODEL_DIR / "category_v8_confusion_matrix.csv"
OUTPUT_RESULTS = MODEL_DIR / "category_v8_experiments.csv"

V3_ACCURACY = 0.70375


# =========================================================
# CLEAN TEXT
# =========================================================

def clean_text(value):
    if pd.isna(value):
        return ""

    text = str(value)

    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    text = re.sub(
        r"\[inaudible\]",
        " ",
        text,
        flags=re.I
    )

    # Remove old quoted support history
    markers = [
        r"\bon an earlier date\b",
        r"\bearlier unrelated case\b",
        r"\bprevious unrelated case\b",
    ]

    for marker in markers:
        match = re.search(
            marker,
            text,
            flags=re.I
        )

        if match:
            text = text[:match.start()]

    # Remove quoted lines
    text = re.sub(
        r"(?m)^\s*>\s*.*$",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    return text


# =========================================================
# REGEX HELPER
# =========================================================

def contains_any(text, patterns):
    for pattern in patterns:
        if re.search(
            pattern,
            text,
            flags=re.I
        ):
            return True

    return False


# =========================================================
# V8 CONCEPT HINTS
# =========================================================

def add_v8_concept_hints(text):
    """
    General semantic concept hints.

    No ticket IDs.
    No answer lookup.
    No validation-row mapping.
    """

    raw = clean_text(text)
    lower = raw.lower()

    hints = []

    # =====================================================
    # 1. APP TECHNICAL
    # =====================================================

    app_patterns = [
        r"\bmenu\b.{0,35}\b(not|won'?t|doesn'?t|cannot|can'?t)\b.{0,25}\b(load|open|render|display)",
        r"\b(food|restaurant)\s+(list|menu)\b.{0,35}\b(load|open|render)",
        r"\bconversation panel\b.{0,35}\b(render|load|open)",
        r"\bpanel\b.{0,25}\b(refuses|fail|failed|not)\b.{0,20}\b(render|load|open)",
        r"\bapp\b.{0,25}\b(crash|freeze|frozen|unresponsive)",
        r"\bscreen\b.{0,25}\b(blank|freeze|frozen)",
        r"\bviewer\b.{0,30}\bunresponsive\b",

        # Sinhala
        r"සම්බන්ධතාව.{0,25}හොඳයි.{0,50}(කෑම|ආහාර).{0,20}(ලැයිස්තුව|මෙනුව).{0,35}(පූරණය|විවෘත).{0,20}(නැහැ|නෑ|වෙන්නේ නැහැ)",

        # Tamil
        r"இணைப்பு.{0,25}நன்றாக.{0,50}(உணவு|சாப்பாடு).{0,20}(பட்டியல்|மெனு).{0,35}(திறக்க|ஏற்ற).{0,20}(வில்லை|முடியவில்லை)",

        # Tanglish
        r"\b(connection|internet)\b.{0,20}\b(ok|fine|working)\b.{0,35}\b(menu|food list)\b.{0,25}\b(not loading|not opening|open aagala|load aagala)",
    ]

    if contains_any(raw, app_patterns):
        hints.extend([
            "__V8_APP_TECH__",
            "__V8_MENU_LOAD__",
            "__V8_TECH_FAILURE__",
        ])

    # =====================================================
    # 2. DELIVERY DELAY
    # =====================================================

    delivery_patterns = [
        r"\b(food|meal|order|delivery|takeaway|dinner bag)\b.{0,50}\b(not arrived|hasn'?t arrived|not turned up|still not arrived)",
        r"\bcourier\b.{0,40}\b(stopped|not moving|no progress)",
        r"\bstranded\b.{0,25}\b(collection|queue)",
        r"\barrival window\b.{0,35}\bpassed\b",
        r"\btracking\b.{0,30}\b(delivered|handover|complete)\b.{0,40}\b(no|not|nothing)\b",

        # Sinhala
        r"අවන්හලෙන්.{0,35}(කෑම|ආහාර).{0,35}(තවම|තවමත්).{0,35}(ගෙදර|නිවස).{0,35}(ඇවිත් නැහැ|ඇවිත් නෑ|ලැබී නැහැ)",

        # Tamil
        r"உணவகத்திலிருந்து.{0,40}(உணவு|சாப்பாடு).{0,35}(இன்னும்|இதுவரை).{0,35}(வீடு|வீட்டை).{0,35}(வந்தடையவில்லை|வரவில்லை)",

        # Singlish
        r"\b(kema|food|order)\b.{0,35}\b(thawama|still)\b.{0,30}\b(gedarata|home)\b.{0,30}\b(awilla na|enne na|arrive wela na)",
    ]

    if contains_any(raw, delivery_patterns):
        hints.extend([
            "__V8_DELIVERY_DELAY__",
            "__V8_NOT_ARRIVED__",
        ])

    # =====================================================
    # 3. PAYMENT / REFUND
    # =====================================================

    payment_patterns = [
        r"\b(overcharged|overcharge|extra charge|charged extra)\b",
        r"\bcharged\b.{0,30}\bmore\b",
        r"\bduplicate\b.{0,25}\b(charge|transaction|deduction)",
        r"\btwo\b.{0,25}\b(deductions|charges)\b",
        r"\brefund\b.{0,35}\b(missing|absent|not received|not credited)",
        r"\bcancellation credit\b.{0,30}\b(absent|missing|not)",
        r"\bbank\b.{0,30}\btransfer\b.{0,35}\b(succeeded|successful)\b.{0,40}\b(funds|balance)\b",

        # Sinhala
        r"රිසිට්.{0,35}ගානට.{0,20}වඩා.{0,30}(වැඩිපුර|වැඩි).{0,25}(අය කරලා|අරන්|ගෙන)",
        r"ගෙවීම්.{0,30}(වැඩිපුර|වැඩි).{0,25}(අය|ගෙවා)",

        # Tamil
        r"(ரசீது|கட்டணம்).{0,40}(அதிகமாக|கூடுதலாக).{0,35}(வசூல்|எடுத்த|கழித்த)",

        # Singlish
        r"\breceipt eke\b.{0,25}\bganata wada\b.{0,20}\b(wadipura|wedi)\b",
    ]

    if contains_any(raw, payment_patterns):
        hints.extend([
            "__V8_PAYMENT__",
            "__V8_REFUND_OR_CHARGE__",

            # Stronger payment evidence
            "__V8_PAYMENT_STRONG__",
            "__V8_PAYMENT_STRONG__",
        ])

    # =====================================================
    # 4. LOST ITEM
    # =====================================================

    lost_patterns = [
        r"\b(left|forgot|forgotten)\b.{0,35}\b(bag|phone|wallet|notebook|item|belonging|medicine)\b",
        r"\b(bag|phone|wallet|notebook|item|belonging)\b.{0,35}\b(rear seat|back seat|boot|vehicle|car)\b",
        r"\bgot out\b.{0,35}\bwithout taking\b",
        r"\bstill\b.{0,20}\b(rear seat|back seat|boot)\b",

        # Tamil
        r"(மறந்த|விட்டுவந்த|விட்டுவிட்ட).{0,35}(பை|பொருள்|மருந்து|தொலைபேசி)",

        # Sinhala
        r"(අමතක|දාලා ආවා|ඉතුරු වෙලා).{0,35}(බෑග්|බඩු|දුරකථනය|බෙහෙත්|ලිපිගොනුව)",
    ]

    if contains_any(raw, lost_patterns):
        hints.extend([
            "__V8_LOST_ITEM__",
            "__V8_LEFT_IN_VEHICLE__",
        ])

    # =====================================================
    # 5. RIDE / TRIP ISSUE
    # =====================================================

    ride_patterns = [
        r"\b(driver|operator|person assigned)\b.{0,40}\b(cancelled|canceled|rejected|withdrew)\b",
        r"\brejected\b.{0,35}\bjourney\b",
        r"\bwithdrew\b.{0,30}\bbooking\b",
        r"\bwrong\b.{0,30}\b(vehicle|entrance|destination)\b",
        r"\bsedan\b.{0,35}\bthree[- ]?wheeler\b",
        r"\broute\b.{0,30}\b(long|unnecessarily long)\b",
        r"\basked\b.{0,30}\bme\b.{0,25}\bcancel\b",
    ]

    if contains_any(raw, ride_patterns):
        hints.extend([
            "__V8_RIDE_ISSUE__",
            "__V8_TRIP_PROBLEM__",
        ])

    # =====================================================
    # 6. FOOD QUALITY
    # =====================================================

    food_quality_patterns = [
        r"\b(cold|spoiled|fungal|mould|mold|uncooked|raw)\b.{0,35}\b(food|meal|meat|bread)",
        r"\bpacking\b.{0,35}\b(crushed|damaged|open)",
        r"\bcontainer\b.{0,25}\bopen\b",
        r"\bmeal\b.{0,35}\bspread\b",
        r"\bthroat\b.{0,30}\b(tight|swelling)",
        r"\bface\b.{0,30}\bswelling\b",

        # Tamil
        r"உணவு.{0,30}(குளிர்ந்த|கெட்ட)",
        r"பொதி.{0,30}(நசுங்கி|சேத)",

        # Sinhala
        r"(කෑම|ආහාර).{0,30}(සීතල|නරක්|අමු)",
    ]

    if contains_any(raw, food_quality_patterns):
        hints.extend([
            "__V8_FOOD_QUALITY__",
        ])

    # =====================================================
    # 7. NEGATION AWARE PROTECTION
    # =====================================================

    safety_negation = contains_any(
        lower,
        [
            r"\bno safety incident\b",
            r"\bnot a safety issue\b",
            r"\bno danger\b",
            r"\bnobody is being threatened\b",
            r"\bno one is being threatened\b",
            r"\bonly joking\b",
            r"\bjust an expression\b",
        ],
    )

    if safety_negation:
        hints.extend([
            "__V8_NEGATED_SAFETY__",
            "__V8_NOT_SAFETY__",
        ])

    refund_negation = contains_any(
        lower,
        [
            r"\bnot asking for (a )?refund\b",
            r"\bdo not want (a )?refund\b",
            r"\bdon'?t want (a )?refund\b",
            r"\bno refund requested\b",
        ],
    )

    if refund_negation:
        hints.append(
            "__V8_NEGATED_REFUND__"
        )

    lost_negation = contains_any(
        lower,
        [
            r"\bnot lost\b.{0,20}\b(any|my)?\s*(item|belonging)",
            r"\bhave not lost\b.{0,25}\b(item|belonging|anything)",
            r"\bi have not lost any belongings\b",
        ],
    )

    if lost_negation:
        hints.append(
            "__V8_NEGATED_LOST__"
        )

    # =====================================================
    # OUTPUT
    # =====================================================

    if hints:
        return (
            raw
            + " "
            + " ".join(hints)
        )

    return raw


# =========================================================
# BUILD CATEGORY TEXT
# =========================================================

def build_text(row):
    channel = clean_text(
        row.get(
            "channel",
            ""
        )
    )

    subject = clean_text(
        row.get(
            "subject",
            ""
        )
    )

    body = clean_text(
        row.get(
            "text",
            ""
        )
    )

    combined = (
        f"{channel} "
        f"{subject} "
        f"{body}"
    ).strip()

    # Original V3 hints
    v3_hints = add_intent_hints(
        combined
    )

    # V8 semantic hints
    v8_text = add_v8_concept_hints(
        combined
    )

    parts = [
        combined
    ]

    if v3_hints:
        parts.append(
            v3_hints
        )

    cleaned_combined = clean_text(
        combined
    )

    if v8_text.startswith(
        cleaned_combined
    ):
        extra_v8 = v8_text[
            len(cleaned_combined):
        ].strip()

        if extra_v8:
            parts.append(
                extra_v8
            )

    return " ".join(
        parts
    )


# =========================================================
# MODEL PIPELINE
# =========================================================

def build_pipeline(C=1.25):
    features = FeatureUnion(
        [
            (
                "word",
                TfidfVectorizer(
                    analyzer="word",
                    ngram_range=(1, 2),
                    min_df=1,
                    max_df=0.995,
                    sublinear_tf=True,
                    max_features=120000,
                ),
            ),
            (
                "char",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=(3, 5),
                    min_df=1,
                    sublinear_tf=True,
                    max_features=180000,
                ),
            ),
        ]
    )

    model = LinearSVC(
        C=C,
        class_weight=None,
    )

    return Pipeline(
        [
            (
                "features",
                features
            ),
            (
                "classifier",
                model
            ),
        ]
    )


# =========================================================
# TRAIN
# =========================================================

def main():
    print(
        "=" * 70
    )

    print(
        "RouteIQ Category Model V8"
    )

    print(
        "=" * 70
    )

    train = pd.read_csv(
        TRAIN_PATH
    )

    val = pd.read_csv(
        VAL_PATH
    )

    print(
        f"Train rows      : {len(train)}"
    )

    print(
        f"Validation rows : {len(val)}"
    )

    X_train = train.apply(
        build_text,
        axis=1
    )

    y_train = train[
        "category"
    ].astype(str)

    X_val = val.apply(
        build_text,
        axis=1
    )

    y_val = val[
        "category"
    ].astype(str)

    experiments = []

    C_VALUES = [
        0.80,
        1.00,
        1.25,
        1.50,
        2.00,
        2.50,
    ]

    best_model = None
    best_accuracy = -1
    best_macro = -1
    best_c = None
    best_pred = None

    for c in C_VALUES:
        print()

        print(
            "-" * 70
        )

        print(
            f"Training C = {c}"
        )

        print(
            "-" * 70
        )

        pipeline = build_pipeline(
            C=c
        )

        pipeline.fit(
            X_train,
            y_train
        )

        pred = pipeline.predict(
            X_val
        )

        accuracy = accuracy_score(
            y_val,
            pred
        )

        macro_f1 = f1_score(
            y_val,
            pred,
            average="macro",
        )

        print(
            f"Accuracy : {accuracy:.4%}"
        )

        print(
            f"Macro F1 : {macro_f1:.6f}"
        )

        experiments.append(
            {
                "C": c,
                "accuracy": accuracy,
                "macro_f1": macro_f1,
            }
        )

        if (
            accuracy > best_accuracy
            or (
                np.isclose(
                    accuracy,
                    best_accuracy
                )
                and
                macro_f1 > best_macro
            )
        ):
            best_accuracy = accuracy
            best_macro = macro_f1
            best_c = c
            best_model = pipeline
            best_pred = pred

    # =====================================================
    # RESULTS
    # =====================================================

    print()

    print(
        "=" * 70
    )

    print(
        "BEST V8 RESULT"
    )

    print(
        "=" * 70
    )

    print(
        f"Best C          : {best_c}"
    )

    print(
        f"V8 Accuracy     : {best_accuracy:.4%}"
    )

    print(
        f"V8 Macro F1     : {best_macro:.6f}"
    )

    print(
        f"V3 Accuracy     : {V3_ACCURACY:.4%}"
    )

    delta = (
        best_accuracy
        - V3_ACCURACY
    )

    print(
        f"Accuracy change : {delta:+.4%}"
    )

    if best_accuracy > V3_ACCURACY:
        print(
            "RESULT           : V8 BEATS V3"
        )

    elif np.isclose(
        best_accuracy,
        V3_ACCURACY
    ):
        print(
            "RESULT           : V8 TIES V3"
        )

    else:
        print(
            "RESULT           : V8 DOES NOT BEAT V3"
        )

    print()

    print(
        classification_report(
            y_val,
            best_pred,
            digits=4,
            zero_division=0,
        )
    )

    # =====================================================
    # SAVE EXPERIMENT RESULTS
    # =====================================================

    result_df = pd.DataFrame(
        experiments
    )

    result_df.to_csv(
        OUTPUT_RESULTS,
        index=False,
    )

    # =====================================================
    # SAVE ERRORS
    # =====================================================

    error_df = val.copy()

    error_df[
        "predicted_category"
    ] = best_pred

    wrong = error_df[
        error_df["category"]
        !=
        error_df["predicted_category"]
    ].copy()

    wrong.to_csv(
        OUTPUT_ERRORS,
        index=False,
    )

    print(
        f"Wrong predictions: {len(wrong)}"
    )

    # =====================================================
    # CONFUSION MATRIX
    # =====================================================

    labels = sorted(
        y_val.unique()
    )

    cm = confusion_matrix(
        y_val,
        best_pred,
        labels=labels,
    )

    cm_df = pd.DataFrame(
        cm,
        index=labels,
        columns=labels,
    )

    cm_df.to_csv(
        OUTPUT_MATRIX
    )

    # =====================================================
    # SAVE MODEL
    # =====================================================

    joblib.dump(
        {
            "pipeline": best_model,
            "version": "v8",
            "C": best_c,
            "accuracy": best_accuracy,
            "macro_f1": best_macro,
            "preprocessor": (
                "v3_hints_plus_v8_concepts"
            ),
        },
        OUTPUT_MODEL,
    )

    print()

    print(
        "Saved V8 model:"
    )

    print(
        OUTPUT_MODEL
    )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "Production V3 model was NOT overwritten."
    )

    if best_accuracy > V3_ACCURACY:
        print(
            "V8 is a candidate for production."
        )

    else:
        print(
            "Keep V3 as production."
        )


if __name__ == "__main__":
    main()