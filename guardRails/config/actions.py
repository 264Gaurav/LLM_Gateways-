import os
import re
import httpx
from nemoguardrails.actions import action
from logger import get_logger

logger = get_logger(__name__)

LITELLM_ENDPOINT = "http://localhost:4000/v1/chat/completions"

# Retrieve master key from environment or fallback to local key
LITELLM_API_KEY = os.environ.get("LITELLM_MASTER_KEY", "your-actual-master-key-here")

HAZARD_MAP = {
    "S1": "Violent Crimes",
    "S2": "Non-Violent Crimes",
    "S3": "Sex-Related Crimes",
    "S4": "Child Sexual Exploitation",
    "S5": "Defamation",
    "S6": "Specialized Advice",
    "S7": "Privacy",
    "S8": "Intellectual Property",
    "S9": "Indiscriminate Weapons",
    "S10": "Hate",
    "S11": "Suicide & Self-Harm",
    "S12": "Sexual Content",
    "S13": "Elections"
}


@action(name="check_greeting_terms")
async def check_greeting_terms(user_input: str) -> bool:
    """
    Evaluates incoming user text locally for standard greetings
    without triggering an LLM call.
    """
    if not user_input:
        return False

    greetings = {"hello", "hi", "hey", "good morning", "good evening", "good afternoon"}
    cleaned_input = user_input.strip().lower()
    
    is_greeting = cleaned_input in greetings
    if is_greeting:
        logger.info(f"[Input Rail] Local greeting detected for input: '{user_input}'")
    return is_greeting


@action(name="check_blocked_terms")
async def check_blocked_terms(user_input: str) -> bool:
    """
    Evaluates incoming user text against local regex patterns for basic off-topic
    or adversarial phrases without triggering an LLM call.
    """
    if not user_input:
        return False

    blocked_patterns = [
        r"\bhow to build a bomb\b",
        r"\bhack a database\b",
        r"\bignore previous instructions\b",
        r"\boverride safety rules\b",
    ]
    
    lowered_input = user_input.lower()
    for pattern in blocked_patterns:
        if re.search(pattern, lowered_input):
            logger.warning(f"[Input Rail] Blocked phrase detected via regex matching pattern: '{pattern}'")
            return True

    return False


@action(name="check_llama_guard_input")
async def check_llama_guard_input(context: dict) -> dict:
    """
    Runs Llama Guard 3 1B classification via local LiteLLM proxy.
    """
    user_message = context.get("user_message", "")
    logger.info(f"[Input Rail] Evaluating Llama Guard 3 1B classification for: '{user_message}'")
    
    payload = {
        "model": "llama-guard-3-1b",
        "messages": [
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.0
    }
    
    headers = {
        "Authorization": f"Bearer {LITELLM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                LITELLM_ENDPOINT, 
                json=payload, 
                headers=headers, 
                timeout=5.0
            )
            response.raise_for_status()
            
            res_data = response.json()
            raw_content = res_data["choices"][0]["message"]["content"].strip()
            
            logger.info(f"[Llama Guard 3 1B Raw Output]: '{raw_content}'")
            
            if "unsafe" in raw_content.lower():
                lines = raw_content.split("\n")
                detected_hazards = []
                
                for line in lines:
                    code = line.strip().upper()
                    if code in HAZARD_MAP:
                        detected_hazards.append(f"{code}: {HAZARD_MAP[code]}")
                
                hazard_str = ", ".join(detected_hazards) if detected_hazards else "Unspecified Hazard"
                logger.warning(f"[Input Rail] Blocked by local Llama Guard 3 1B: {hazard_str}")
                
                return {
                    "is_safe": False,
                    "hazards": hazard_str
                }
                
            return {"is_safe": True, "hazards": ""}
            
        except Exception as e:
            logger.error(f"[Input Rail] Local Llama Guard 3 1B call failed: {e}")
            return {"is_safe": True, "hazards": ""}





# import os
# import httpx
# from nemoguardrails.actions import action
# from logger import get_logger

# logger = get_logger(__name__)

# LITELLM_ENDPOINT = "http://localhost:4000/v1/chat/completions"

# # Retrieve master key from environment or fallback to your explicit key
# LITELLM_API_KEY = os.environ.get("LITELLM_MASTER_KEY", "your-actual-master-key-here")

# HAZARD_MAP = {
#     "S1": "Violent Crimes",
#     "S2": "Non-Violent Crimes",
#     "S3": "Sex-Related Crimes",
#     "S4": "Child Sexual Exploitation",
#     "S5": "Defamation",
#     "S6": "Specialized Advice",
#     "S7": "Privacy",
#     "S8": "Intellectual Property",
#     "S9": "Indiscriminate Weapons",
#     "S10": "Hate",
#     "S11": "Suicide & Self-Harm",
#     "S12": "Sexual Content",
#     "S13": "Elections"
# }

# @action(name="check_llama_guard_input")
# async def check_llama_guard_input(context: dict) -> dict:
#     user_message = context.get("user_message", "")
#     logger.info(f"[Input Rail] Evaluating Llama Guard 3 1B classification for: '{user_message}'")
    
#     payload = {
#         "model": "llama-guard-3-1b",
#         "messages": [
#             {"role": "user", "content": user_message}
#         ],
#         "temperature": 0.0
#     }
    
#     # Add Authorization Header
#     headers = {
#         "Authorization": f"Bearer {LITELLM_API_KEY}",
#         "Content-Type": "application/json"
#     }
    
#     async with httpx.AsyncClient() as client:
#         try:
#             response = await client.post(
#                 LITELLM_ENDPOINT, 
#                 json=payload, 
#                 headers=headers, 
#                 timeout=5.0
#             )
#             response.raise_for_status()  # Raises HTTPStatusError if 4xx/5xx status
            
#             res_data = response.json()
#             raw_content = res_data["choices"][0]["message"]["content"].strip()
            
#             logger.info(f"[Llama Guard 3 1B Raw Output]: '{raw_content}'")
            
#             if "unsafe" in raw_content.lower():
#                 lines = raw_content.split("\n")
#                 detected_hazards = []
                
#                 for line in lines:
#                     code = line.strip().upper()
#                     if code in HAZARD_MAP:
#                         detected_hazards.append(f"{code}: {HAZARD_MAP[code]}")
                
#                 hazard_str = ", ".join(detected_hazards) if detected_hazards else "Unspecified Hazard"
#                 logger.warning(f"[Input Rail] Blocked by local Llama Guard 3 1B: {hazard_str}")
                
#                 return {
#                     "is_safe": False,
#                     "hazards": hazard_str
#                 }
                
#             return {"is_safe": True, "hazards": ""}
            
#         except Exception as e:
#             logger.error(f"[Input Rail] Local Llama Guard 3 1B call failed: {e}")
#             return {"is_safe": True, "hazards": ""}
