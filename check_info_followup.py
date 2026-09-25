from langsmith import traceable

REQUIRED_FIELDS = [
    "emergency_type",
    "location",
    "people_involved",
    "injuries",
]

MISSING_VALUES = {"Unknown", "", None}


@traceable(name="checkMissingFields")
def check_missing_fields(current_info, previous_info):
    """Merge the latest extraction with existing incident state.

    Only factual caller-provided fields are required. Severity is a derived field
    and is therefore never requested from the caller.
    """

    merged_info = previous_info.copy()

    for field in REQUIRED_FIELDS:
        current_value = current_info.get(field, "Unknown")

        # A new explicit value replaces the previous value, which also allows
        # callers to correct information on later turns.
        if current_value not in MISSING_VALUES:
            merged_info[field] = current_value
        elif field not in merged_info:
            merged_info[field] = "Unknown"

    missing_fields = [
        field
        for field in REQUIRED_FIELDS
        if merged_info.get(field, "Unknown") in MISSING_VALUES
    ]

    return merged_info, missing_fields


@traceable(name="askFollowup")
def ask_follow(missing_fields):
    follow_questions = {
        "emergency_type": "What type of emergency is it?",
        "location": "What is the exact location?",
        "people_involved": "How many people are involved?",
        "injuries": (
            "How many people are injured? If you know, also mention whether anyone "
            "is unconscious, not breathing, bleeding heavily, trapped, or seriously hurt."
        ),
    }

    return [
        follow_questions[field]
        for field in missing_fields
        if field in follow_questions
    ]