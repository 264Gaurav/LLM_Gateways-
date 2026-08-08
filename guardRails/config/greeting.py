import re
from nemoguardrails.actions import action
from logger import get_logger

logger = get_logger(__name__)

GREETING_OPENERS = [
    "hello",
    "hi",
    "hey",
    "hiya",
    "yo",
    "greetings",
    "good morning",
    "good afternoon",
    "good evening",
]

SMALL_TALK_SUFFIXES = [
    "what's up",
    "whats up",
    "how are you",
    "how's it going",
    "what's going on",
    "what's new",
    "sup",
    "how are things",
    "howdy",
]

THANKS_PHRASES = [
    "thanks",
    "thank you",
    "thank you very much",
    "thank you so much",
    "thanks a lot",
    "thanks so much",
]


def is_simple_greeting(text: str) -> bool:
    normalized = re.sub(r"[\s!?.,]+$", "", text.strip().lower())
    return normalized in GREETING_OPENERS or normalized in THANKS_PHRASES


def is_small_talk_after_greeting(text: str) -> bool:
    normalized = text.strip().lower()
    opener_pattern = r"^" + r"|".join(re.escape(item) for item in GREETING_OPENERS)
    opener_match = re.match(opener_pattern, normalized)
    if not opener_match:
        return False

    remainder = normalized[opener_match.end():].strip(" ,.!?")
    if not remainder:
        return True

    if remainder in SMALL_TALK_SUFFIXES:
        return True

    if len(remainder.split()) <= 3 and re.search(r"\b(what|whats|what's|how|sup|up|you|new)\b", remainder):
        return True

    return False


@action(name="check_greeting_terms")
async def check_greeting_terms(context: dict = None, user_input: str = None) -> bool:
    message = user_input or (context.get("last_user_message") if context else "") or ""
    if not message.strip():
        return False

    cleaned_input = message.strip().lower()
    if is_simple_greeting(cleaned_input) or is_small_talk_after_greeting(cleaned_input):
        logger.info("Detected greeting/small talk phrase: %s", cleaned_input)
        return True

    return False
