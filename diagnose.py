#!/usr/bin/env python3
"""
CaptionCraft Diagnostics Tool
Checks system requirements, environment variables, database, Redis, Celery, and Fireworks AI API.
"""

import os
import sys
import asyncio
import subprocess
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Color codes for terminal output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"

def print_section(title):
    print(f"\n{BOLD}{BLUE}=== {title} ==={RESET}")

def print_ok(message):
    print(f"[{GREEN}OK{RESET}] {message}")

def print_warn(message):
    print(f"[{YELLOW}WARN{RESET}] {message}")

def print_error(message):
    print(f"[{RED}FAIL{RESET}] {message}")

def print_info(message):
    print(f"[{BLUE}INFO{RESET}] {message}")

# --- Step 1: Check Python Libraries ---
def check_python_libs():
    print_section("Checking Python Dependencies")
    required_libs = {
        "dotenv": "python-dotenv",
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "pydantic": "pydantic",
        "pydantic_settings": "pydantic-settings",
        "sqlalchemy": "sqlalchemy",
        "asyncpg": "asyncpg",
        "celery": "celery",
        "redis": "redis",
        "faster_whisper": "faster-whisper",
        "httpx": "httpx",
        "openai": "openai",
    }
    
    missing = []
    for lib, package in required_libs.items():
        try:
            __import__(lib)
            print_ok(f"Package '{package}' is installed.")
        except ImportError:
            print_error(f"Package '{package}' (module: {lib}) is NOT installed.")
            missing.append(package)
            
    if missing:
        print_warn(f"Some packages are missing. Install them using: pip install -r requirements.txt")
        return False
    return True

