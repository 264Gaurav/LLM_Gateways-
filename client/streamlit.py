import json
from typing import Any, Dict, Optional

import requests
import streamlit as st


# ============================================================
# Page configuration
# ============================================================

st.set_page_config(
    page_title="LLM Gateway",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# Session state
# ============================================================

DEFAULT_SETTINGS = {
    "api_base": "http://localhost:8000",
    "api_key": "",
    "model": "gateway-model",
    "system_prompt": "You are a helpful assistant.",
    "stream": True,
    "temperature": 0.7,
    "top_p": 1.0,
    "max_tokens": 0,
}

if "settings" not in st.session_state:
    st.session_state.settings = DEFAULT_SETTINGS.copy()

if "draft_settings" not in st.session_state:
    st.session_state.draft_settings = st.session_state.settings.copy()

if "guardrail_messages" not in st.session_state:
    st.session_state.guardrail_messages = []

if "direct_messages" not in st.session_state:
    st.session_state.direct_messages = []

if "chat_mode" not in st.session_state:
    st.session_state.chat_mode = "guardrails"

if "settings_open" not in st.session_state:
    st.session_state.settings_open = False

if "busy" not in st.session_state:
    st.session_state.busy = False

if "last_error" not in st.session_state:
    st.session_state.last_error = None

if "last_health" not in st.session_state:
    st.session_state.last_health = None

if "embedding_result" not in st.session_state:
    st.session_state.embedding_result = None


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
<style>
#MainMenu, footer {visibility:hidden}

.block-container {
    max-width: 1100px;
    padding-top: 3.75rem !important;
    padding-bottom: 7rem;
}

/* Prevent application content from being placed underneath
   Streamlit's Deploy / toolbar area. */
header[data-testid="stHeader"] {
    z-index: 999;
}

.app-brand {
    display:flex;
    align-items:center;
    gap:.75rem;
    min-height:44px;
}

.app-mark {
    width:38px;
    height:38px;
    flex:0 0 38px;
    border:1px solid rgba(128,128,128,.25);
    border-radius:11px;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:18px;
    font-weight:700;
    background:rgba(128,128,128,.07);
}

.app-title {
    font-size:1.08rem;
    font-weight:700;
    line-height:1.15;
}

.app-subtitle {
    font-size:.76rem;
    color:rgba(128,128,128,.85);
    margin-top:.12rem;
}

.gateway-status {
    display:inline-flex;
    align-items:center;
    gap:.4rem;
    border:1px solid rgba(128,128,128,.20);
    border-radius:999px;
    padding:.32rem .65rem;
    font-size:.76rem;
    color:rgba(128,128,128,.95);
}

.mode-help {
    font-size:.84rem;
    color:rgba(128,128,128,.9);
    margin:-.15rem 0 .8rem;
}

[data-testid="stChatMessage"] {
    border-radius:14px;
    margin-bottom:.45rem;
}

[data-testid="stChatInput"] {
    margin-bottom:1rem;
}

.empty-state {
    text-align:center;
    padding:4.5rem 1rem 2rem;
    color:rgba(128,128,128,.9);
}

.empty-icon {
    font-size:2.3rem;
    margin-bottom:.4rem;
}

.empty-title {
    font-weight:650;
    font-size:1.05rem;
}

.empty-subtitle {
    font-size:.84rem;
    margin-top:.3rem;
}

.muted {
    font-size:.76rem;
    color:rgba(128,128,128,.78);
}

.saved-badge {
    font-size:.76rem;
    color:rgba(128,128,128,.85);
}
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# Settings helpers
# ============================================================

def settings_snapshot() -> Dict[str, Any]:
    return st.session_state.settings.copy()


def apply_draft_settings() -> None:
    """
    Explicitly commit the settings form to the active configuration.

    This is intentionally separate from widget state. Users can edit
    several fields and either Save or Discard without partially changing
    the active request configuration.
    """
    st.session_state.settings = st.session_state.draft_settings.copy()


def reset_draft_from_saved() -> None:
    st.session_state.draft_settings = st.session_state.settings.copy()


def gateway_url() -> str:
    return st.session_state.settings["api_base"].strip().rstrip("/")


def auth_headers() -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    api_key = st.session_state.settings["api_key"].strip()

    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    return headers


# ============================================================
# API response helpers
# ============================================================

def error_text(response: requests.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text.strip() or "No error details returned."

    if isinstance(body, dict):
        for key in ("reason", "detail", "message"):
            if body.get(key):
                value = body[key]
                if isinstance(value, dict):
                    return str(value.get("message") or value)
                return str(value)

        if body.get("error"):
            value = body["error"]
            if isinstance(value, dict):
                return str(value.get("message") or value)
            return str(value)

    return str(body)


def extract_content(data: Any) -> str:
    """
    Supports the gateway's response and common OpenAI/LiteLLM response
    structures.
    """
    if data is None:
        return ""

    if isinstance(data, str):
        return data

    if isinstance(data, dict):
        if data.get("content") is not None:
            return str(data["content"])

        choices = data.get("choices")

        if isinstance(choices, list) and choices:
            choice = choices[0] or {}

            message = choice.get("message")
            if isinstance(message, dict) and message.get("content") is not None:
                return str(message["content"])

            if choice.get("text") is not None:
                return str(choice["text"])

            delta = choice.get("delta")
            if isinstance(delta, dict) and delta.get("content") is not None:
                return str(delta["content"])

    return str(data)


def parse_sse_line(line: str) -> Optional[str]:
    """
    Supports:
      data: {"choices":[{"delta":{"content":"Hello"}}]}
      data: {"content":"Hello"}
      data: [DONE]
      plain text chunks
    """
    line = line.strip()

    if not line:
        return None

    if line.startswith("data:"):
        line = line[5:].strip()

    if line == "[DONE]":
        return "__DONE__"

    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return line

    if isinstance(data, str):
        return data

    if isinstance(data, dict):
        if data.get("content") is not None:
            return str(data["content"])

        delta = data.get("delta")

        if isinstance(delta, str):
            return delta

        choices = data.get("choices")

        if isinstance(choices, list) and choices:
            choice = choices[0] or {}

            delta = choice.get("delta")
            if isinstance(delta, dict) and delta.get("content") is not None:
                return str(delta["content"])

            if choice.get("text") is not None:
                return str(choice["text"])

    return None


# ============================================================
# API calls
# ============================================================

def call_chat(
    endpoint: str,
    messages: list,
    placeholder,
) -> tuple[str, Optional[str]]:
    """
    Chat API:
      Guardrails + LiteLLM -> POST /ai/llms
      Direct LiteLLM       -> POST /ai/litellm/chat

    Returns:
      (response_text, error_message)
    """
    settings = st.session_state.settings

    payload: Dict[str, Any] = {
        "model": settings["model"],
        "messages": messages,
        "temperature": float(settings["temperature"]),
        "top_p": float(settings["top_p"]),
        "n": 1,
        "stream": bool(settings["stream"]),
    }

    if int(settings["max_tokens"]) > 0:
        payload["max_tokens"] = int(settings["max_tokens"])

    text = ""

    try:
        if settings["stream"]:
            response = requests.post(
                f"{gateway_url()}{endpoint}",
                json=payload,
                headers=auth_headers(),
                stream=True,
                timeout=(10, 300),
            )

            if not response.ok:
                return "", (
                    f"Request failed ({response.status_code}): "
                    f"{error_text(response)}"
                )

            try:
                for raw_line in response.iter_lines(decode_unicode=True):
                    if not raw_line:
                        continue

                    chunk = parse_sse_line(raw_line)

                    if chunk == "__DONE__":
                        break

                    if chunk:
                        text += chunk
                        placeholder.markdown(text + "▌")
            finally:
                response.close()

        else:
            response = requests.post(
                f"{gateway_url()}{endpoint}",
                json=payload,
                headers=auth_headers(),
                timeout=(10, 120),
            )

            if not response.ok:
                return "", (
                    f"Request failed ({response.status_code}): "
                    f"{error_text(response)}"
                )

            try:
                data = response.json()
            except ValueError:
                data = {"content": response.text}

            text = extract_content(data)

        placeholder.markdown(
            text or "_The assistant returned an empty response._"
        )

        return text, None

    except requests.Timeout:
        return "", (
            "The request timed out. Check the gateway and model provider. "
            "The server may still be processing the request."
        )

    except requests.ConnectionError:
        return "", (
            "Could not connect to the gateway at "
            f"`{gateway_url()}`. Make sure the FastAPI server is running."
        )

    except requests.RequestException as exc:
        return "", f"Network request failed: {exc}"

    except Exception as exc:
        return "", f"Unexpected client error: {exc}"


def call_embeddings(text: str) -> tuple[Optional[dict], Optional[str]]:
    """
    Embeddings API:
      POST /ai/embeddings

    The gateway README specifies:
      {
        "model": "...",
        "input": "..."
      }
    """
    settings = st.session_state.settings

    # Embedding model is intentionally separate from chat model.
    embedding_model = st.session_state.get(
        "embedding_model",
        "text-embedding-3-small",
    )

    payload = {
        "model": embedding_model,
        "input": text,
    }

    try:
        response = requests.post(
            f"{gateway_url()}/ai/embeddings",
            json=payload,
            headers=auth_headers(),
            timeout=(10, 120),
        )

        if not response.ok:
            return None, (
                f"Embedding request failed ({response.status_code}): "
                f"{error_text(response)}"
            )

        try:
            return response.json(), None
        except ValueError:
            return None, "Embedding endpoint returned a non-JSON response."

    except requests.Timeout:
        return None, "Embedding request timed out."

    except requests.ConnectionError:
        return None, (
            f"Could not connect to the gateway at `{gateway_url()}`."
        )

    except requests.RequestException as exc:
        return None, f"Embedding request failed: {exc}"


def run_health_check() -> None:
    try:
        response = requests.get(
            f"{gateway_url()}/health",
            headers=auth_headers(),
            timeout=(5, 10),
        )

        if response.ok:
            try:
                data = response.json()
            except ValueError:
                data = {"response": response.text}

            st.session_state.last_health = {
                "ok": True,
                "data": data,
            }
        else:
            st.session_state.last_health = {
                "ok": False,
                "data": error_text(response),
                "status": response.status_code,
            }

    except requests.Timeout:
        st.session_state.last_health = {
            "ok": False,
            "data": "Health check timed out.",
        }

    except requests.ConnectionError:
        st.session_state.last_health = {
            "ok": False,
            "data": "Gateway is unreachable.",
        }

    except requests.RequestException as exc:
        st.session_state.last_health = {
            "ok": False,
            "data": str(exc),
        }


# ============================================================
# Chat helpers
# ============================================================

def current_history() -> list:
    if st.session_state.chat_mode == "guardrails":
        return st.session_state.guardrail_messages

    return st.session_state.direct_messages


def current_endpoint() -> str:
    if st.session_state.chat_mode == "guardrails":
        return "/ai/llms"

    return "/ai/litellm/chat"


def build_messages(history: list) -> list:
    messages = []

    system_prompt = st.session_state.settings["system_prompt"].strip()

    if system_prompt:
        messages.append(
            {
                "role": "system",
                "content": system_prompt,
            }
        )

    messages.extend(history)

    return messages


def render_history(history: list) -> None:
    for message in history:
        role = message.get("role")

        if role not in ("user", "assistant"):
            continue

        with st.chat_message(role):
            st.markdown(message.get("content", ""))


# ============================================================
# Header
# ============================================================

st.markdown(
    """
<div class="app-brand">
    <div class="app-mark">✦</div>
    <div>
        <div class="app-title">LLM Gateway</div>
        <div class="app-subtitle">Chat with your configured LLM</div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

header_left, header_right = st.columns(
    [8, 1],
    vertical_alignment="center",
)

with header_left:
    st.markdown(
        '<span class="gateway-status">● Gateway console</span>',
        unsafe_allow_html=True,
    )

with header_right:
    if st.button(
        "⚙",
        help="Open gateway and model settings",
        use_container_width=True,
        disabled=st.session_state.busy,
    ):
        # Always load the current saved settings when opening.
        reset_draft_from_saved()
        st.session_state.settings_open = not st.session_state.settings_open
        st.rerun()


# ============================================================
# Settings
# ============================================================

if st.session_state.settings_open:
    with st.container(border=True):
        st.markdown("### Settings")
        st.caption(
            "Edit configuration, then explicitly save it. Unsaved changes "
            "do not affect chat requests."
        )

        draft = st.session_state.draft_settings

        left, right = st.columns(2)

        with left:
            draft["api_base"] = st.text_input(
                "Gateway URL",
                value=draft["api_base"],
                key="draft_api_base",
                disabled=st.session_state.busy,
            )

            draft["api_key"] = st.text_input(
                "Bearer API key",
                value=draft["api_key"],
                type="password",
                key="draft_api_key",
                disabled=st.session_state.busy,
            )

            draft["model"] = st.text_input(
                "Chat model",
                value=draft["model"],
                key="draft_model",
                disabled=st.session_state.busy,
            )

        with right:
            draft["system_prompt"] = st.text_area(
                "System prompt",
                value=draft["system_prompt"],
                height=130,
                key="draft_system_prompt",
                disabled=st.session_state.busy,
            )

            draft["stream"] = st.toggle(
                "Stream responses",
                value=draft["stream"],
                key="draft_stream",
                disabled=st.session_state.busy,
            )

        with st.expander("Advanced generation"):
            a, b, c = st.columns(3)

            with a:
                draft["temperature"] = st.number_input(
                    "Temperature",
                    min_value=0.0,
                    max_value=2.0,
                    step=0.1,
                    value=float(draft["temperature"]),
                    key="draft_temperature",
                    disabled=st.session_state.busy,
                )

            with b:
                draft["top_p"] = st.number_input(
                    "Top P",
                    min_value=0.0,
                    max_value=1.0,
                    step=0.01,
                    value=float(draft["top_p"]),
                    key="draft_top_p",
                    disabled=st.session_state.busy,
                )

            with c:
                draft["max_tokens"] = st.number_input(
                    "Max tokens",
                    min_value=0,
                    step=1,
                    value=int(draft["max_tokens"]),
                    key="draft_max_tokens",
                    help="0 = do not send max_tokens.",
                    disabled=st.session_state.busy,
                )

        # Keep draft object synchronized with the actual widget values.
        st.session_state.draft_settings = draft

        save_col, discard_col, _ = st.columns([1, 1, 5])

        with save_col:
            if st.button(
                "Save settings",
                type="primary",
                use_container_width=True,
                disabled=st.session_state.busy,
            ):
                # Validate before committing.
                api_base = draft["api_base"].strip()

                if not api_base:
                    st.error("Gateway URL cannot be empty.")
                elif not (
                    api_base.startswith("http://")
                    or api_base.startswith("https://")
                ):
                    st.error(
                        "Gateway URL must start with http:// or https://."
                    )
                elif not draft["model"].strip():
                    st.error("Chat model cannot be empty.")
                else:
                    # Normalize values.
                    draft["api_base"] = api_base.rstrip("/")
                    draft["model"] = draft["model"].strip()
                    draft["api_key"] = draft["api_key"].strip()
                    draft["system_prompt"] = draft["system_prompt"].strip()
                    draft["temperature"] = float(draft["temperature"])
                    draft["top_p"] = float(draft["top_p"])
                    draft["max_tokens"] = int(draft["max_tokens"])

                    st.session_state.settings = draft.copy()
                    st.session_state.draft_settings = draft.copy()
                    st.session_state.settings_open = False

                    st.success("Settings saved successfully.")
                    st.rerun()

        with discard_col:
            if st.button(
                "Discard",
                use_container_width=True,
                disabled=st.session_state.busy,
            ):
                reset_draft_from_saved()
                st.session_state.settings_open = False
                st.rerun()


# ============================================================
# Feature navigation
# ============================================================

st.markdown("### Workspace")

feature = st.radio(
    "Feature",
    ["chat", "embeddings"],
    format_func=lambda value: (
        "💬 Chat"
        if value == "chat"
        else "🔢 Embeddings"
    ),
    horizontal=True,
    label_visibility="collapsed",
    disabled=st.session_state.busy,
)


# ============================================================
# CHAT
# ============================================================

if feature == "chat":

    st.markdown("#### Chat mode")

    selected_mode = st.radio(
        "Chat mode",
        ["guardrails", "direct"],
        format_func=lambda value: (
            "🛡️ Guardrails + LiteLLM"
            if value == "guardrails"
            else "⚡ Direct LiteLLM"
        ),
        horizontal=True,
        label_visibility="collapsed",
        disabled=st.session_state.busy,
    )

    if selected_mode != st.session_state.chat_mode:
        st.session_state.chat_mode = selected_mode
        st.rerun()

    if selected_mode == "guardrails":
        st.markdown(
            '<div class="mode-help">'
            "Protected path: <b>POST /ai/llms</b>. "
            "The request passes through Guardrails before LiteLLM."
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="mode-help">'
            "Baseline path: <b>POST /ai/litellm/chat</b>. "
            "The request bypasses the Guardrails layer."
            "</div>",
            unsafe_allow_html=True,
        )

    history = current_history()

    if not history:
        st.markdown(
            """
<div class="empty-state">
    <div class="empty-icon">✦</div>
    <div class="empty-title">Start a conversation</div>
    <div class="empty-subtitle">
        Ask a question to test the selected gateway path.
    </div>
</div>
""",
            unsafe_allow_html=True,
        )
    else:
        render_history(history)

    prompt = st.chat_input(
        "Message the assistant...",
        disabled=st.session_state.busy,
    )

    if prompt and prompt.strip() and not st.session_state.busy:
        prompt = prompt.strip()

        st.session_state.busy = True
        st.session_state.last_error = None

        history.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            placeholder = st.empty()

            if st.session_state.settings["stream"]:
                placeholder.markdown("_Connecting to the gateway…_")
            else:
                placeholder.markdown("_Waiting for the assistant…_")

            answer, error = call_chat(
                endpoint=current_endpoint(),
                messages=build_messages(history),
                placeholder=placeholder,
            )

        if error:
            st.session_state.last_error = error
            st.session_state.busy = False
            st.error(error)
        else:
            if answer:
                history.append(
                    {
                        "role": "assistant",
                        "content": answer,
                    }
                )

            st.session_state.busy = False

        st.rerun()

    if st.session_state.busy:
        st.info(
            "The assistant is processing your request. "
            "Chat controls are temporarily locked."
        )

    if history and not st.session_state.busy:
        c1, c2, _ = st.columns([1, 1, 6])

        with c1:
            if st.button("Clear", use_container_width=True):
                if selected_mode == "guardrails":
                    st.session_state.guardrail_messages = []
                else:
                    st.session_state.direct_messages = []

                st.session_state.last_error = None
                st.rerun()

        with c2:
            st.download_button(
                "Export",
                data=json.dumps(
                    history,
                    indent=2,
                    ensure_ascii=False,
                ),
                file_name=f"{selected_mode}-chat.json",
                mime="application/json",
                use_container_width=True,
            )

    if st.session_state.last_error and not st.session_state.busy:
        with st.expander("Last request details"):
            st.error(st.session_state.last_error)

    # --------------------------------------------------------
    # Guardrails comparison
    # --------------------------------------------------------

    st.divider()

    with st.expander("Compare Guardrails vs Direct LiteLLM"):
        st.caption(
            "The same prompt, system prompt and generation settings are "
            "sent independently to both chat endpoints."
        )

        compare_prompt = st.text_area(
            "Comparison prompt",
            height=110,
            placeholder="Enter one prompt to test both paths...",
            label_visibility="collapsed",
            disabled=st.session_state.busy,
        )

        if st.button(
            "Run comparison",
            type="primary",
            disabled=(
                st.session_state.busy
                or not compare_prompt.strip()
            ),
        ):
            st.session_state.busy = True
            st.session_state.last_error = None

            messages = []

            system = st.session_state.settings["system_prompt"].strip()

            if system:
                messages.append(
                    {
                        "role": "system",
                        "content": system,
                    }
                )

            messages.append(
                {
                    "role": "user",
                    "content": compare_prompt.strip(),
                }
            )

            left, right = st.columns(2)

            with left:
                st.markdown("**🛡️ Guardrails + LiteLLM**")
                p1 = st.empty()
                p1.markdown("_Running guarded path…_")

                guard_response, guard_error = call_chat(
                    "/ai/llms",
                    messages,
                    p1,
                )

                if guard_error:
                    st.error(guard_error)

            with right:
                st.markdown("**⚡ Direct LiteLLM**")
                p2 = st.empty()
                p2.markdown("_Running direct path…_")

                direct_response, direct_error = call_chat(
                    "/ai/litellm/chat",
                    messages,
                    p2,
                )

                if direct_error:
                    st.error(direct_error)

            st.session_state.busy = False

            if guard_error or direct_error:
                st.warning(
                    "One or both comparison requests did not complete."
                )
            else:
                st.caption(
                    "Both requests used the same configuration."
                )


# ============================================================
# EMBEDDINGS
# ============================================================

else:
    st.markdown("#### Generate embeddings")

    st.caption(
        "Embeddings use the guarded gateway endpoint "
        "`POST /ai/embeddings`."
    )

    embedding_model = st.text_input(
        "Embedding model",
        value=st.session_state.get(
            "embedding_model",
            "text-embedding-3-small",
        ),
        disabled=st.session_state.busy,
    )

    st.session_state.embedding_model = embedding_model.strip()

    embedding_text = st.text_area(
        "Text",
        height=180,
        placeholder="Enter text to convert into an embedding...",
        disabled=st.session_state.busy,
    )

    if st.button(
        "Generate embedding",
        type="primary",
        disabled=(
            st.session_state.busy
            or not embedding_text.strip()
        ),
    ):
        st.session_state.busy = True
        st.session_state.embedding_result = None

        with st.spinner("Generating embedding…"):
            data, error = call_embeddings(
                embedding_text.strip()
            )

        st.session_state.busy = False

        if error:
            st.error(error)
        else:
            st.session_state.embedding_result = data

    if st.session_state.embedding_result is not None:
        data = st.session_state.embedding_result

        st.success("Embedding generated successfully.")

        vector = None

        if isinstance(data, dict):
            items = data.get("data")

            if isinstance(items, list) and items:
                first = items[0]

                if isinstance(first, dict):
                    vector = first.get("embedding")

            if vector is None:
                vector = data.get("embedding")

        elif isinstance(data, list):
            vector = data

        if isinstance(vector, list):
            st.metric("Vector dimensions", len(vector))

            with st.expander("View vector"):
                st.json(vector)

        with st.expander("Raw API response"):
            st.json(data)


# ============================================================
# Gateway status
# ============================================================

st.divider()

with st.expander("Gateway status"):
    st.caption(
        f"Current endpoint base: `{gateway_url()}`"
    )

    if st.button(
        "Check gateway",
        disabled=st.session_state.busy,
    ):
        run_health_check()

    health = st.session_state.last_health

    if health is None:
        st.caption("No health check has been run yet.")
    elif health["ok"]:
        st.success("Gateway is reachable.")
        st.json(health["data"])
    else:
        st.error(str(health["data"]))


# ============================================================
# Footer
# ============================================================

st.markdown(
    '<div class="muted" style="text-align:center;margin-top:2rem;">'
    "FastAPI Gateway · Guardrails · LiteLLM"
    "</div>",
    unsafe_allow_html=True,
)




# import json
# from typing import Any, Dict, Optional

# import requests
# import streamlit as st


# # ============================================================
# # Page
# # ============================================================

# st.set_page_config(
#     page_title="LLM Gateway",
#     page_icon="✦",
#     layout="centered",
#     initial_sidebar_state="collapsed",
# )


# # ============================================================
# # Session state
# # ============================================================

# DEFAULT_STATE = {
#     "messages": [],
#     "guardrail_messages": [],
#     "direct_messages": [],
#     "chat_mode": "guardrails",
#     "stream": True,
#     "settings_open": False,
# }

# for key, value in DEFAULT_STATE.items():
#     if key not in st.session_state:
#         st.session_state[key] = value


# # ============================================================
# # CSS — deliberately restrained, chat-product style
# # ============================================================

# st.markdown(
#     """
#     <style>
#     #MainMenu, footer { visibility: hidden; }

#     .block-container {
#         max-width: 900px;
#         padding-top: 1rem;
#         padding-bottom: 7rem;
#     }

#     /* Header */
#     .app-header {
#         display: flex;
#         align-items: center;
#         justify-content: space-between;
#         margin-bottom: 1rem;
#     }

#     .brand {
#         display: flex;
#         align-items: center;
#         gap: .65rem;
#     }

#     .brand-mark {
#         width: 34px;
#         height: 34px;
#         border-radius: 10px;
#         display: flex;
#         align-items: center;
#         justify-content: center;
#         font-size: 18px;
#         font-weight: 700;
#         border: 1px solid rgba(128,128,128,.25);
#         background: rgba(128,128,128,.07);
#     }

#     .brand-title {
#         font-size: 1.05rem;
#         font-weight: 700;
#         line-height: 1.1;
#     }

#     .brand-subtitle {
#         color: rgba(128,128,128,.85);
#         font-size: .75rem;
#     }

#     /* Mode cards */
#     .mode-description {
#         color: rgba(128,128,128,.9);
#         font-size: .84rem;
#         margin-top: -.25rem;
#         margin-bottom: .8rem;
#     }

#     /* Chat */
#     [data-testid="stChatMessage"] {
#         border-radius: 14px;
#         margin-bottom: .45rem;
#     }

#     [data-testid="stChatInput"] {
#         margin-bottom: 1rem;
#     }

#     /* Settings panel */
#     .settings-note {
#         color: rgba(128,128,128,.85);
#         font-size: .8rem;
#     }

#     /* Comparison */
#     .compare-title {
#         font-size: 1rem;
#         font-weight: 700;
#         margin-bottom: .25rem;
#     }

#     .compare-subtitle {
#         color: rgba(128,128,128,.85);
#         font-size: .8rem;
#         margin-bottom: .8rem;
#     }

#     /* Small footer text */
#     .muted {
#         color: rgba(128,128,128,.8);
#         font-size: .78rem;
#     }
#     </style>
#     """,
#     unsafe_allow_html=True,
# )


# # ============================================================
# # Helpers
# # ============================================================

# def base_url() -> str:
#     return st.session_state.get("api_base", "http://localhost:8000").strip().rstrip("/")


# def headers() -> Dict[str, str]:
#     result = {"Content-Type": "application/json"}
#     key = st.session_state.get("api_key", "").strip()
#     if key:
#         result["Authorization"] = f"Bearer {key}"
#     return result


# def extract_content(data: Any) -> str:
#     if data is None:
#         return ""

#     if isinstance(data, str):
#         return data

#     if isinstance(data, dict):
#         if data.get("content") is not None:
#             return str(data["content"])

#         choices = data.get("choices")
#         if isinstance(choices, list) and choices:
#             choice = choices[0] or {}

#             message = choice.get("message")
#             if isinstance(message, dict) and message.get("content") is not None:
#                 return str(message["content"])

#             if choice.get("text") is not None:
#                 return str(choice["text"])

#             delta = choice.get("delta")
#             if isinstance(delta, dict) and delta.get("content") is not None:
#                 return str(delta["content"])

#         error = data.get("error")
#         if error:
#             return str(error.get("message") if isinstance(error, dict) else error)

#     return str(data)


# def parse_sse_line(line: str) -> Optional[str]:
#     line = line.strip()

#     if not line:
#         return None

#     if line.startswith("data:"):
#         line = line[5:].strip()

#     if line == "[DONE]":
#         return "__DONE__"

#     try:
#         data = json.loads(line)
#     except json.JSONDecodeError:
#         return line

#     if isinstance(data, str):
#         return data

#     if isinstance(data, dict):
#         if data.get("content") is not None:
#             return str(data["content"])

#         if isinstance(data.get("delta"), str):
#             return data["delta"]

#         choices = data.get("choices")
#         if isinstance(choices, list) and choices:
#             choice = choices[0] or {}
#             delta = choice.get("delta")

#             if isinstance(delta, dict) and delta.get("content") is not None:
#                 return str(delta["content"])

#             if choice.get("text") is not None:
#                 return str(choice["text"])

#     return None


# def api_error(response: requests.Response) -> str:
#     try:
#         body = response.json()
#     except ValueError:
#         return response.text

#     if isinstance(body, dict):
#         if body.get("reason"):
#             return str(body["reason"])
#         if body.get("detail"):
#             return str(body["detail"])
#         if body.get("error"):
#             error = body["error"]
#             return str(error.get("message") if isinstance(error, dict) else error)

#     return str(body)


# def request_chat(
#     endpoint: str,
#     messages: list,
#     placeholder,
# ) -> str:
#     payload: Dict[str, Any] = {
#         "model": st.session_state["model"],
#         "messages": messages,
#         "stream": st.session_state["stream"],
#         "temperature": st.session_state["temperature"],
#         "top_p": st.session_state["top_p"],
#         "n": 1,
#     }

#     if st.session_state["max_tokens"] > 0:
#         payload["max_tokens"] = st.session_state["max_tokens"]

#     assistant_text = ""

#     try:
#         if st.session_state["stream"]:
#             response = requests.post(
#                 f"{base_url()}{endpoint}",
#                 json=payload,
#                 headers=headers(),
#                 stream=True,
#                 timeout=(10, 300),
#             )

#             if not response.ok:
#                 st.error(
#                     f"Request failed ({response.status_code}): "
#                     f"{api_error(response)}"
#                 )
#                 return ""

#             for raw in response.iter_lines(decode_unicode=True):
#                 if not raw:
#                     continue

#                 chunk = parse_sse_line(raw)

#                 if chunk == "__DONE__":
#                     break

#                 if chunk:
#                     assistant_text += chunk
#                     placeholder.markdown(assistant_text + "▌")

#             placeholder.markdown(
#                 assistant_text or "_No response content returned._"
#             )

#         else:
#             response = requests.post(
#                 f"{base_url()}{endpoint}",
#                 json=payload,
#                 headers=headers(),
#                 timeout=(10, 120),
#             )

#             if not response.ok:
#                 st.error(
#                     f"Request failed ({response.status_code}): "
#                     f"{api_error(response)}"
#                 )
#                 return ""

#             try:
#                 data = response.json()
#             except ValueError:
#                 data = {"content": response.text}

#             assistant_text = extract_content(data)
#             placeholder.markdown(
#                 assistant_text or "_No response content returned._"
#             )

#     except requests.RequestException as exc:
#         st.error(f"Unable to reach the gateway: {exc}")

#     return assistant_text


# def render_messages(messages: list) -> None:
#     for message in messages:
#         role = message["role"]
#         content = message["content"]

#         with st.chat_message("user" if role == "user" else "assistant"):
#             st.markdown(content)


# # ============================================================
# # Header
# # ============================================================

# header_left, header_right = st.columns([6, 1])

# with header_left:
#     st.markdown(
#         """
#         <div class="brand">
#             <div class="brand-mark">✦</div>
#             <div>
#                 <div class="brand-title">LLM Gateway</div>
#                 <div class="brand-subtitle">Chat with your configured LLM</div>
#             </div>
#         </div>
#         """,
#         unsafe_allow_html=True,
#     )

# with header_right:
#     if st.button(
#         "⚙",
#         help="Chat and gateway settings",
#         use_container_width=True,
#     ):
#         st.session_state["settings_open"] = not st.session_state["settings_open"]


# # ============================================================
# # Settings — intentionally hidden behind the gear
# # ============================================================

# if st.session_state["settings_open"]:
#     with st.container(border=True):
#         st.markdown("### Settings")
#         st.caption(
#             "Configuration is hidden by default so the normal chat stays simple."
#         )

#         s1, s2 = st.columns(2)

#         with s1:
#             st.text_input(
#                 "Gateway URL",
#                 value=st.session_state.get(
#                     "api_base", "http://localhost:8000"
#                 ),
#                 key="api_base",
#             )

#             st.text_input(
#                 "Bearer API key",
#                 value=st.session_state.get("api_key", ""),
#                 type="password",
#                 key="api_key",
#             )

#             st.text_input(
#                 "Model",
#                 value=st.session_state.get("model", "gateway-model"),
#                 key="model",
#             )

#         with s2:
#             st.text_area(
#                 "System prompt",
#                 value=st.session_state.get(
#                     "system_prompt",
#                     "You are a helpful assistant.",
#                 ),
#                 height=125,
#                 key="system_prompt",
#             )

#             st.toggle(
#                 "Stream responses",
#                 value=st.session_state.get("stream", True),
#                 key="stream",
#             )

#         with st.expander("Advanced generation"):
#             a1, a2, a3 = st.columns(3)

#             with a1:
#                 st.number_input(
#                     "Temperature",
#                     min_value=0.0,
#                     max_value=2.0,
#                     value=st.session_state.get("temperature", 0.7),
#                     step=0.1,
#                     key="temperature",
#                 )

#             with a2:
#                 st.number_input(
#                     "Top P",
#                     min_value=0.0,
#                     max_value=1.0,
#                     value=st.session_state.get("top_p", 1.0),
#                     step=0.01,
#                     key="top_p",
#                 )

#             with a3:
#                 st.number_input(
#                     "Max tokens",
#                     min_value=0,
#                     value=st.session_state.get("max_tokens", 0),
#                     step=1,
#                     key="max_tokens",
#                     help="0 = backend default.",
#                 )

#         st.markdown(
#             '<div class="settings-note">'
#             "Changes apply to the next message."
#             "</div>",
#             unsafe_allow_html=True,
#         )


# # ============================================================
# # Feature selection
# # ============================================================

# st.markdown("### Chat mode")

# mode = st.radio(
#     "Choose how the message is processed",
#     options=["guardrails", "direct"],
#     format_func=lambda value: (
#         "🛡️ Guardrails + LiteLLM"
#         if value == "guardrails"
#         else "⚡ Direct LiteLLM"
#     ),
#     horizontal=True,
#     label_visibility="collapsed",
# )

# if mode != st.session_state["chat_mode"]:
#     st.session_state["chat_mode"] = mode

# if mode == "guardrails":
#     st.markdown(
#         '<div class="mode-description">'
#         "Safety checks are applied before the request reaches the LLM. "
#         "Use this mode to see the protected gateway behavior."
#         "</div>",
#         unsafe_allow_html=True,
#     )
#     endpoint = "/ai/llms"
# else:
#     st.markdown(
#         '<div class="mode-description">'
#         "The request goes directly through LiteLLM without the Guardrails layer. "
#         "Use this mode as a baseline for comparison."
#         "</div>",
#         unsafe_allow_html=True,
#     )
#     endpoint = "/ai/litellm/chat"


# # ============================================================
# # Chat
# # ============================================================

# if not st.session_state["guardrail_messages"] and not st.session_state["direct_messages"]:
#     st.markdown(
#         """
#         <div style="
#             text-align:center;
#             padding:4rem 1rem 2rem 1rem;
#             color:rgba(128,128,128,.9);
#         ">
#             <div style="font-size:2.2rem;">✦</div>
#             <div style="font-size:1.1rem;font-weight:600;margin-top:.5rem;">
#                 Start a conversation
#             </div>
#             <div style="font-size:.85rem;margin-top:.3rem;">
#                 Ask anything to test the selected gateway path.
#             </div>
#         </div>
#         """,
#         unsafe_allow_html=True,
#     )


# current_messages = (
#     st.session_state["guardrail_messages"]
#     if mode == "guardrails"
#     else st.session_state["direct_messages"]
# )

# render_messages(current_messages)


# # ============================================================
# # Composer
# # ============================================================

# prompt = st.chat_input(
#     "Message the assistant...",
# )

# if prompt:
#     prompt = prompt.strip()

#     if prompt:
#         history = (
#             st.session_state["guardrail_messages"]
#             if mode == "guardrails"
#             else st.session_state["direct_messages"]
#         )

#         user_message = {
#             "role": "user",
#             "content": prompt,
#         }

#         history.append(user_message)

#         with st.chat_message("user"):
#             st.markdown(prompt)

#         llm_messages = []

#         system_prompt = st.session_state.get("system_prompt", "").strip()

#         if system_prompt:
#             llm_messages.append(
#                 {
#                     "role": "system",
#                     "content": system_prompt,
#                 }
#             )

#         # Preserve only conversation turns for the request.
#         llm_messages.extend(history)

#         with st.chat_message("assistant"):
#             response_placeholder = st.empty()

#             assistant_text = request_chat(
#                 endpoint=endpoint,
#                 messages=llm_messages,
#                 placeholder=response_placeholder,
#             )

#         if assistant_text:
#             history.append(
#                 {
#                     "role": "assistant",
#                     "content": assistant_text,
#                 }
#             )

#         st.rerun()


# # ============================================================
# # Conversation controls
# # ============================================================

# active_history = (
#     st.session_state["guardrail_messages"]
#     if mode == "guardrails"
#     else st.session_state["direct_messages"]
# )

# if active_history:
#     c1, c2, c3 = st.columns([1, 1, 4])

#     with c1:
#         if st.button("Clear", use_container_width=True):
#             if mode == "guardrails":
#                 st.session_state["guardrail_messages"] = []
#             else:
#                 st.session_state["direct_messages"] = []
#             st.rerun()

#     with c2:
#         export_data = json.dumps(
#             active_history,
#             indent=2,
#             ensure_ascii=False,
#         )

#         st.download_button(
#             "Export",
#             data=export_data,
#             file_name=f"{mode}-chat.json",
#             mime="application/json",
#             use_container_width=True,
#         )


# # ============================================================
# # Compare mode
# # ============================================================

# st.divider()

# with st.expander("Compare Guardrails vs Direct LiteLLM"):
#     st.markdown(
#         '<div class="compare-subtitle">'
#         "Run the same prompt through both paths and inspect how their behavior differs."
#         "</div>",
#         unsafe_allow_html=True,
#     )

#     compare_prompt = st.text_area(
#         "Prompt",
#         height=100,
#         placeholder="Enter one prompt to send through both paths...",
#         label_visibility="collapsed",
#     )

#     if st.button(
#         "Run comparison",
#         type="primary",
#         disabled=not compare_prompt.strip(),
#     ):
#         comparison_messages = []

#         system_prompt = st.session_state.get("system_prompt", "").strip()

#         if system_prompt:
#             comparison_messages.append(
#                 {
#                     "role": "system",
#                     "content": system_prompt,
#                 }
#             )

#         comparison_messages.append(
#             {
#                 "role": "user",
#                 "content": compare_prompt.strip(),
#             }
#         )

#         left, right = st.columns(2)

#         with left:
#             st.markdown(
#                 '<div class="compare-title">🛡️ Guardrails + LiteLLM</div>',
#                 unsafe_allow_html=True,
#             )

#             guard_placeholder = st.empty()

#             guard_response = request_chat(
#                 endpoint="/ai/llms",
#                 messages=comparison_messages,
#                 placeholder=guard_placeholder,
#             )

#         with right:
#             st.markdown(
#                 '<div class="compare-title">⚡ Direct LiteLLM</div>',
#                 unsafe_allow_html=True,
#             )

#             direct_placeholder = st.empty()

#             direct_response = request_chat(
#                 endpoint="/ai/litellm/chat",
#                 messages=comparison_messages,
#                 placeholder=direct_placeholder,
#             )

#         if guard_response or direct_response:
#             st.caption(
#                 "This comparison is a behavioral test; it does not bypass "
#                 "the configured server-side authorization."
#             )


# # ============================================================
# # Minimal footer
# # ============================================================

# st.markdown(
#     '<div class="muted" style="text-align:center;margin-top:2rem;">'
#     "FastAPI Gateway · Guardrails · LiteLLM"
#     "</div>",
#     unsafe_allow_html=True,
# )
