from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import requests


# ============================================================
# Configuration
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

LITELLM_DIR = ROOT / "litellm-setup"
STREAMLIT_APP = ROOT / "client" / "streamlit.py"

FASTAPI_HOST = "127.0.0.1"
FASTAPI_PORT = 8000

STREAMLIT_HOST = "127.0.0.1"
STREAMLIT_PORT = 8501

LITELLM_HOST = "127.0.0.1"
LITELLM_PORT = 4000

FASTAPI_HEALTH_URL = (
    f"http://{FASTAPI_HOST}:{FASTAPI_PORT}/health"
)

COMPOSE_FILE = LITELLM_DIR / "docker-compose.yml"


# ============================================================
# Process state
# ============================================================

fastapi_process: subprocess.Popen | None = None
streamlit_process: subprocess.Popen | None = None

shutdown_requested = False


# ============================================================
# Logging
# ============================================================

def log(message: str) -> None:
    print(f"[DEV] {message}", flush=True)


def error(message: str) -> None:
    print(f"[DEV][ERROR] {message}", flush=True)


# ============================================================
# Utility
# ============================================================

def run_command(
    command: list[str],
    cwd: Path | None = None,
) -> subprocess.CompletedProcess:

    log(f"Running: {' '.join(command)}")

    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        check=False,
    )


def port_available(host: str, port: int) -> bool:
    try:
        with socket.create_connection(
            (host, port),
            timeout=1,
        ):
            return True
    except OSError:
        return False


def wait_for_port(
    host: str,
    port: int,
    timeout: int = 120,
) -> bool:

    log(f"Waiting for {host}:{port}...")

    deadline = time.time() + timeout

    while time.time() < deadline:

        if port_available(host, port):
            log(f"{host}:{port} is available.")
            return True

        time.sleep(1)

    error(
        f"Timed out waiting for {host}:{port} "
        f"after {timeout} seconds."
    )

    return False


def wait_for_http(
    url: str,
    timeout: int = 120,
) -> bool:

    log(f"Waiting for service: {url}")

    deadline = time.time() + timeout

    while time.time() < deadline:

        try:
            response = requests.get(
                url,
                timeout=3,
            )

            if response.ok:
                log(f"Service is healthy: {url}")
                return True

        except requests.RequestException:
            pass

        time.sleep(1)

    error(
        f"Timed out waiting for service: {url}"
    )

    return False


# ============================================================
# Docker / LiteLLM
# ============================================================

def start_litellm() -> bool:

    if not COMPOSE_FILE.exists():
        error(
            f"Docker Compose file not found:\n"
            f"{COMPOSE_FILE}"
        )
        return False

    log("Starting LiteLLM Docker stack...")

    result = run_command(
        [
            "docker",
            "compose",
            "up",
            "-d",
        ],
        cwd=LITELLM_DIR,
    )

    if result.returncode != 0:
        error(
            "Failed to start LiteLLM Docker stack."
        )
        return False

    if not wait_for_port(
        LITELLM_HOST,
        LITELLM_PORT,
        timeout=180,
    ):
        return False

    log("LiteLLM stack is running.")

    return True


# ============================================================
# FastAPI
# ============================================================

def start_fastapi() -> bool:

    global fastapi_process

    log("Starting FastAPI...")

    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "server.main:app",
        "--host",
        FASTAPI_HOST,
        "--port",
        str(FASTAPI_PORT),

        # IMPORTANT:
        # Do not use --reload in the orchestrated launcher.
        #
        # It creates another process and complicates process
        # lifecycle management on Windows.
    ]

    fastapi_process = subprocess.Popen(
        command,
        cwd=str(ROOT),
    )

    log(
        f"FastAPI process started "
        f"(PID={fastapi_process.pid})"
    )

    if not wait_for_http(
        FASTAPI_HEALTH_URL,
        timeout=180,
    ):
        error(
            "FastAPI did not become healthy."
        )

        return False

    log("FastAPI is healthy.")

    return True


# ============================================================
# Streamlit
# ============================================================

def start_streamlit() -> bool:

    global streamlit_process

    if not STREAMLIT_APP.exists():
        error(
            f"Streamlit application not found:\n"
            f"{STREAMLIT_APP}"
        )
        return False

    log("Starting Streamlit...")

    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(STREAMLIT_APP),
        "--server.address",
        STREAMLIT_HOST,
        "--server.port",
        str(STREAMLIT_PORT),
        "--browser.gatherUsageStats",
        "false",
    ]

    streamlit_process = subprocess.Popen(
        command,
        cwd=str(ROOT),
    )

    log(
        f"Streamlit process started "
        f"(PID={streamlit_process.pid})"
    )

    log(
        f"Streamlit UI: "
        f"http://{STREAMLIT_HOST}:{STREAMLIT_PORT}"
    )

    return True