# --- Step 2: Check System Dependencies ---
def check_system_deps():
    print_section("Checking System Binaries (FFmpeg)")
    
    # Check ffmpeg
    try:
        res = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            version_line = res.stdout.split('\n')[0]
            print_ok(f"FFmpeg is installed: {version_line}")
        else:
            print_error(f"FFmpeg check returned non-zero code {res.returncode}")
    except FileNotFoundError:
        print_error("FFmpeg was NOT found in your system PATH. It is required for video frame and audio extraction!")
        print_info("To resolve this, please install ffmpeg on your machine and add it to your PATH, or run the app via Docker.")
        
    # Check ffprobe
    try:
        res = subprocess.run(["ffprobe", "-version"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            version_line = res.stdout.split('\n')[0]
            print_ok(f"FFprobe is installed: {version_line}")
        else:
            print_error(f"FFprobe check returned non-zero code {res.returncode}")
    except FileNotFoundError:
        print_error("FFprobe was NOT found in your system PATH. It is required to get video duration!")

# --- Step 3: Check Environment & Config ---
def check_env():
    print_section("Checking Environment Variables")
    env_path = Path(".env")
    if not env_path.exists():
        print_error(".env file not found in the root directory!")
        print_info("Create it by copying .env.example: cp .env.example .env")
        return None
    
    print_ok(".env file found.")
    
    # Try to load .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        # Fall back to manual parsing if dotenv is missing
        with open(".env") as f:
            for line in f:
                if line.strip() and not line.startswith("#") and "=" in line:
                    k, v = line.strip().split("=", 1)
                    os.environ[k] = v
                    
    # Read Settings
    try:
        from backend.core.config import get_settings
        settings = get_settings()
        
        # Check Fireworks key
        key = settings.fireworks_api_key
        if not key or key == "your_fireworks_api_key_here":
            print_error("FIREWORKS_API_KEY is not set. Please configure it in your .env file.")
        elif len(key) < 15:
            print_warn(f"FIREWORKS_API_KEY looks very short ({key[:5]}...). It might be a placeholder.")
        else:
            print_ok("FIREWORKS_API_KEY is configured.")
            
        print_info(f"Fireworks Model: {settings.fireworks_model}")
        print_info(f"Database URL: {settings.database_url}")
        print_info(f"Redis URL: {settings.redis_url}")
        print_info(f"Temp Directory: {settings.temp_dir}")
        
        return settings
    except Exception as e:
        print_error(f"Failed to parse configuration: {e}")
        return None

# --- Step 4: Check Database Connection ---
async def check_db_connection(settings):
    print_section("Testing Database Connection")
    db_url = settings.database_url
    
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
        
        print_info(f"Connecting to database...")
        engine = create_async_engine(db_url, socket_timeout=5)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        print_ok("Database connection check successful.")
        return True
    except Exception as e:
        print_error(f"Failed to connect to the database: {e}")
        print_info("Make sure your PostgreSQL container/service is running and DATABASE_URL is correct.")
        return False

# --- Step 5: Check Redis Connection & Celery Worker ---
async def check_redis_and_celery(settings):
    print_section("Testing Redis & Celery")
    redis_url = settings.redis_url
    
    redis_connected = False
    try:
        import redis.asyncio as aioredis
        print_info("Connecting to Redis...")
        r = aioredis.from_url(redis_url, socket_connect_timeout=3)
        await r.ping()
        await r.aclose()
        print_ok("Redis connection check successful.")
        redis_connected = True
    except Exception as e:
        print_error(f"Failed to connect to Redis: {e}")
        print_info("Make sure your Redis container/service is running and REDIS_URL is correct.")
        
    if redis_connected:
        try:
            from backend.worker.celery_app import celery_app
            print_info("Checking for active Celery workers...")
            # We must run this in a thread or executor since celery control inspect is blocking
            def inspect_workers():
                inspect = celery_app.control.inspect(timeout=3.0)
                return inspect.active() if inspect else None
                
            loop = asyncio.get_running_loop()
            active = await loop.run_in_executor(None, inspect_workers)
            
            if active:
                workers = list(active.keys())
                print_ok(f"Active Celery workers found: {', '.join(workers)}")
            else:
                print_error("No active Celery workers detected! Captions tasks will stay in PENDING status.")
                print_info("Start a worker locally using: celery -A backend.worker.celery_app worker --loglevel=info --pool=solo")
        except Exception as e:
            print_warn(f"Could not inspect Celery workers (this is normal if celery isn't fully configured): {e}")

# --- Step 6: Test Fireworks AI API ---
async def check_fireworks_api(settings):
    print_section("Testing Fireworks AI API")
    key = settings.fireworks_api_key
    model = settings.fireworks_model
    
    if not key or key == "your_fireworks_api_key_here" or len(key) < 10:
        print_error("Skipping Fireworks API check: Invalid or missing API key.")
        return
        
    try:
        import httpx
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": "Hello! Keep your answer to exactly one word: 'Success'."}
            ],
            "max_tokens": 10,
        }
        print_info("Sending test request to Fireworks AI...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.fireworks.ai/inference/v1/chat/completions",
                json=payload,
                headers=headers,
            )
            if response.status_code == 200:
                data = response.json()
                reply = data["choices"][0]["message"]["content"].strip()
                print_ok(f"Fireworks AI check successful! Reply: '{reply}'")
            elif response.status_code in (401, 403):
                print_error(f"Fireworks AI authentication failed (status {response.status_code}). Please verify your FIREWORKS_API_KEY in .env.")
            else:
                print_error(f"Fireworks AI API returned error status {response.status_code}: {response.text}")
    except Exception as e:
        print_error(f"Failed to communicate with Fireworks AI: {e}")

async def main():
    print(f"\n{BOLD}{GREEN}=============================================={RESET}")
    print(f"{BOLD}{GREEN}      CaptionCraft Environment Diagnostics     {RESET}")
    print(f"{BOLD}{GREEN}=============================================={RESET}")
    
    libs_ok = check_python_libs()
    check_system_deps()
    settings = check_env()
    
    if settings:
        db_ok = await check_db_connection(settings)
        await check_redis_and_celery(settings)
        await check_fireworks_api(settings)
        
    print(f"\n{BOLD}{GREEN}=============================================={RESET}")
    print(f"{BOLD}{BLUE}Diagnostics Complete.{RESET}")
    print(f"{BOLD}{GREEN}=============================================={RESET}\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDiagnostics cancelled.")
