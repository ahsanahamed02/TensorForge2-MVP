from pathlib import Path
import re

import joblib
import pandas as pd

from model.train_category_v8 import (
    build_text as build_category_text_v8,
)


# =========================================================
# PATH
# =========================================================

BASE_DIR = Path(__file__).resolve().parent


# =========================================================
# LOAD MODELS
# =========================================================

category_model_data = joblib.load(
    BASE_DIR / "category_model_v8.joblib"
)

category_model = category_model_data["pipeline"]

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
# LEGIT RECEIPT / INVOICE MESSAGE
# =========================================================

def is_legit_receipt_message(subject, text):
    combined = f"{subject or ''} {text or ''}".lower()

    legit_patterns = [
        r"\bview.*receipt\b",
        r"\bview.*invoice\b",
        r"\bsee.*receipt\b",
        r"\bsee.*invoice\b",
        r"\border.*successful\b",
        r"\bpurchase.*successful\b",
        r"\bcompleted.*order\b",
        r"\bcompletion.*order\b",
    ]

    return any(
        re.search(pattern, combined, re.IGNORECASE)
        for pattern in legit_patterns
    )


# =========================================================
# SPAM DETECTION
# =========================================================

def is_obvious_spam(subject, text):
    combined = f"{subject or ''} {text or ''}".lower()

    prize_patterns = [
        r"\byou have won\b",
        r"\byou've won\b",
        r"\bwon a prize\b",
        r"\bcash prize\b",
        r"\bfree prize\b",
        r"\bprize winner\b",
        r"\bselected as (a )?winner\b",
        r"\bcongratulations.*won\b",
        r"\bcongratulations.*winner\b",
    ]

    action_patterns = [
        r"\bclick here\b",
        r"\bclick now\b",
        r"\bclaim now\b",
        r"\bclaim your prize\b",
        r"\bclaim.*reward\b",
        r"\bredeem now\b",
    ]

    suspicious_patterns = [
        r"\bfree cash\b",
        r"\bguaranteed prize\b",
        r"\binstant cash prize\b",
        r"\byou are a winner\b",
    ]

    has_prize_signal = any(
        re.search(pattern, combined, re.IGNORECASE)
        for pattern in prize_patterns
    )

    has_action_signal = any(
        re.search(pattern, combined, re.IGNORECASE)
        for pattern in action_patterns
    )

    has_strong_signal = any(
        re.search(pattern, combined, re.IGNORECASE)
        for pattern in suspicious_patterns
    )

    if has_strong_signal:
        return True

    if has_prize_signal and has_action_signal:
        return True

    return False


# =========================================================
# SAFETY NEGATION
# =========================================================

def has_safety_negation(subject, text):
    combined = f"{subject or ''} {text or ''}".lower()

    negation_patterns = [
        # English
        r"\bnot unsafe\b",
        r"\bnever felt unsafe\b",
        r"\bdid not feel unsafe\b",
        r"\bdidn't feel unsafe\b",
        r"\bno safety problem\b",
        r"\bwithout any safety problem\b",
        r"\bdid not threaten\b",
        r"\bdidn't threaten\b",
        r"\bwas not threatened\b",
        r"\bnot threatened\b",
        r"\breached safely\b",
        r"\breached my destination safely\b",
        r"\bwithout any problem\b",
        r"\bsafely without any problem\b",

        # Tanglish
        r"\bunsafe feel aagala\b",
        r"\bunsafe ah feel aagala\b",
        r"\bunsafe nu feel aagala\b",
        r"\bunsafe feel pannala\b",
        r"\bunsafe ah feel pannala\b",
        r"\bunsafe nu feel pannala\b",
        r"\bunsafe illa\b",
        r"\bsafe ah reach\b",
        r"\bsafe ah destination\b",
        r"\bsafe ah reach pann",

        # Tamil transliteration
        r"\bunsafe.*aagavillai\b",
        r"\bunsafe.*illai\b",

        # Singlish
        r"\bunsafe.*naha\b",
        r"\bunsafe.*nehe\b",
        r"\bunsafe.*hithune naha\b",
        r"\bunsafe.*hithune nehe\b",
    ]

    return any(
        re.search(pattern, combined, re.IGNORECASE)
        for pattern in negation_patterns
    )


# =========================================================
# DRIVER / RIDE CONTEXT
# =========================================================

def has_driver_context(subject, text):
    combined = f"{subject or ''} {text or ''}".lower()

    driver_patterns = [
        r"\bdriver\b",
        r"\brider\b",
        r"\btaxi\b",
        r"\bvehicle\b",
        r"\btrip\b",
        r"\bride\b",
    ]

    return any(
        re.search(pattern, combined, re.IGNORECASE)
        for pattern in driver_patterns
    )


