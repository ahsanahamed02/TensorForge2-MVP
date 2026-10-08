from pathlib import Path

import joblib
import pandas as pd

from model.train_category_v8 import build_text as build_category_text_v8


# =========================================================
# PATH
# =========================================================

BASE_DIR = Path(__file__).resolve().parent


# =========================================================
# LOAD MODELS
# =========================================================

# V8 category model is saved inside a dictionary
category_model_data = joblib.load(
    BASE_DIR / "category_model_v8.joblib"
)

category_model = category_model_data["pipeline"]


# Existing production models
urgency_model = joblib.load(
    BASE_DIR / "urgency_model.joblib"
)

secondary_detector = joblib.load(
    BASE_DIR / "secondary_detector.joblib"
)

secondary_label_model = joblib.load(
    BASE_DIR / "secondary_label_model.joblib"
)


# =========================================================
# TEAM ROUTING
# =========================================================

TEAM_MAP = {
    "payment_refund": "Payments & Refunds",
    "ride_trip_issue": "Ride Operations",
    "lost_item": "Lost & Found",
    "order_missing_wrong": "Food Operations",
    "delivery_delay": "Delivery Operations",
    "food_quality": "Restaurant Quality",
    "account_promo": "Account Services",
    "safety_conduct": "Trust & Safety",
    "app_technical": "Tech Support",
    "general_inquiry": "Front-line Support",
    "spam_irrelevant": "Auto-close / Spam Filter",
}


# =========================================================
# OLD TEXT FORMAT
# Used for urgency + secondary models
# =========================================================

def build_text(channel, subject, text):
    subject = subject or ""
    text = text or ""
    channel = channel or ""

    return (
        f"__CHANNEL_{channel} "
        f"{subject} "
        f"{text}"
    )


# =========================================================
# V8 CATEGORY TEXT FORMAT
# IMPORTANT:
# Must match exactly how category_model_v8 was trained.
# =========================================================

def build_category_text(channel, subject, text):
    row = {
        "channel": channel or "",
        "subject": subject or "",
        "text": text or "",
    }

    return build_category_text_v8(row)


# =========================================================
# SECONDARY TEXT FORMAT
# =========================================================

def build_secondary_text(
    channel,
    subject,
    text,
    primary
):
    subject = subject or ""
    text = text or ""
    channel = channel or ""

    return (
        f"__PRIMARY_{primary} "
        f"__CHANNEL_{channel} "
        f"{subject} "
        f"{text}"
    )


# =========================================================
# MAIN PREDICTION
# =========================================================

def predict_ticket(
    channel,
    subject,
    text
):
    channel = channel or ""
    subject = subject or ""
    text = text or ""

    # -----------------------------------------------------
    # OLD TEXT
    # Urgency + secondary models were trained with this
    # -----------------------------------------------------

    model_text = build_text(
        channel,
        subject,
        text
    )

    # -----------------------------------------------------
    # V8 TEXT
    # Primary category model
    # -----------------------------------------------------

    category_text = build_category_text(
        channel,
        subject,
        text
    )

    # -----------------------------------------------------
    # PRIMARY CATEGORY
    # -----------------------------------------------------

    primary = str(
        category_model.predict(
            [category_text]
        )[0]
    )

    # -----------------------------------------------------
    # URGENCY
    # -----------------------------------------------------

    urgent = bool(
        urgency_model.predict(
            [model_text]
        )[0]
    )

    # -----------------------------------------------------
    # SECONDARY DETECTION
    # -----------------------------------------------------

    has_secondary = bool(
        secondary_detector.predict(
            [model_text]
        )[0]
    )

    secondary = None

    # -----------------------------------------------------
    # SECONDARY CATEGORY
    # -----------------------------------------------------

    if (
        has_secondary
        and primary != "spam_irrelevant"
    ):
        secondary_text = build_secondary_text(
            channel,
            subject,
            text,
            primary
        )

        secondary = str(
            secondary_label_model.predict(
                [secondary_text]
            )[0]
        )

        # Do not return same primary + secondary category
        if secondary == primary:
            secondary = None

    # -----------------------------------------------------
    # SPAM RULE
    # -----------------------------------------------------

    if primary == "spam_irrelevant":
        secondary = None
        urgent = False

    # -----------------------------------------------------
    # ROUTING TEAM
    # -----------------------------------------------------

    team = TEAM_MAP.get(
        primary,
        "Front-line Support"
    )

    # -----------------------------------------------------
    # CONFIDENCE INDICATOR
    #
    # NOTE:
    # LinearSVC does not output calibrated probability.
    # We convert decision scores using softmax only as a
    # confidence indicator.
    # -----------------------------------------------------

    decision_scores = category_model.decision_function(
        [category_text]
    )

    scores = decision_scores[0]

    # Numerical stability:
    # subtract max before exponential calculation
    max_score = max(scores)

    exp_scores = pd.Series(
        scores
    ).apply(
        lambda value: pow(
            2.718281828,
            value - max_score
        )
    )

    probabilities = (
        exp_scores /
        exp_scores.sum()
    )

    confidence = float(
        probabilities.max()
    )

    confidence = round(
        max(
            0.0,
            min(
                1.0,
                confidence
            )
        ),
        4
    )

    # -----------------------------------------------------
    # OUTPUT
    # -----------------------------------------------------

    return {
        "category": primary,
        "secondary_category": secondary,
        "team": team,
        "is_urgent": urgent,
        "confidence": confidence,
        "model_version": "v1.2"
    }