# ============================================================
# Shutdown
# ============================================================

def shutdown() -> None:

    global shutdown_requested

    if shutdown_requested:
        return

    shutdown_requested = True

    print()
    log("Shutting down development stack...")

    # --------------------------------------------------------
    # Stop Streamlit
    # --------------------------------------------------------

    if streamlit_process is not None:

        if streamlit_process.poll() is None:

            log("Stopping Streamlit...")

            try:
                streamlit_process.terminate()
                streamlit_process.wait(timeout=5)
            except Exception:
                try:
                    streamlit_process.kill()
                except Exception:
                    pass

    # --------------------------------------------------------
    # Stop FastAPI
    # --------------------------------------------------------

    if fastapi_process is not None:

        if fastapi_process.poll() is None:

            log("Stopping FastAPI...")

            try:
                fastapi_process.terminate()
                fastapi_process.wait(timeout=5)
            except Exception:
                try:
                    fastapi_process.kill()
                except Exception:
                    pass

    # --------------------------------------------------------
    # Stop Docker
    # --------------------------------------------------------

    log("Stopping LiteLLM Docker stack...")

    result = run_command(
        [
            "docker",
            "compose",
            "down",
        ],
        cwd=LITELLM_DIR,
    )

    if result.returncode != 0:
        error(
            "Docker Compose shutdown returned "
            f"exit code {result.returncode}"
        )

    log("Development stack stopped.")


# ============================================================
# Signal handling
# ============================================================

def handle_signal(signum, frame):
    log("Shutdown signal received.")
    shutdown()


# ============================================================
# Main
# ============================================================

def main() -> int:

    global shutdown_requested

    signal.signal(
        signal.SIGINT,
        handle_signal,
    )

    if hasattr(signal, "SIGTERM"):
        signal.signal(
            signal.SIGTERM,
            handle_signal,
        )

    print()
    print("=" * 60)
    print("             LLM GATEWAYS DEVELOPMENT")
    print("=" * 60)
    print()

    # --------------------------------------------------------
    # 1. Start LiteLLM
    # --------------------------------------------------------

    if not start_litellm():
        shutdown()
        return 1

    # --------------------------------------------------------
    # 2. Start FastAPI
    # --------------------------------------------------------

    if not start_fastapi():
        shutdown()
        return 1

    # --------------------------------------------------------
    # 3. Start Streamlit
    # --------------------------------------------------------

    if not start_streamlit():
        shutdown()
        return 1

    # --------------------------------------------------------
    # 4. Everything is running
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("                 STACK IS READY")
    print("=" * 60)
    print()
    print(
        f"LiteLLM : http://{LITELLM_HOST}:{LITELLM_PORT}"
    )
    print(
        f"FastAPI : http://{FASTAPI_HOST}:{FASTAPI_PORT}"
    )
    print(
        f"Health  : {FASTAPI_HEALTH_URL}"
    )
    print(
        f"UI      : http://{STREAMLIT_HOST}:{STREAMLIT_PORT}"
    )
    print()
    print("Press Ctrl+C to stop the complete stack.")
    print()

    # --------------------------------------------------------
    # 5. Keep orchestrator alive
    # --------------------------------------------------------

    try:

        while not shutdown_requested:

            time.sleep(2)

            # Don't automatically shut down merely because
            # Streamlit or FastAPI temporarily changes state.
            #
            # However, report if either process actually dies.

            if (
                fastapi_process is not None
                and fastapi_process.poll() is not None
            ):

                error(
                    "FastAPI process exited unexpectedly. "
                    f"Exit code: {fastapi_process.returncode}"
                )

                shutdown()
                return 1

            if (
                streamlit_process is not None
                and streamlit_process.poll() is not None
            ):

                error(
                    "Streamlit process exited unexpectedly. "
                    f"Exit code: {streamlit_process.returncode}"
                )

                shutdown()
                return 1

    except KeyboardInterrupt:

        log("Ctrl+C received.")
        shutdown()

    return 0


if __name__ == "__main__":
    sys.exit(main())