# =========================================================
# SAFE RIDE CONTEXT
# =========================================================

def is_safe_ride_context(subject, text):
    return (
        has_driver_context(subject, text)
        and has_safety_negation(subject, text)
    )


# =========================================================
# SAFETY CATEGORY
# =========================================================

def is_obvious_safety_category(subject, text):
    combined = f"{subject or ''} {text or ''}".lower()

    if has_safety_negation(subject, text):
        return False

    strong_safety_patterns = [
        r"\bthreat\b",
        r"\bthreatened\b",
        r"\bthreatening\b",
        r"\bthreaten(?:ed|ing)?\b",
        r"\bthreaten pann(?:aru|anga|an)?\b",
        r"\bthreat pann(?:aru|anga|an)?\b",

        r"\bharassed\b",
        r"\bharassment\b",
        r"\babusive\b",
        r"\bunsafe\b",
        r"\bviolence\b",
        r"\bviolent\b",
        r"\battack\b",
        r"\battacked\b",
        r"\binappropriate\b",

        r"\bfelt threatened\b",
        r"\bfeel threatened\b",

        # Driver
        r"\bdriver.*shouting\b",
        r"\bdriver.*shouted\b",
        r"\bdriver.*yelling\b",
        r"\bdriver.*yelled\b",
        r"\bdriver.*abusive\b",
        r"\bdriver.*inappropriate\b",
        r"\bdriver.*scared\b",

        # Rider
        r"\brider.*shouting\b",
        r"\brider.*shouted\b",
        r"\brider.*yelling\b",
        r"\brider.*yelled\b",
        r"\brider.*abusive\b",
        r"\brider.*inappropriate\b",
        r"\brider.*scared\b",

        r"\bscared.*driver\b",
        r"\bscared.*rider\b",
        r"\bfelt scared during the trip\b",

        r"\bromba unsafe\b",
        r"\bromba bayama\b",
        r"\bbayama irundhuchu\b",
        r"\bbayama iruku\b",
    ]

    return any(
        re.search(pattern, combined, re.IGNORECASE)
        for pattern in strong_safety_patterns
    )


# =========================================================
# SAFETY URGENCY
# =========================================================

def is_obvious_safety_urgent(subject, text):
    combined = f"{subject or ''} {text or ''}".lower()

    if has_safety_negation(subject, text):
        return False

    urgent_safety_patterns = [
        r"\bthreat\b",
        r"\bthreatened\b",
        r"\bthreatening\b",
        r"\bthreaten(?:ed|ing)?\b",
        r"\bthreaten pann(?:aru|anga|an)?\b",
        r"\bthreat pann(?:aru|anga|an)?\b",

        r"\bunsafe\b",
        r"\bdanger\b",
        r"\bdangerous\b",
        r"\bviolence\b",
        r"\bviolent\b",
        r"\bharassed\b",
        r"\bharassment\b",
        r"\battack\b",
        r"\battacked\b",

        r"\bfelt threatened\b",
        r"\bfeel threatened\b",
        r"\bscared for my safety\b",

        # Driver
        r"\bdriver.*shouting\b",
        r"\bdriver.*shouted\b",
        r"\bdriver.*yelling\b",
        r"\bdriver.*yelled\b",
        r"\bdriver.*scared\b",

        # Rider
        r"\brider.*shouting\b",
        r"\brider.*shouted\b",
        r"\brider.*yelling\b",
        r"\brider.*yelled\b",
        r"\brider.*scared\b",

        r"\bscared.*driver\b",
        r"\bscared.*rider\b",
        r"\bfelt scared during the trip\b",

        r"\baggressively\b",
        r"\bunsafe ah\b",
        r"\bbayama iruku\b",
        r"\bbayama irundhuchu\b",
        r"\bromba bayama\b",
    ]

    return any(
        re.search(pattern, combined, re.IGNORECASE)
        for pattern in urgent_safety_patterns
    )


# =========================================================
# DUPLICATE PAYMENT
# =========================================================

def is_obvious_duplicate_payment(subject, text):
    combined = f"{subject or ''} {text or ''}".lower()

    patterns = [
        r"\bcharged twice\b",
        r"\bcharged two times\b",
        r"\bcharged double\b",
        r"\bdouble charged\b",
        r"\bduplicate charge\b",
        r"\bduplicate payment\b",
        r"\bamount.*twice\b",
        r"\bamount.*two times\b",
        r"\bdeduct(?:ed)?.*twice\b",
        r"\bdeduct(?:ed)?.*two times\b",
        r"\btwo times.*deduct\b",
        r"\btwice.*deduct\b",
        r"\bdeparak.*kapila\b",
    ]

    return any(
        re.search(pattern, combined, re.IGNORECASE)
        for pattern in patterns
    )


# =========================================================
# LOST ITEM
# =========================================================

