import re
from nemoguardrails.actions import action
from logger import get_logger

logger = get_logger(__name__)

@action(name="check_greeting_terms")
async def check_greeting_terms(context: dict = None, user_input: str = None) -> bool:
    message = user_input or (context.get("last_user_message") if context else "") or ""
    if not message.strip():
        return False

    cleaned_input = message.strip().lower()
    greeting_patterns = [
        r"^(hello|hi|hey|hiya|yo|greetings|good morning|good afternoon|good evening)\b",
        r"\b(thanks|thank you|thank you very much|thank you so much)\b"
    ]

    for pat in greeting_patterns:
        if re.search(pat, cleaned_input):
            logger.info("Detected greeting phrase: %s", cleaned_input)
            return True

    return False
