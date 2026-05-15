import re
from typing import List, Tuple

def validate_linkedin_content(text: str, topic: str = "") -> Tuple[bool, List[str]]:
    """
    Validates generated content against platform boundaries and spam rules.
    Returns (is_valid, list_of_validation_warnings)
    """
    warnings = []
    if not text:
        return False, ["Content is empty."]

    # 1. Max Length Validation (LinkedIn limit is 3000 chars, but 1800 is ideal for readability)
    if len(text) > 3000:
        warnings.append(f"Post length ({len(text)} chars) exceeds LinkedIn's maximum limit of 3000 characters.")
    elif len(text) > 2000:
        warnings.append("Post is quite long (over 2000 chars). Consider making it more concise.")

    # 2. Hashtag Validation (LinkedIn algorithm penalizes > 3-5 hashtags as search spam)
    hashtags = re.findall(r"#\w+", text)
    if len(hashtags) > 5:
        warnings.append(f"Spam Alert: Found {len(hashtags)} hashtags. Keep it under 5 to maintain organic reach.")
    
    # Check for duplicate consecutive hashtags
    if len(hashtags) != len(set(hashtags)):
        warnings.append("Duplicate hashtags detected.")

    # 3. Emoji Validation (Excessive emoji usage degrades professional readability)
    # Basic regex to count broad ranges of unicode emojis
    emoji_pattern = re.compile(r"[\U00010000-\U0010ffff]", flags=re.UNICODE)
    emojis = emoji_pattern.findall(text)
    if len(emojis) > 10:
        warnings.append(f"High emoji density detected ({len(emojis)} emojis). May appear unprofessional.")

    # 4. Formatting & Scannability Validation
    paragraphs = [p for p in text.split('\n') if p.strip()]
    for p in paragraphs:
        if len(p) > 400:
            warnings.append("Wall of text alert: One or more paragraphs are too long. Break them down with line breaks.")
            break

    # 5. Duplicate Detection (Simple heuristic checking if AI repeats the exact topic sentence)
    if topic and topic.lower() in text.lower():
        # Check if the title/topic is explicitly printed multiple times verbatim
        occurrences = text.lower().count(topic.lower())
        if occurrences > 3:
            warnings.append("High phrase repetition: The core topic text is repeated too frequently.")

    is_valid = len(warnings) == 0
    return is_valid, warnings