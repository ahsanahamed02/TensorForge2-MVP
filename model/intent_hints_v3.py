import re


def add_intent_hints(text):
    lower = str(text).lower()
    hints = []

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
        r"\bparcel la vaikkala\b",
        r"\bparcel la illa\b",
        r"\border la illa\b",
        r"\bitem varala\b",
        r"\bitem missing\b",
        r"\bfood missing\b",
        r"\bdrink missing\b",
        r"பொட்டலத்தில் வைக்கவில்லை",
        r"பார்சலில் இல்லை",
        r"ஆர்டரில் இல்லை",
        r"தவறான உணவு",
        r"පාර්සලයට දාලා නැහැ",
        r"ඇණවුමේ නැහැ",
    ]

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
        r"\brefund venum\b",
        r"\bmoney return\b",
        r"\bkaasu thiruppi\b",
        r"\bamount thiruppi\b",
        r"\btwice charge\b",
        r"பணம்.*திருப்ப",
        r"கட்டணம்",
        r"பணம் திரும்ப",
        r"මුදල්.*ආපසු",
        r"ගෙවීම",
    ]

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
        r"\border varala\b",
        r"\bfood varala\b",
        r"\blate ah varuthu\b",
        r"\bdelivery late\b",
        r"இன்னும் வரவில்லை",
        r"தாமத",
        r"டெலிவரி.*வரவில்லை",
        r"තවම.*ආවේ නැහැ",
        r"ප්‍රමාද",
    ]

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
        r"\bapp work aagala\b",
        r"\bapp open aagala\b",
        r"\blogin panna mudiyala\b",
        r"\berror varuthu\b",
        r"உள்நுழைய முடியவில்லை",
        r"செயலி.*வேலை செய்யவில்லை",
        r"பிழை",
        r"ලොග්.*වෙන්න බැහැ",
        r"ඇප්.*වැඩ කරන්නේ නැහැ",
    ]

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
        r"\bfood cold\b",
        r"\btaste sari illa\b",
        r"\bfood nalla illa\b",
        r"\bquality sari illa\b",
        r"உணவு.*குளிர",
        r"சுவை.*சரியில்லை",
        r"உணவு.*கெட்ட",
        r"කෑම.*සීතල",
        r"රස.*නැහැ",
    ]

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
        r"\bphone vittuten\b",
        r"\bbag vittuten\b",
        r"\bitem maranthuten\b",
        r"\blost aachu\b",
    ]

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

    if "__ORDER_ISSUE_HINT" in hints and "__PAYMENT_HINT" in hints:
        hints.append("__ORDER_AND_PAYMENT")

    if "__ORDER_ISSUE_HINT" in hints and "__DELIVERY_HINT" not in hints:
        hints.append("__ORDER_CONTENT_PROBLEM")

    if "__DELIVERY_HINT" in hints and "__ORDER_ISSUE_HINT" not in hints:
        hints.append("__PURE_DELIVERY_PROBLEM")

    return " ".join(hints)