"""Custom NeMo Guardrails actions with centralized logging."""

import re
from nemoguardrails.actions import action
from logger import get_logger

logger = get_logger(__name__)

BLOCKED_PATTERNS = [
    r"(?i)ignore\s+previous\s+instructions",
    r"(?i)system\s+prompt",
    r"(?i)drop\s+table",
    r"(?i)eval\(",
]

@action(name="check_blocked_terms")
async def check_blocked_terms(user_input: str) -> bool:
    logger.info(f"Evaluating local regex check for input: '{user_input}'")
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, user_input):
            logger.warning(f"Input triggered blocked pattern '{pattern}': '{user_input}'")
            return True
    logger.info("Input passed local pattern checks.")
    return False



# from nemoguardrails.actions import action
# import re

# # Fast local regex check (Cost: $0, Execution: <1ms)
# BLOCKED_PATTERNS = [
#     r"(?i)ignore\s+previous\s+instructions",
#     r"(?i)system\s+prompt",
#     r"(?i)drop\s+table",
#     r"(?i)eval\(",
# ]

# @action(name="check_blocked_terms")
# async def check_blocked_terms(user_input: str):
#     for pattern in BLOCKED_PATTERNS:
#         if re.search(pattern, user_input):
#             return True  # Term is blocked
#     return False