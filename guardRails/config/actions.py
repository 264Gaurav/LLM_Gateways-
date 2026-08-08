import os
import re
import httpx
from nemoguardrails.actions import action
from logger import get_logger
from dotenv import load_dotenv

logger = get_logger(__name__)
load_dotenv()

LITELLM_ENDPOINT = os.environ.get("LITELLM_ENDPOINT", "http://localhost:4000/v1/chat/completions")
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
async def check_greeting_terms(context: dict = None, user_input: str = None) -> bool:
    message = user_input or (context.get("last_user_message") if context else "") or ""
    if not message.strip():
        return False

    greetings = {
        "hello", "hi", "hey", "good morning", "good evening", "good afternoon",
        "thanks", "thank you", "thank you!", "thank you very much", "thank you so much"
    }
    cleaned_input = message.strip().lower()
    return cleaned_input in greetings


@action(name="check_blocked_terms")
async def check_blocked_terms(context: dict = None, user_input: str = None) -> bool:
    message = user_input or (context.get("last_user_message") if context else "") or ""
    if not message.strip():
        return False

    blocked_patterns = [
        r"\bhow to build a bomb\b",
        r"\bhack a database\b",
        r"\bhack a bank account\b",
        r"\bbypass transaction limits\b",
        r"\bbypass fraud detection\b",
        r"\bignore previous instructions\b",
        r"\boverride safety rules\b",
    ]
    
    lowered_input = message.lower()
    for pattern in blocked_patterns:
        if re.search(pattern, lowered_input):
            return True

    return False


@action(name="check_pii_and_mask")
async def check_pii_and_mask(context: dict = None, user_input: str = None) -> dict:
    message = user_input or (context.get("last_user_message") if context else "") or ""
    if not message.strip():
        return {
            "is_safe": True,
            "hazards": "",
            "masked_input": "",
            "message": ""
        }

    secret_patterns = [
        r"\bapi[_-]?key\b",
        r"\bsecret\b",
        r"\btoken\b",
        r"sk-[A-Za-z0-9_-]{16,}\b",
        r"ghp_[A-Za-z0-9_-]{36,}",
        r"xox[baprs]-[A-Za-z0-9-]{10,}",
    ]
    lowered_input = message.lower()
    for pattern in secret_patterns:
        if re.search(pattern, lowered_input):
            return {
                "is_safe": False,
                "hazards": "PII / Secret Detected",
                "masked_input": "",
                "message": "Detected a secret or API key in your request. Please remove it before retrying."
            }

    masked_input = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[EMAIL_REDACTED]", message)
    masked_input = re.sub(r"\b(?:\+?\d[\d\s().-]{7,}\d)\b", "[PHONE_REDACTED]", masked_input)
    masked_input = re.sub(r"\b\d{3}[- ]?\d{2}[- ]?\d{4}\b", "[SSN_REDACTED]", masked_input)

    return {
        "is_safe": True,
        "hazards": "",
        "masked_input": masked_input,
        "message": ""
    }


@action(name="check_llama_guard_input")
async def check_llama_guard_input(context: dict = None, user_input: str = None) -> dict:
    # Resolution Priority:
    # 1. Directly passed user_input (if valid string and not literal parameter name)
    # 2. Context 'masked_user_input'
    # 3. Context 'last_user_message'
    message = None
    if user_input and user_input != "$masked_input" and user_input != "$masked_user_input":
        message = user_input

    if not message and context:
        message = (
            context.get("masked_user_input")
            or context.get("last_user_message")
            or context.get("user_message")
        )

    message = (message or "").strip()

    if not message:
        logger.warning("[Input Rail] Empty or unresolved message in check_llama_guard_input; skipping.")
        return {"is_safe": True, "hazards": ""}

    logger.info(f"[Input Rail] Evaluating Llama Guard 3 for: '{message}'")
    
    payload = {
        "model": "llama-guard-3-1b",
        "messages": [
            {"role": "user", "content": message}
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
                timeout=15.0  # Increased timeout for local inference calls
            )
            response.raise_for_status()
            
            res_data = response.json()
            raw_content = res_data["choices"][0]["message"]["content"].strip()
            
            logger.info(f"[Llama Guard Raw Output]: '{raw_content}'")
            
            normalized = raw_content.strip().lower()
            codes = set(re.findall(r"\b(s\d{1,2})\b", normalized, flags=re.IGNORECASE))

            if "unsafe" in normalized or codes:
                detected_hazards = []
                for code in sorted(codes, key=lambda x: int(x[1:])):
                    code_up = code.upper()
                    if code_up in HAZARD_MAP:
                        detected_hazards.append(f"{code_up}: {HAZARD_MAP[code_up]}")

                hazard_str = ", ".join(detected_hazards) if detected_hazards else "Unspecified Hazard"
                logger.warning(f"[Input Rail] Blocked by Llama Guard: {hazard_str}")

                return {
                    "is_safe": False,
                    "hazards": hazard_str
                }

            return {"is_safe": True, "hazards": ""}
            
        except Exception as e:
            logger.error(f"[Input Rail] Local Llama Guard call failed: {e}")
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