def is_obvious_lost_item(subject, text):
    combined = f"{subject or ''} {text or ''}".lower()

    patterns = [
        r"\bleft my .* in the car\b",
        r"\bleft my .* in the vehicle\b",
        r"\bleft my .* in the taxi\b",
        r"\bleft my .* in the driver's car\b",
        r"\bleft .* after the ride\b",
        r"\bforgot my .* in the car\b",
        r"\bforgot my .* in the vehicle\b",
        r"\bforgot my .* in the taxi\b",
        r"\bvittuten\b",
        r"\bvittu vandhuten\b",
        r"\bmarandhuten\b",
        r"\bdala awilla\b",
    ]

    return any(
        re.search(pattern, combined, re.IGNORECASE)
        for pattern in patterns
    )


# =========================================================
# DELIVERY DELAY
# =========================================================

def is_obvious_delivery_delay(subject, text):
    combined = f"{subject or ''} {text or ''}".lower()

    patterns = [
        r"\border.*late\b",
        r"\border.*delayed\b",
        r"\bdelivery.*late\b",
        r"\bdelivery.*delayed\b",
        r"\bwhole order.*not arrived\b",
        r"\bwhole order.*still not arrived\b",
        r"\border.*still.*not arrived\b",
        r"\border.*still on the way\b",
        r"\bstill on the way\b",
        r"\bwhole order.*varala\b",
        r"\border full ah.*varala\b",
        r"\brider.*not moving\b",
        r"\brider.*movement.*illa\b",
        r"\border eka.*late\b",
        r"\border eka.*parakku\b",
        r"\bgodak parakku\b",
        r"\bgodak late\b",
        r"\border.*varala\b",
        r"\bdelivery.*varala\b",
    ]

    return any(
        re.search(pattern, combined, re.IGNORECASE)
        for pattern in patterns
    )


# =========================================================
# APP DATA / UPDATE ISSUE
# =========================================================

def is_obvious_app_data_issue(subject, text):
    combined = f"{subject or ''} {text or ''}".lower()

    app_signal = re.search(
        r"\b(app|application|update|reinstall|install)\b",
        combined,
        re.IGNORECASE
    )

    data_signal = re.search(
        r"\b(data|account data|saved data|saved cards|delete|disappear|lost|missing)\b",
        combined,
        re.IGNORECASE
    )

    return bool(app_signal and data_signal)


# =========================================================
# TECHNICAL CATEGORY
# =========================================================

def is_obvious_technical(subject, text):
    combined = f"{subject or ''} {text or ''}".lower()

    technical_patterns = [
        r"\bapp work aagala\b",
        r"\bapp open aagala\b",
        r"\bapp crash\b",
        r"\bapp crashed\b",
        r"\bapp crashes\b",
        r"\bapp crashing\b",
        r"\bapplication crash\b",
        r"\bapp freeze\b",
        r"\bapp freezes\b",
        r"\bapp frozen\b",

        r"\blogin panna mudiyala\b",
        r"\blogin aagala\b",
        r"\blogin problem\b",
        r"\blogin issue\b",
        r"\bcannot log ?in\b",
        r"\bcan't log ?in\b",
        r"\bcant log ?in\b",

        r"\berror varuthu\b",
        r"\berror message\b",
        r"\bserver error\b",
        r"\bscreen blank\b",
        r"\bblank screen\b",
        r"\bpage load aagala\b",
        r"\bnot loading\b",
        r"\bnot opening\b",
        r"\btechnical issue\b",
        r"\bbug\b",
        r"\bglitch\b",

        r"\bprofile.*error\b",
        r"\berror.*profile\b",
        r"\bprofile.*not loading\b",
        r"\bprofile.*blank\b",
        r"\bprofile.*crash(?:es|ing|ed)?\b",
        r"\bpage.*error\b",
        r"\bpage.*crash(?:es|ing|ed)?\b",
    ]

    return any(
        re.search(pattern, combined, re.IGNORECASE)
        for pattern in technical_patterns
    )


# =========================================================
# ORDER-MISSING / WRONG ITEM
# =========================================================

def is_obvious_order_missing(subject, text):
    combined = f"{subject or ''} {text or ''}".lower()

    if is_legit_receipt_message(subject, text):
        return False

    order_missing_patterns = [
        r"\bfries varala\b",
        r"\bdrink varala\b",
        r"\bdessert varala\b",
        r"\bitem varala\b",
        r"\bfood item varala\b",

        r"\bone item missing\b",
        r"\btwo items missing\b",
        r"\bitem missing\b",
        r"\bmissing item\b",

        r"\bnot in the bag\b",
        r"\bnot in my order\b",
        r"\bmissing from the bag\b",
        r"\bmissing from my order\b",
        r"\bmissing from the package\b",

        r"\bwrong item\b",
        r"\bwrong food\b",
        r"\bwrong order\b",
        r"\bwrong burger\b",
        r"\bwrong drink\b",
    ]

    return any(
        re.search(pattern, combined, re.IGNORECASE)
        for pattern in order_missing_patterns
    )


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
# CONFIDENCE INDICATOR
# =========================================================

