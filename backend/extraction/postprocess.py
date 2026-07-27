import re
from typing import Any


def clean_string(text: str) -> str:
    """
    Clean unwanted characters from extracted strings.
    """

    if not isinstance(text, str):
        return text

    # Remove control characters
    text = re.sub(r"[\x00-\x1F\x7F]", "", text)

    # Remove zero-width characters
    text = text.replace("\u200b", "")
    text = text.replace("\ufeff", "")

    # Remove multiple spaces
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def clean_json(data: Any):
    """
    Recursively clean every string in a JSON object.
    """

    if isinstance(data, dict):
        return {
            key: clean_json(value)
            for key, value in data.items()
        }

    if isinstance(data, list):

        cleaned = []

        seen = set()

        for item in data:

            value = clean_json(item)

            key = str(value)

            if key not in seen:
                seen.add(key)
                cleaned.append(value)

        return cleaned

    if isinstance(data, str):
        return clean_string(data)

    return data