def get_confidence_indicator(
    category_text,
    selected_category
):
    decision_scores = category_model.decision_function(
        [category_text]
    )

    scores = decision_scores[0]
    max_score = max(scores)

    exp_scores = pd.Series(
        scores
    ).apply(
        lambda value: pow(
            2.718281828,
            value - max_score
        )
    )

    indicators = (
        exp_scores /
        exp_scores.sum()
    )

    try:
        classes = list(
            category_model.classes_
        )

        selected_index = classes.index(
            selected_category
        )

        confidence = float(
            indicators.iloc[selected_index]
        )

    except (
        AttributeError,
        ValueError,
        IndexError,
    ):
        confidence = float(
            indicators.max()
        )

    return round(
        max(
            0.0,
            min(
                1.0,
                confidence
            )
        ),
        4
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

    model_text = build_text(
        channel,
        subject,
        text
    )

    category_text = build_category_text(
        channel,
        subject,
        text
    )

    # -----------------------------------------------------
    # BASE ML CATEGORY
    # -----------------------------------------------------

    primary = str(
        category_model.predict(
            [category_text]
        )[0]
    )

    # -----------------------------------------------------
    # LEGIT RECEIPT / INVOICE
    # -----------------------------------------------------

    legit_receipt = is_legit_receipt_message(
        subject,
        text
    )

    if legit_receipt:
        primary = "general_inquiry"

    # -----------------------------------------------------
    # SAFE RIDE CONTEXT
    # -----------------------------------------------------

    safe_ride = is_safe_ride_context(
        subject,
        text
    )

    if safe_ride:
        primary = "ride_trip_issue"

    # -----------------------------------------------------
    # DUPLICATE PAYMENT
    # -----------------------------------------------------

    if is_obvious_duplicate_payment(
        subject,
        text
    ):
        primary = "payment_refund"

    # -----------------------------------------------------
    # LOST ITEM
    # -----------------------------------------------------

    if is_obvious_lost_item(
        subject,
        text
    ):
        primary = "lost_item"

    # -----------------------------------------------------
    # DELIVERY DELAY
    # -----------------------------------------------------

    if is_obvious_delivery_delay(
        subject,
        text
    ):
        primary = "delivery_delay"

    # -----------------------------------------------------
    # ORDER MISSING / WRONG ITEM
    # -----------------------------------------------------

    if is_obvious_order_missing(
        subject,
        text
    ):
        primary = "order_missing_wrong"

    # -----------------------------------------------------
    # APP DATA ISSUE
    # -----------------------------------------------------

    if is_obvious_app_data_issue(
        subject,
        text
    ):
        primary = "app_technical"

    # -----------------------------------------------------
    # TECHNICAL
    # -----------------------------------------------------

    if is_obvious_technical(
        subject,
        text
    ):
        primary = "app_technical"

    # -----------------------------------------------------
    # SAFETY
    # -----------------------------------------------------

    if (
        not safe_ride
        and is_obvious_safety_category(
            subject,
            text
        )
    ):
        primary = "safety_conduct"

    # -----------------------------------------------------
    # SPAM FINAL PRIORITY
    # -----------------------------------------------------

    if is_obvious_spam(
        subject,
        text
    ):
        primary = "spam_irrelevant"

    # -----------------------------------------------------
    # URGENCY MODEL
    # -----------------------------------------------------

    urgent = bool(
        urgency_model.predict(
            [model_text]
        )[0]
    )

    # -----------------------------------------------------
    # SAFE RIDE → NORMAL
    # -----------------------------------------------------

    if safe_ride:
        urgent = False

    # -----------------------------------------------------
    # LEGIT RECEIPT → NORMAL
    # -----------------------------------------------------

    if legit_receipt:
        urgent = False

    # -----------------------------------------------------
    # SAFETY → URGENT
    # -----------------------------------------------------

    if (
        primary == "safety_conduct"
        and is_obvious_safety_urgent(
            subject,
            text
        )
    ):
        urgent = True

    # -----------------------------------------------------
    # SECONDARY DETECTION
    # -----------------------------------------------------

    has_secondary = bool(
        secondary_detector.predict(
            [model_text]
        )[0]
    )

    secondary = None

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

        if secondary == primary:
            secondary = None

    # -----------------------------------------------------
    # SPAM BEHAVIOUR
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
    # -----------------------------------------------------

    confidence = get_confidence_indicator(
        category_text,
        primary
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
        "model_version": "v1.2",
    }