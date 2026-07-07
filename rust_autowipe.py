from urllib.parse import quote
#!/usr/bin/env python3
import asyncio
import json
import logging
import os
import random
import re
import fnmatch
import subprocess
import shutil
import threading
import uuid
import hashlib
import hmac
import secrets
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import discord
import requests
from flask import Flask, abort, jsonify, redirect, render_template_string, request, send_file, session
from werkzeug.exceptions import HTTPException

BASE_DIR = Path(os.getenv("BASE_DIR", "/home/container"))
DATA_DIR = BASE_DIR / "dashboard_data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SETTINGS_FILE = DATA_DIR / "settings.json"
POOL_STATE_FILE = BASE_DIR / "rustmaps_vote_pool" / "pool_state.json"
POOL_STATE_BACKUP_FILE = BASE_DIR / "rustmaps_vote_pool" / "pool_state.backup.json"
MAP_DELETE_AUDIT_FILE = DATA_DIR / "map_delete_audit.log"
DELETED_MAPS_DIR = BASE_DIR / "rustmaps_vote_pool" / "_deleted_maps"
WIPED_MAPS_ARCHIVE_DIR = BASE_DIR / "rustmaps_vote_pool" / "_wiped_maps_archive"
UPLOADED_LOGO_DIR = DATA_DIR / "uploaded_logo"
UPLOADED_LOGO_DIR.mkdir(parents=True, exist_ok=True)
GEN_STATUS_FILE = DATA_DIR / "generation_status.json"
RUNTIME_STATUS_FILE = DATA_DIR / "runtime_status.json"
PLAYER_STATS_FILE = DATA_DIR / "player_stats.json"
WIPE_HISTORY_FILE = DATA_DIR / "wipe_history.json"
LOG_DIR = BASE_DIR / "logs"
AUTH_FILE = DATA_DIR / "dashboard_auth.json"
COMMITS_FILE = DATA_DIR / "commits.json"

DEFAULT_SETTINGS = {
    "discord": {
        "token": "",
        "channel_id": "",
        "vote_duration_seconds": 60,
        "reaction_emoji": "✅",
    },
    "rustmaps": {
        "binary": str(BASE_DIR / "rustmaps"),
        "api_key": "",
        "size": 3750,
        "saved_config": "default",
        "downloads_dir": str(BASE_DIR / "rustmaps_vote_pool"),
        "generate_timeout_seconds": 2400,
        "target_pool_size": 10,
        "concurrent_generations": 3,
        "fill_pool_batch_max": 5,
        "fill_pool_full_immediately": False,
        "log_level": "info",
        "cleanup_deleted_maps_days": 3,
    },
    "pterodactyl": {
        "panel_url": "https://panel.example.com",
        "server_id": "",
        "api_key": "",
        "request_timeout": 60,
    },
    "rust_server": {
        "ip": "",
        "port": 28015,
    },
    "notifications": {
        "wipe_webhook_url": "",
        "server_name": "YOUR SERVER NAME",
        "server_brand": "YOUR BRAND",
        "logo_url": "",
        "connect_address": "",
        "enabled": False
    },
    "commits": {
        "enabled": False,
        "webhook_url": "",
        "author_user_id": "",
        "channel_label": "main",
        "color": "#22dd6a",
        "ping_target": "",
        "send_on_create": True
    },
    "schedule": {
        "timezone": "UTC",
        "ordinary_wipe_cron": "",
        "full_wipe_cron": "",
        "ordinary_wipe_start_date": "",
        "full_wipe_start_date": "",
        "wipe_time": "11:55",
        "ordinary_interval_days": 3,
        "full_interval_days": 6,
        "vote_publish_before_minutes": 60,
        "vote_duration_minutes": 60,
        "vote_close_mode": "finalize_before_wipe",
        "publish_when_pool_ready_min": 3,
        "auto_publish_vote": True,
        "ordinary_wipe_label": "ordinary",
        "full_wipe_label": "full"
    },
    "wipe": {
        "remove_map": True,
        "remove_sav": True,
        "remove_occlusion": True,
        "remove_bp_db": True,
        "remove_bp_wal": True,
        "remove_player_identities": False,
        "remove_player_states": False,
        "remove_player_tokens": False,
        "remove_player_deaths": False
    },
    "wipe_profiles": {
        "ordinary": {
            "locked": True,
            "paths": [
                "server/rust/*.map",
                "server/rust/*.sav",
                "server/rust/*.sav.1",
                "server/rust/*.sav.2",
                "server/rust/*_occlusion_*.dat"
            ]
        },
        "blueprint": {
            "locked": True,
            "paths": [
                "server/rust/*.map",
                "server/rust/*.sav",
                "server/rust/*.sav.1",
                "server/rust/*.sav.2",
                "server/rust/*_occlusion_*.dat",
                "server/rust/player.blueprints*.db",
                "server/rust/player.blueprints*.db-wal"
            ]
        }
    },
    "smm": {
        "enabled": False,
        "post_time": "16:00",
        "channel_id": "",
        "templates": {
            "monday": "💬 VEXON RUST — ОБСУЖДЕНИЕ ВЫХОДНЫХ\nКак прошли ваши выходные на сервере? Какие рейды запомнились больше всего?\n\n• Сражения: Расскажите о самых эпичных PvP-столкновениях и защите баз.\n• Рейды: Поделитесь историями об успешных захватах и скриншотами лучшего лута.\n• Обратная связь: Что вам понравилось или не понравилось в балансе?\n\nСайт: vexonrust.com\nПодключение: connect play.vexonrust.com",
            "tuesday": "🪙 VEXON RUST — ЭКОНОМИКА И V-COINS\nНапоминаем про нашу экономическую систему V-Coins на серверах.\n\n• Заработок: Получайте V-Coins за проведенное время в игре и активное PvP.\n• Обмен: Обменивайте накопленную валюту на привилегии и ресурсы в Личном Кабинете.\n• Статистика: Следите за балансом и характеристиками вашего персонажа на сайте.\n\nЛичный кабинет: vexonrust.com\nПодключение: connect play.vexonrust.com",
            "wednesday": "🏠 VEXON RUST — ЖИЗНЬ СЕРВЕРА\nПрошла половина текущего вайпа. Самое время оценить ситуацию на карте.\n\n• Базы: Делитесь скриншотами ваших построек и архитектурных решений.\n• Карта: Как обстоят дела с ключевыми точками? Кто доминирует в вашем секторе?\n• Планы: Готовы ли вы к финальным рейдам перед грядущим обновлением?\n\nСайт: vexonrust.com\nПодключение: connect play.vexonrust.com",
            "thursday": "🗺️ VEXON RUST — ПЛАНЫ НА ВАЙП\nУже завтра начнется новый вайп. Пора выбрать карту для следующего цикла.\n\n• Голосование: Зайдите в специальный канал и выберите понравившийся вариант карты.\n• Подготовка: Продумайте стратегию старта и состав вашей команды.\n• Анонс: Точное время вайпа и технические детали будут опубликованы в Discord.\n\nСайт: vexonrust.com\nПодключение: connect play.vexonrust.com",
            "friday": "🎁 VEXON RUST — РОЗЫГРЫШ ВЫХОДНЫХ\nВ честь начала выходных и нового вайпа мы запускаем розыгрыш бонусов!\n\n• Участие: Напишите ваш точный игровой никнейм в ветке обсуждения под этим постом.\n• Призы: Бонусные балансы на аккаунт в личном кабинете для быстрого старта.\n• Итоги: Победители будут выбраны случайным образом и объявлены завтра.\n\nСайт: vexonrust.com\nПодключение: connect play.vexonrust.com",
            "saturday": "⚔️ VEXON RUST — ВРЕМЯ РЕЙДОВ\nВыходные в самом разгаре. Время для активных боевых действий на сервере.\n\n• PvP: Покажите свои лучшие моменты сражений и дуэлей.\n• Рейды: Поделитесь записями или скриншотами успешного подрыва чужих баз.\n• Общение: Координируйте действия в голосовых каналах и ищите напарников.\n\nСайт: vexonrust.com\nПодключение: connect play.vexonrust.com",
            "sunday": "📊 VEXON RUST — ОБРАТНАЯ СВЯЗЬ\nМы постоянно работаем над улучшением геймплея и баланса на серверах.\n\n• Баланс: Предложите изменения для плагинов, лимитов команд или системы лута.\n• Идеи: Каких нововведений или ивентов вам не хватает на сервере?\n• Отзывы: Напишите ваше мнение о качестве работы администрации и хостинга.\n\nСайт: vexonrust.com\nПодключение: connect play.vexonrust.com"
        }
    },
    "frontend": {
        "login_url": "https://raw.githubusercontent.com/gothbreach/Autowipe-Project/main/login.html",
        "setup_url": "https://raw.githubusercontent.com/gothbreach/Autowipe-Project/main/setup_password.html",
        "dashboard_url": "https://raw.githubusercontent.com/gothbreach/Autowipe-Project/main/dashboard.html"
    }
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("rust_autowipe_allinone")

app = Flask(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard login/auth
# Console command: admin.login <name>
# ─────────────────────────────────────────────────────────────────────────────
AUTH_SESSION_KEY = "dashboard_user"
AUTH_LAST_ACTIVE_KEY = "dashboard_last_active"
AUTH_IDLE_SECONDS = 1800
AUTH_PUBLIC_PATHS = {"/login", "/setup-password", "/favicon.ico"}


# ─────────────────────────────────────────────────────────────────────────────
# Dynamic Frontend Loader with Local Cache
# ─────────────────────────────────────────────────────────────────────────────
import requests

AUTH_STYLE = ""

LOGIN_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>RUST AUTOWIPE // LOGIN</title>
  <style>
    body { background:#090c10; color:#f1f5f9; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; display:flex; align-items:center; justify-content:center; min-height:100vh; margin:0; }
    .box { padding:40px; background:#0f131c; border:1px solid rgba(255,255,255,0.06); border-radius:12px; max-width:360px; width:100%; box-shadow: 0 10px 30px rgba(0,0,0,0.5); text-align:center; }
    h2 { margin-top:0; font-size:20px; font-weight:600; letter-spacing:1px; color:#fff; margin-bottom:24px; }
    input { width:100%; box-sizing:border-box; background:#161b22; border:1px solid rgba(255,255,255,0.1); color:#fff; padding:12px 16px; border-radius:6px; margin-bottom:16px; outline:none; font-size:14px; transition:border-color 0.2s; }
    input:focus { border-color:#3b82f6; }
    button { width:100%; background:#2563eb; color:#fff; border:none; padding:12px; border-radius:6px; font-size:14px; font-weight:600; cursor:pointer; transition:background 0.2s; }
    button:hover { background:#1d4ed8; }
    .error { color:#ef4444; font-size:13px; margin-bottom:16px; background:rgba(239,68,68,0.1); padding:8px; border-radius:4px; }
    .message { color:#10b981; font-size:13px; margin-bottom:16px; background:rgba(16,185,129,0.1); padding:8px; border-radius:4px; }
  </style>
</head>
<body>
  <div class="box">
    <h2>RUST AUTOWIPE // LOGIN</h2>
    {% if error %}
    <div class="error">{{ error }}</div>
    {% endif %}
    {% if message %}
    <div class="message">{{ message }}</div>
    {% endif %}
    <form method="POST" action="/login">
      <input type="text" name="username" placeholder="Username" value="{{ username }}" required autofocus>
      <input type="password" name="password" placeholder="Password" required>
      <button type="submit">SIGN IN</button>
    </form>
  </div>
</body>
</html>
"""

SETUP_PASSWORD_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>RUST AUTOWIPE // SETUP</title>
  <style>
    body { background:#090c10; color:#f1f5f9; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; display:flex; align-items:center; justify-content:center; min-height:100vh; margin:0; }
    .box { padding:40px; background:#0f131c; border:1px solid rgba(255,255,255,0.06); border-radius:12px; max-width:360px; width:100%; box-shadow: 0 10px 30px rgba(0,0,0,0.5); text-align:center; }
    h2 { margin-top:0; font-size:20px; font-weight:600; letter-spacing:1px; color:#fff; margin-bottom:10px; }
    p { font-size:13px; color:#94a3b8; margin-bottom:24px; line-height:1.5; }
    input { width:100%; box-sizing:border-box; background:#161b22; border:1px solid rgba(255,255,255,0.1); color:#fff; padding:12px 16px; border-radius:6px; margin-bottom:16px; outline:none; font-size:14px; transition:border-color 0.2s; }
    input:focus { border-color:#3b82f6; }
    button { width:100%; background:#10b981; color:#fff; border:none; padding:12px; border-radius:6px; font-size:14px; font-weight:600; cursor:pointer; transition:background 0.2s; }
    button:hover { background:#059669; }
    .error { color:#ef4444; font-size:13px; margin-bottom:16px; background:rgba(239,68,68,0.1); padding:8px; border-radius:4px; }
  </style>
</head>
<body>
  <div class="box">
    <h2>SETUP PASSWORD</h2>
    <p>Welcome, <strong>{{ username }}</strong>. Set your dashboard password.</p>
    {% if error %}
    <div class="error">{{ error }}</div>
    {% endif %}
    <form method="POST" action="/setup-password">
      <input type="password" name="password" placeholder="New Password" required autofocus>
      <input type="password" name="password2" placeholder="Confirm Password" required>
      <button type="submit">SAVE PASSWORD</button>
    </form>
  </div>
</body>
</html>
"""

DASHBOARD_HTML = """
<!doctype html>
<html>
<head><title>RUST AUTOWIPE // SYSTEM CONTROL</title></head>
<body style="background:#090c10; color:#f1f5f9; font-family:sans-serif; display:flex; align-items:center; justify-content:center; min-height:100vh; margin:0;">
  <div style="padding:40px; background:#0f131c; border:1px solid rgba(255,255,255,0.06); border-radius:10px; max-width:500px; width:100%; text-align:center;">
    <h2>RUST AUTOWIPE // DASHBOARD</h2>
    <p style="color:#94a3b8;">Интерфейс не загружен. Убедитесь, что сервер подключен к сети, или скопируйте локальный кэш.</p>
  </div>
</body>
</html>
"""

def download_frontend():
    import zipfile
    import io
    import requests
    import shutil
    import sys
    import time
    url = f"https://github.com/qutlawsoasis-debug/Autowipe-Project/archive/refs/heads/gh-pages.zip?t={int(time.time())}"
    try:
        log.info("Downloading Next.js frontend from GitHub...")
        r = requests.get(url, stream=True, timeout=15)
        if r.status_code == 200:
            total_size = int(r.headers.get('content-length', 0))
            block_size = 8192
            downloaded = 0
            content = bytearray()
            
            sys.stdout.write("\n")
            for data in r.iter_content(block_size):
                content.extend(data)
                downloaded += len(data)
                if total_size > 0:
                    percent = int(50 * downloaded / total_size)
                    sys.stdout.write(f"\r[Frontend] Downloading: [{'=' * percent}{' ' * (50 - percent)}] {int(downloaded/total_size*100)}%")
                else:
                    sys.stdout.write(f"\r[Frontend] Downloading: {downloaded / 1024:.1f} KB downloaded...")
                sys.stdout.flush()
            sys.stdout.write("\n\n")
            sys.stdout.flush()
            
            log.info("Extracting frontend files...")
            extract_to = Path(BASE_DIR) / "dashboard_data"
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                z.extractall(extract_to)
            
            extracted_dir = extract_to / "Autowipe-Project-gh-pages"
            frontend_dir = Path(BASE_DIR) / "dashboard_data" / "frontend_cache"
            if frontend_dir.exists():
                shutil.rmtree(frontend_dir)
            extracted_dir.rename(frontend_dir)
            log.info("Frontend updated successfully from GitHub gh-pages branch!")
        else:
            log.error(f"Failed to download frontend: HTTP {r.status_code}")
    except Exception as e:
        log.error(f"Failed to download frontend: {e}")

# Start the frontend download automatically on boot
import threading
threading.Thread(target=download_frontend, daemon=True).start()

def get_frontend_html(page_name, setting_key, fallback_html):
    frontend_dir = Path(BASE_DIR) / "dashboard_data" / "frontend_cache"
    
    # Map page_name to the correct HTML file
    if page_name == "dashboard":
        cache_file = frontend_dir / "index.html"
    elif page_name == "login":
        cache_file = frontend_dir / "login.html"
    elif page_name == "setup_password":
        cache_file = frontend_dir / "setup_password.html"
    else:
        cache_file = frontend_dir / f"{page_name}.html"
    
    # Try loading from local cache (extracted from GitHub gh-pages)
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            pass
            
    return fallback_html

def render_frontend(page_name, setting_key, fallback_html, **context):
    html = get_frontend_html(page_name, setting_key, fallback_html)
    # Don't run Jinja on the React dashboard app!
    if page_name == "dashboard":
        return html
    return render_template_string(html, **context)

from flask import send_from_directory

@app.route("/_next/<path:path>")
def serve_next_static(path):
    frontend_dir = Path(BASE_DIR) / "dashboard_data" / "frontend_cache" / "_next"
    return send_from_directory(frontend_dir, path)

@app.route("/maps/<path:path>")
def serve_maps_static(path):
    frontend_dir = Path(BASE_DIR) / "dashboard_data" / "frontend_cache" / "maps"
    return send_from_directory(frontend_dir, path)

def load_auth_state() -> dict:
    # This function runs before the shared load_json/save_json helpers are defined,
    # so it must read/write auth.json directly.
    try:
        data = json.loads(AUTH_FILE.read_text(encoding="utf-8")) if AUTH_FILE.exists() else {}
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    changed = False
    if not data.get("secret_key"):
        data["secret_key"] = secrets.token_hex(32); changed = True
    if not isinstance(data.get("users"), dict):
        data["users"] = {}; changed = True
    if not isinstance(data.get("pending"), dict):
        data["pending"] = {}; changed = True
    if changed:
        save_auth_state(data)
    return data

def save_auth_state(data: dict) -> None:
    AUTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    AUTH_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def normalize_login(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]", "", (name or "").strip()).lower()[:32]

def hash_password(password: str, salt_hex: Optional[str] = None) -> dict:
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 220_000)
    return {"salt": salt.hex(), "hash": digest.hex(), "algo": "pbkdf2_sha256", "iterations": 220000}

def verify_password(password: str, record: dict) -> bool:
    try:
        salt = record.get("salt", "")
        expected = record.get("hash", "")
        got = hash_password(password, salt).get("hash", "")
        return hmac.compare_digest(got, expected)
    except Exception:
        return False

def is_logged_in() -> bool:
    user = session.get(AUTH_SESSION_KEY)
    if not user: return False
    auth = load_auth_state()
    return normalize_login(user) in auth.get("users", {})

def create_one_time_login(username: str):
    login = normalize_login(username)
    if not login:
        return False, "Логин может содержать только буквы, цифры, точку, дефис и подчёркивание.", None
    # Human-friendly one-time password: no ambiguous chars and no trailing symbols.
    token = secrets.token_urlsafe(12).rstrip("=")
    auth = load_auth_state()
    auth.setdefault("pending", {})[login] = {
        "token_hash": hash_password(token),
        "token_plain": token,  # one-time; removed after permanent password setup
        "created_at_ts": time.time(),
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    save_auth_state(auth)
    return True, login, token

def start_admin_console_thread() -> None:
    def loop():
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    time.sleep(1); continue
                line = line.strip()
                if not line: continue
                m = re.match(r"^admin\.login\s+(.+)$", line, flags=re.IGNORECASE)
                if not m: continue
                ok, login_or_msg, token = create_one_time_login(m.group(1))
                if ok:
                    msg = f"ADMIN LOGIN | login={login_or_msg} | one-time password={token}"
                    print(msg, flush=True)
                    log.warning(msg)
                    append_runtime_log(f"admin.login created one-time password for {login_or_msg}")
                else:
                    msg = f"ADMIN LOGIN ERROR | {login_or_msg}"
                    print(msg, flush=True)
                    log.warning(msg)
            except Exception as e:
                try: log.exception("admin console thread error: %s", e)
                except Exception: pass
                time.sleep(2)
    threading.Thread(target=loop, daemon=True, name="admin-console-login").start()

app.secret_key = load_auth_state().get("secret_key")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,
    PERMANENT_SESSION_LIFETIME=timedelta(seconds=AUTH_IDLE_SECONDS),
)
_worker_lock = threading.Lock()
VOTE_PUBLISH_LOCK = threading.Lock()
_pool_thread: Optional[threading.Thread] = None
discord_loop: Optional[asyncio.AbstractEventLoop] = None
scheduler: Optional[BackgroundScheduler] = None


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Keep a lightweight backup of pool_state before every overwrite.
    # If a bad cleanup/reconcile ever mutates the state, the last good version
    # can be restored from rustmaps_vote_pool/pool_state.backup.json.
    try:
        if path == POOL_STATE_FILE and path.exists():
            POOL_STATE_BACKUP_FILE.parent.mkdir(parents=True, exist_ok=True)
            POOL_STATE_BACKUP_FILE.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    except Exception as e:
        try:
            log.warning("pool_state backup failed: %s", e)
        except Exception:
            pass
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def save_state(state: Dict[str, Any]) -> None:
    save_json(POOL_STATE_FILE, state)


def load_settings() -> Dict[str, Any]:
    data = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
    merged = json.loads(json.dumps(DEFAULT_SETTINGS))
    for section, values in data.items():
        if isinstance(values, dict) and section in merged:
            merged[section].update(values)
    return merged


def save_settings(data: Dict[str, Any]) -> None:
    save_json(SETTINGS_FILE, data)


def update_gen_status(**kwargs):
    current = load_json(GEN_STATUS_FILE, {
        "running": False,
        "stage": "idle",
        "message": "Ожидание",
        "current_seed": None,
        "current_index": 0,
        "target_index": 0,
        "started_at": None,
        "updated_at": None,
        "last_output": [],
        "error": None,
        "active_generations": 0,
    })
    current.update(kwargs)
    current["updated_at"] = datetime.utcnow().isoformat() + "Z"
    save_json(GEN_STATUS_FILE, current)


def append_gen_output(line: str):
    status = load_json(GEN_STATUS_FILE, {
        "running": False,
        "stage": "idle",
        "message": "Ожидание",
        "last_output": [],
        "active_generations": 0,
    })
    lines = status.get("last_output", [])
    lines.append(line)
    status["last_output"] = lines[-80:]
    status["updated_at"] = datetime.utcnow().isoformat() + "Z"
    save_json(GEN_STATUS_FILE, status)


def now_ts() -> float:
    return time.time()

def update_runtime_status(**kwargs):
    current = load_json(RUNTIME_STATUS_FILE, {
        "discord_ready": False,
        "worker_running": False,
        "message": "Ожидание",
        "last_action": None,
        "updated_at": None,
        "log": [],
    })
    current.update(kwargs)
    current["updated_at"] = datetime.utcnow().isoformat() + "Z"
    save_json(RUNTIME_STATUS_FILE, current)

def append_runtime_log(line: str):
    current = load_json(RUNTIME_STATUS_FILE, {
        "discord_ready": False,
        "worker_running": False,
        "message": "Ожидание",
        "last_action": None,
        "updated_at": None,
        "log": [],
    })
    lines = current.get("log", [])
    lines.append(line)
    current["log"] = lines[-80:]
    current["updated_at"] = datetime.utcnow().isoformat() + "Z"
    save_json(RUNTIME_STATUS_FILE, current)


def audit_map_delete(reason: str, map_item: dict, key: str = "map_path") -> None:
    seed = map_item.get("seed")
    path = map_item.get(key) or map_item.get("map_path")
    line = f"{datetime.utcnow().isoformat()}Z | reason={reason} | seed={seed} | key={key} | path={path}"
    try:
        MAP_DELETE_AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with MAP_DELETE_AUDIT_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    try:
        append_runtime_log(f"MAP DELETE | reason={reason} | seed={seed} | path={path}")
    except Exception:
        pass


def is_ready_map_protected(map_item: dict) -> bool:
    mp = map_item.get("map_path")
    return bool(map_item.get("status") == "ready" and mp and Path(mp).exists())


def mask_secret(v: str) -> str:
    if not v:
        return ""
    if len(v) <= 8:
        return "*" * len(v)
    return v[:4] + "..." + v[-4:]


TIMEZONE_OPTIONS = [
    ("UTC-12", "Etc/GMT+12"), ("UTC-11", "Etc/GMT+11"), ("UTC-10", "Etc/GMT+10"),
    ("UTC-9", "Etc/GMT+9"), ("UTC-8", "Etc/GMT+8"), ("UTC-7", "Etc/GMT+7"),
    ("UTC-6", "Etc/GMT+6"), ("UTC-5", "Etc/GMT+5"), ("UTC-4", "Etc/GMT+4"),
    ("UTC-3", "Etc/GMT+3"), ("UTC-2", "Etc/GMT+2"), ("UTC-1", "Etc/GMT+1"),
    ("UTC", "UTC"),
    ("UTC+1", "Etc/GMT-1"), ("UTC+2", "Etc/GMT-2"), ("UTC+3", "Etc/GMT-3"),
    ("UTC+4", "Etc/GMT-4"), ("UTC+5", "Etc/GMT-5"), ("UTC+6", "Etc/GMT-6"),
    ("UTC+7", "Etc/GMT-7"), ("UTC+8", "Etc/GMT-8"), ("UTC+9", "Etc/GMT-9"),
    ("UTC+10", "Etc/GMT-10"), ("UTC+11", "Etc/GMT-11"), ("UTC+12", "Etc/GMT-12"),
]
VOTE_CLOSE_MODE_OPTIONS = [
    ("after_first_vote", "Таймер после первого голоса"),
    ("fixed_duration_after_publish", "Фиксированно после публикации"),
]
def parse_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
def timezone_label(current_value: str) -> str:
    for label, val in TIMEZONE_OPTIONS:
        if val == current_value:
            return label
    return current_value or "UTC"


def ensure_state() -> Dict[str, Any]:
    state = load_json(POOL_STATE_FILE, {
        "maps": [],
        "vote": None,
        "selected_map_path": None,
        "selected_at": None,
        "winner_message_id": None,
        "last_wipe_at": None,
        "wipe_attempt_in_progress": False,
        "wipe_error": None,
        "wipe_error_notified": False,
        "scheduled_wipe_mode": None,
        "scheduled_wipe_requested_at": None,
        "scheduled_wipe_target_at": None,
        "vote_window_consumed_target_at": None,
        "vote_publish_in_progress_for_target": None,
        "last_vote_target_at": None,
        "queued_extra_generations": 0,
        "generation_epoch": 0,
        "remote_inflight": [],
    })
    state.setdefault("maps", [])
    state.setdefault("vote", None)
    state.setdefault("selected_map_path", None)
    state.setdefault("selected_at", None)
    state.setdefault("winner_message_id", None)
    state.setdefault("last_wipe_at", None)
    state.setdefault("wipe_attempt_in_progress", False)
    state.setdefault("wipe_error", None)
    state.setdefault("wipe_error_notified", False)
    state.setdefault("scheduled_wipe_mode", None)
    state.setdefault("scheduled_wipe_requested_at", None)
    state.setdefault("scheduled_wipe_target_at", None)
    state.setdefault("vote_window_consumed_target_at", None)
    state.setdefault("vote_publish_in_progress_for_target", None)
    state.setdefault("last_vote_target_at", None)
    state.setdefault("queued_extra_generations", 0)
    state.setdefault("generation_epoch", 0)
    state.setdefault("remote_inflight", [])
    state.setdefault("orphaned_message_ids", [])

    return state


def to_media_url(path: Optional[str]) -> str:
    if not path:
        return ""
    return "/media?path=" + quote(str(path), safe="")


def pick_preview_path(item: dict) -> str:
    for key in ("image_path", "icons_path", "thumbnail_path"):
        val = item.get(key)
        if val and Path(val).exists():
            return str(val)
    return ""


def _walk_values_for_strings(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield str(k)
            yield from _walk_values_for_strings(v)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            yield from _walk_values_for_strings(item)
    elif value is not None:
        yield str(value)


def _extract_with_patterns(raw_text: str, patterns: list[str]) -> Optional[str]:
    for pattern in patterns:
        m = re.search(pattern, raw_text, flags=re.IGNORECASE)
        if m:
            for group in m.groups():
                if group:
                    return group
            return m.group(0)
    return None


def _load_json_loose(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_map_metadata_from_artifacts(parent: Path, stem: str) -> dict:
    download_links = parent / f"{stem}_download_links.json"
    specs = parent / f"{stem}_specs.json"
    result = {"map_url": None, "page_url": None, "map_id": None, "seed": None, "size": None}

    url_patterns = [
        r'(https://maps\.rustmaps\.com/[^\s"\']+\.map)',
        r'(https://[^\s"\']+\.map)',
    ]
    page_patterns = [
        r'(https://rustmaps\.com/map/[^\s"\']+)',
        r'(https://[^\s"\']*rustmaps\.com/[^\s"\']+)',
    ]
    map_id_patterns = [
        r'"map_id"\s*:\s*"([a-f0-9]+)"',
        r'"mapId"\s*:\s*"([a-f0-9]+)"',
        r'\b([a-f0-9]{32})\b',
    ]

    for artifact in (download_links, specs):
        if not artifact.exists():
            continue
        raw = artifact.read_text(encoding="utf-8", errors="ignore")
        payload = _load_json_loose(artifact)
        strings = [raw]
        if payload is not None:
            strings.extend(_walk_values_for_strings(payload))

        if payload is not None and isinstance(payload, dict):
            result["map_url"] = result["map_url"] or payload.get("map") or payload.get("mapUrl") or payload.get("downloadUrl")
            result["page_url"] = result["page_url"] or payload.get("website") or payload.get("pageUrl") or payload.get("url")
            result["map_id"] = result["map_id"] or payload.get("map_id") or payload.get("mapId")
            result["seed"] = result["seed"] or payload.get("seed")
            result["size"] = result["size"] or payload.get("size")

        for s in strings:
            if not result["map_url"]:
                result["map_url"] = _extract_with_patterns(s, url_patterns)
            if not result["page_url"]:
                result["page_url"] = _extract_with_patterns(s, page_patterns)
            if not result["map_id"]:
                result["map_id"] = _extract_with_patterns(s, map_id_patterns)

    return result


def scan_disk_maps(download_dir: Path) -> Dict[str, dict]:
    found = {}
    if not download_dir.exists():
        return found

    # FIX #1: skip archive/deleted folders so wiped maps never re-enter the pool
    excluded_dirs = {
        str((download_dir / "_deleted_maps").resolve()),
        str((download_dir / "_wiped_maps_archive").resolve()),
    }

    for map_file in sorted(download_dir.rglob("*.map"), key=lambda p: p.stat().st_mtime):
        if any(str(map_file.resolve()).startswith(ex) for ex in excluded_dirs):
            continue
        stem = map_file.stem
        parent = map_file.parent
        icons = parent / f"{stem}_icons.png"
        thumb = parent / f"{stem}_thumbnail.png"
        image = parent / f"{stem}.png"
        seed = None
        size = None
        map_url = None
        page_url = None
        map_id = None

        m = re.match(r"(?P<seed>\d+)_(?P<size>\d+)_", stem)
        if m:
            seed = int(m.group("seed"))
            size = int(m.group("size"))

        metadata = _read_map_metadata_from_artifacts(parent, stem)
        map_url = metadata.get("map_url") or map_url
        page_url = metadata.get("page_url") or page_url
        map_id = metadata.get("map_id") or map_id
        seed = metadata.get("seed") or seed
        size = metadata.get("size") or size

        found[str(map_file.resolve())] = {
            "seed": seed,
            "size": size,
            "map_url": map_url,
            "page_url": page_url,
            "map_id": map_id,
            "map_path": str(map_file.resolve()),
            "image_path": str(image) if image.exists() else None,
            "icons_path": str(icons) if icons.exists() else None,
            "thumbnail_path": str(thumb) if thumb.exists() else None,
            "created_at": map_file.stat().st_mtime,
            "status": "ready",
            "message_id": None,
        }
    return found



def _merge_disk_and_state_map(base: dict, item: dict, selected_path: Optional[str], vote_paths: set[str]) -> dict:
    merged = dict(base)

    # Keep freshest metadata from disk, but preserve meaningful runtime state from saved item.
    for k, v in item.items():
        if k in ("image_path", "icons_path", "thumbnail_path", "map_url", "page_url", "map_id", "seed", "size"):
            if v not in (None, "", [], {}):
                merged[k] = v
        else:
            merged[k] = v

    # If disk now has preview files, never let stale None from state overwrite them.
    for media_key in ("image_path", "icons_path", "thumbnail_path"):
        if base.get(media_key):
            merged[media_key] = base.get(media_key)

    mp = merged.get("map_path")
    if mp == selected_path:
        merged["status"] = "selected"
    elif mp in vote_paths:
        merged["status"] = "in_vote"
    else:
        merged["status"] = merged.get("status") or "ready"

    return merged


def get_wipe_history() -> list:
    return load_json(WIPE_HISTORY_FILE, [])

def log_wipe_history(wipe_type: str, seed: str, size: str, status: str):
    history = get_wipe_history()
    from datetime import datetime, timezone
    history.insert(0, {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "type": wipe_type,
        "seed": seed,
        "size": size,
        "status": status
    })
    # Keep last 50 wipes
    history = history[:50]
    save_json(WIPE_HISTORY_FILE, history)

def a2s_info(ip: str, port: int, timeout=2.0) -> dict:
    import socket
    if not ip or not port:
        return None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        req = b'\xFF\xFF\xFF\xFFTSource Engine Query\x00'
        sock.sendto(req, (ip, int(port)))
        data, addr = sock.recvfrom(4096)
        if len(data) < 5 or data[4] != 0x49:
            return None
        offset = 6
        def read_str(b, o):
            end = b.find(b'\x00', o)
            return b[o:end].decode('utf-8', 'replace'), end + 1
        name, offset = read_str(data, offset)
        map_, offset = read_str(data, offset)
        folder, offset = read_str(data, offset)
        game, offset = read_str(data, offset)
        offset += 2 # AppID
        players = data[offset]
        offset += 1
        max_players = data[offset]
        return {"players": players, "max_players": max_players}
    except Exception as e:
        # Silently fail for regular tracking
        return None

def track_player_stats():
    settings = load_settings()
    ip = settings.get("rust_server", {}).get("ip")
    port = settings.get("rust_server", {}).get("port")
    if not ip or not port:
        return
        
    stats = load_json(PLAYER_STATS_FILE, {"history": [], "current_players": 0, "max_players": 0})
    result = a2s_info(ip, port)
    
    from datetime import datetime
    now_str = datetime.now().strftime("%H:%M")
    
    if result:
        current = result["players"]
        stats["max_players"] = result["max_players"]
        stats["current_players"] = current
    else:
        # If server is offline, players is 0
        current = 0
        stats["current_players"] = 0
        
    history = stats.get("history", [])
    # Add new datapoint
    history.append({"time": now_str, "players": current})
    
    # Keep last 24 hours assuming every 10 min (144 points)
    if len(history) > 144:
        history = history[-144:]
        
    stats["history"] = history
    save_json(PLAYER_STATS_FILE, stats)

def reconcile_pool_state() -> Dict[str, Any]:
    settings = load_settings()
    download_dir = Path(settings["rustmaps"]["downloads_dir"])
    state = ensure_state()
    disk = scan_disk_maps(download_dir)

    selected = state.get("selected_map_path")
    vote = state.get("vote") or {}
    vote_paths = set(vote.get("candidate_paths") or [])

    merged = []
    for item in state.get("maps", []):
        mp = item.get("map_path")
        if mp in disk and Path(mp).exists():
            base = disk.pop(mp)
            merged.append(_merge_disk_and_state_map(base, item, selected, vote_paths))
        elif mp == selected:
            # Keep selected item even if reconcile runs during transition, but only if map still exists.
            if mp and Path(mp).exists():
                kept = dict(item)
                kept["status"] = "selected"
                merged.append(kept)

    for item in disk.values():
        mp = item.get("map_path")
        if mp == selected:
            item["status"] = "selected"
        elif mp in vote_paths:
            item["status"] = "in_vote"
        else:
            # Never demote an existing downloaded .map back to preparing just because preview files lag behind.
            item["status"] = "ready"
        merged.append(item)

    merged.sort(key=lambda x: x.get("created_at", 0))
    state["maps"] = merged

    if selected and not any(m.get("map_path") == selected for m in merged):
        state["selected_map_path"] = None
        state["selected_at"] = None
        state["winner_message_id"] = None

    vote = state.get("vote")
    if vote and vote.get("candidate_paths"):
        alive = [p for p in vote["candidate_paths"] if any(m.get("map_path") == p for m in merged)]
        vote["candidate_paths"] = alive
        if not alive:
            state["vote"] = None

    save_json(POOL_STATE_FILE, state)
    return state


def ready_maps(state: dict) -> List[dict]:
    return [
        m for m in state.get("maps", [])
        if m.get("status") == "ready"
        and m.get("map_path")
        and Path(m["map_path"]).exists()
    ]


def votable_ready_maps(state: dict) -> List[dict]:
    # FIX #3: exclude seeds that were already used in a previous vote/wipe cycle
    used_seeds = set(state.get("used_in_vote_seeds") or [])
    return [m for m in ready_maps(state) if m.get("map_url") and m.get("seed") not in used_seeds]



def _now_ts() -> float:
    return time.time()


def prune_remote_inflight(state: Optional[dict] = None, ttl_seconds: Optional[int] = None) -> dict:
    """
    RustMaps keeps generation jobs server-side. If the script was restarted or
    the pool was cleared while jobs were still running, launching a new full
    batch can push the account above the RustMaps concurrency limit. We persist
    a lightweight remote_inflight list and treat fresh entries as occupied
    RustMaps slots until the job finishes or expires.
    """
    state = state or ensure_state()
    try:
        timeout = int(load_settings().get("rustmaps", {}).get("generate_timeout_seconds", 1800) or 1800)
    except Exception:
        timeout = 1800
    ttl = int(ttl_seconds or max(1800, timeout + 600))
    now = _now_ts()
    fresh = []
    for item in state.get("remote_inflight", []) or []:
        try:
            started = float(item.get("started_at_ts") or 0)
        except Exception:
            started = 0
        if started and now - started <= ttl:
            fresh.append(item)
    if len(fresh) != len(state.get("remote_inflight", []) or []):
        state["remote_inflight"] = fresh
        save_json(POOL_STATE_FILE, state)
    return state


def remote_inflight_count(state: Optional[dict] = None) -> int:
    state = prune_remote_inflight(state)
    return len(state.get("remote_inflight", []) or [])


def add_remote_inflight(seeds: list[int], epoch: int) -> None:
    state = prune_remote_inflight()
    existing = {int(x.get("seed")) for x in state.get("remote_inflight", []) or [] if str(x.get("seed", "")).isdigit()}
    now = _now_ts()
    for seed in seeds:
        if int(seed) not in existing:
            state.setdefault("remote_inflight", []).append({"seed": int(seed), "epoch": int(epoch), "started_at_ts": now})
    save_json(POOL_STATE_FILE, state)


def remove_remote_inflight(seeds: list[int]) -> None:
    seed_set = {int(s) for s in seeds if str(s).isdigit() or isinstance(s, int)}
    state = ensure_state()
    state["remote_inflight"] = [x for x in (state.get("remote_inflight", []) or []) if int(x.get("seed") or -1) not in seed_set]
    save_json(POOL_STATE_FILE, state)


def bump_generation_epoch(reason: str = "manual") -> int:
    state = ensure_state()
    state["generation_epoch"] = int(state.get("generation_epoch", 0) or 0) + 1
    # Do NOT clear remote_inflight here: those RustMaps jobs may still occupy account slots.
    save_json(POOL_STATE_FILE, state)
    append_runtime_log(f"generation epoch bumped | epoch={state['generation_epoch']} | reason={reason}")
    return int(state["generation_epoch"])

def active_generation_count() -> int:
    # Prefer persisted RustMaps in-flight slots because RustMaps jobs can outlive
    # the dashboard process and still count against account concurrency.
    remote = remote_inflight_count()
    generation = load_json(GEN_STATUS_FILE, {})
    local = 0
    if generation.get("running"):
        active = generation.get("active_generations")
        if isinstance(active, int) and active >= 0:
            local = active
        else:
            msg = str(generation.get("message") or "")
            if "Ручная генерация" in msg or "Генерация" in msg:
                for token in msg.split():
                    if token.isdigit():
                        local = int(token); break
            if local <= 0:
                local = 1
    return max(remote, local)


def prune_unwipable_ready_maps(state: dict) -> int:
    """
    Non-destructive validation for ready maps.
    Old behavior removed maps that temporarily lacked map_url, which could wipe
    the whole pool after a schedule/settings save. We now keep such maps on disk
    and only count them for diagnostics. Reconcile/metadata recovery may still
    populate map_url later from artifact files.
    """
    missing_url = 0
    for m in state.get("maps", []):
        is_ready = m.get("status") == "ready"
        has_path = bool(m.get("map_path")) and Path(m["map_path"]).exists()
        has_url = bool(m.get("map_url"))
        if is_ready and has_path and not has_url:
            missing_url += 1
    return missing_url


def count_ready_maps(state: dict) -> int:
    return len(ready_maps(state))


def pop_queued_extra_generations() -> int:
    state = ensure_state()
    queued = int(state.get("queued_extra_generations", 0) or 0)
    if queued > 0:
        state["queued_extra_generations"] = 0
        save_json(POOL_STATE_FILE, state)
    return max(0, queued)


def add_queued_extra_generations(count: int) -> int:
    state = ensure_state()
    state["queued_extra_generations"] = int(state.get("queued_extra_generations", 0) or 0) + max(0, int(count or 0))
    save_json(POOL_STATE_FILE, state)
    return int(state.get("queued_extra_generations", 0) or 0)


class RustMapsCLI:
    def __init__(self, cfg: dict):
        self.binary = cfg["binary"]
        self.api_key = cfg["api_key"]
        self.downloads_dir = Path(cfg["downloads_dir"])
        self.timeout_seconds = int(cfg["generate_timeout_seconds"])
        self.log_level = cfg["log_level"]

    def ensure_installed(self) -> None:
        p = Path(self.binary)
        if not p.exists():
            raise RuntimeError(f"Binary not found: {self.binary}")
        os.chmod(self.binary, 0o755)

    def _run_stream(self, args: List[str], timeout: Optional[int] = None) -> str:
        os.chmod(self.binary, 0o755)
        cmd = [self.binary] + args
        line = "CLI run: " + " ".join(cmd)
        log.info(line)
        append_gen_output(line)

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        start = time.time()
        lines: List[str] = []
        last_progress = 0.0

        assert process.stdout is not None
        try:
            for raw_line in iter(process.stdout.readline, ""):
                out = raw_line.rstrip()
                if not out:
                    continue
                lines.append(out)
                log.info("CLI | %s", out)
                append_gen_output(out)

                now = time.time()
                if now - last_progress >= 60:
                    elapsed = int(now - start)
                    progress_line = f"CLI progress | elapsed={elapsed // 60:02d}:{elapsed % 60:02d}"
                    log.info(progress_line)
                    append_gen_output(progress_line)
                    last_progress = now

                if timeout and now - start > timeout:
                    process.kill()
                    raise TimeoutError("RustMaps CLI timeout")
        finally:
            try:
                process.stdout.close()
            except Exception:
                pass

        rc = process.wait(timeout=15)
        output = "\n".join(lines)
        append_gen_output(f"CLI exit={rc}")
        if rc != 0:
            raise RuntimeError(f"CLI failed rc={rc}\n{output[-6000:]}")
        return output

    def auth(self) -> None:
        self._run_stream(["auth", self.api_key], timeout=180)

    def generate_one(self, seed: int, size: int, saved_config: str, staging: bool = False) -> Dict[str, Any]:
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        run_dir = self.downloads_dir / f"{datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')}_{seed}_{uuid.uuid4().hex[:8]}"
        run_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "--log-level", self.log_level,
            "generate",
            "--size", str(size),
            "--seed", str(seed),
            "--saved-config", saved_config,
            "-d",
            "-o", str(run_dir),
        ]
        if staging:
            cmd.append("--staging")

        output = self._run_stream(cmd, timeout=self.timeout_seconds)


        map_urls = re.findall(r'https://maps\.rustmaps\.com/[^\s"]+\.map', output)
        page_urls = re.findall(r'https://rustmaps\.com/map/[^\s"]+', output)
        map_ids = re.findall(r'"map_id":"([a-f0-9]+)"', output)

        map_url = map_urls[-1] if map_urls else None
        if not map_url:
            raise RuntimeError("No .map URL found in CLI output")

        map_path = next(iter(sorted(run_dir.rglob("*.map"), key=lambda x: x.stat().st_mtime, reverse=True)), None)
        if not map_path:
            raise RuntimeError("Generated .map file not found")

        new_pngs = list(sorted(run_dir.rglob("*.png"), key=lambda x: x.stat().st_mtime, reverse=True))
        image_path = None
        icons_path = None
        thumbnail_path = None
        for p in new_pngs:
            n = p.name.lower()
            if n.endswith("_icons.png") and not icons_path:
                icons_path = str(p)
            elif n.endswith("_thumbnail.png") and not thumbnail_path:
                thumbnail_path = str(p)
            elif not image_path:
                image_path = str(p)

        return {
            "seed": seed,
            "size": size,
            "map_url": map_url,
            "page_url": page_urls[-1] if page_urls else None,
            "map_id": map_ids[-1] if map_ids else None,
            "map_path": str(map_path),
            "image_path": image_path,
            "icons_path": icons_path,
            "thumbnail_path": thumbnail_path,
            "created_at": time.time(),
            "status": "ready",
            "message_id": None,
        }



def _fmt_wipe_time_for_webhook(value: Optional[str]) -> str:
    if not value:
        return "Unknown"
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.strftime("%d.%m.%Y %H:%M:%S")
    except Exception:
        return str(value)


def _next_wipe_for_webhook(settings: dict) -> str:
    try:
        mode, target_at, _ = compute_next_wipe_target(settings)
        if target_at:
            label = "Full wipe" if mode == "full" else "Ordinary wipe"
            return f"{label}: {target_at.strftime('%d.%m.%Y %H:%M:%S')}"
    except Exception as e:
        append_runtime_log(f"webhook next wipe compute error | {e}")
    return "Unknown"


def send_wipe_webhook(map_data: dict, wipe_mode: Optional[str] = None) -> None:
    settings = load_settings()
    cfg = settings.get("notifications", {}) or {}
    url = str(cfg.get("wipe_webhook_url") or "").strip()
    if not url or not bool(cfg.get("enabled", False)):
        return

    server_name = str(cfg.get("server_name") or "YOUR SERVER NAME").strip()
    brand = str(cfg.get("server_brand") or "YOUR BRAND").strip()
    connect_address = str(cfg.get("connect_address") or "").strip()
    next_wipe = _next_wipe_for_webhook(settings)
    seed = str(map_data.get("seed") or "—")
    size = str(map_data.get("size") or "—")
    wipe_title = "FULL WIPE" if str(wipe_mode or "").lower() == "full" else "JUST WIPED"
    wipe_type_val = "Full Wipe" if str(wipe_mode or "").lower() == "full" else "Ordinary Wipe"
    mode_text = "Full wipe" if str(wipe_mode or "").lower() == "full" else "Wipe"

    fields = [
        {"name": "Wipe Type", "value": wipe_type_val, "inline": True},
        {"name": "Map Seed", "value": seed, "inline": True},
        {"name": "Map Size", "value": size, "inline": True},
    ]
    if connect_address:
        fields.append({"name": "Server IP", "value": connect_address, "inline": False})
        fields.append({"name": "Console Command", "value": f"```connect {connect_address}```", "inline": False})
    if map_data.get("page_url"):
        fields.append({"name": "Map Details", "value": str(map_data.get("page_url")), "inline": False})
    elif map_data.get("map_url"):
        fields.append({"name": "Map URL", "value": str(map_data.get("map_url")), "inline": False})
    fields.append({"name": "Next Wipe Date", "value": next_wipe, "inline": False})

    embed = {
        "title": server_name,
        "description": f"**{wipe_title}**\n{brand} is online after wipe.",
        "color": 0x00ff66,
        "fields": fields,
        "footer": {"text": f"{brand} • {mode_text}"},
    }

    preview = map_data.get("icons_path") or map_data.get("image_path") or map_data.get("thumbnail_path")
    files = None
    try:
        payload = {"username": brand, "content": "@everyone", "allowed_mentions": {"parse": ["everyone"]}, "embeds": [embed]}
        if preview and Path(str(preview)).exists():
            embed["image"] = {"url": "attachment://wipe_map.png"}
            files = {
                "payload_json": (None, json.dumps(payload, ensure_ascii=False), "application/json"),
                "file": ("wipe_map.png", open(str(preview), "rb"), "image/png"),
            }
            r = requests.post(url, files=files, timeout=15)
        else:
            r = requests.post(url, json=payload, timeout=15)
        if r.status_code >= 300:
            append_runtime_log(f"wipe webhook failed | status={r.status_code} body={r.text[:300]}")
        else:
            append_runtime_log("wipe webhook sent")
    except Exception as e:
        append_runtime_log(f"wipe webhook exception | {e}")
    finally:
        try:
            if files and files.get("file"):
                files["file"][1].close()
        except Exception:
            pass

class PterodactylClient:
    def __init__(self, cfg: dict):
        self.panel_url = cfg["panel_url"].rstrip("/")
        self.server_id = cfg["server_id"]
        self.timeout = int(cfg["request_timeout"])
        self.s = requests.Session()
        self.s.headers.update({
            "Authorization": f"Bearer {cfg['api_key']}",
            "Accept": "Application/vnd.pterodactyl.v1+json",
            "Content-Type": "application/json",
        })

    def _u(self, path: str) -> str:
        return f"{self.panel_url}/api/client/servers/{self.server_id}{path}"

    def power(self, signal: str) -> None:
        log.info("Pterodactyl power -> %s", signal)
        r = self.s.post(self._u("/power"), json={"signal": signal}, timeout=self.timeout)
        log.info("Pterodactyl power response signal=%s status=%s body=%s", signal, r.status_code, r.text[:400])
        if r.status_code not in (200, 202, 204):
            raise RuntimeError(f"Power {signal} failed: {r.status_code} {r.text[:400]}")

    def send_command(self, command: str) -> None:
        command = str(command or "").strip()
        if not command:
            return
        log.info("Pterodactyl command -> %s", command)
        r = self.s.post(self._u("/command"), json={"command": command}, timeout=self.timeout)
        log.info("Pterodactyl command response status=%s body=%s", r.status_code, r.text[:400])
        if r.status_code not in (200, 202, 204):
            raise RuntimeError(f"Command failed: {r.status_code} {r.text[:400]}")

    def get_resources(self) -> dict:
        r = self.s.get(self._u("/resources"), timeout=self.timeout)
        log.info("Pterodactyl resources response status=%s body=%s", r.status_code, r.text[:400])
        r.raise_for_status()
        return r.json()

    def current_state(self) -> str:
        try:
            payload = self.get_resources()
            attrs = payload.get("attributes", {}) if isinstance(payload, dict) else {}
            return str(attrs.get("current_state") or attrs.get("state") or "unknown").lower()
        except Exception as e:
            append_runtime_log(f"pterodactyl state check failed | {e}")
            return "unknown"

    async def wait_until_running(self, timeout_seconds: int = 900, stable_seconds: int = 30) -> bool:
        deadline = time.time() + max(60, int(timeout_seconds or 900))
        running_since = None
        while time.time() < deadline:
            state = self.current_state()
            append_runtime_log(f"waiting server running | state={state}")
            if state == "running":
                if running_since is None:
                    running_since = time.time()
                if time.time() - running_since >= max(0, int(stable_seconds or 0)):
                    return True
            else:
                running_since = None
            await asyncio.sleep(10)
        return False

    def get_startup(self) -> dict:
        log.info("Pterodactyl GET /startup")
        r = self.s.get(self._u("/startup"), timeout=self.timeout)
        log.info("Pterodactyl startup response status=%s body=%s", r.status_code, r.text[:700])
        r.raise_for_status()
        return r.json()

    def try_update_startup_variable(self, variable_name: str, value: str) -> bool:
        attempts = [
            ("PUT", {"key": variable_name, "value": value}),
            ("PATCH", {"key": variable_name, "value": value}),
            ("POST", {"key": variable_name, "value": value}),
            ("PUT", {"variable": variable_name, "value": value}),
            ("PATCH", {"variable": variable_name, "value": value}),
            ("POST", {"variable": variable_name, "value": value}),
        ]
        for method, payload in attempts:
            log.info("Trying startup variable update: %s via %s", variable_name, method)
            r = self.s.request(method, self._u("/startup/variable"), json=payload, timeout=self.timeout)
            log.info("Startup variable response status=%s body=%s", r.status_code, r.text[:700])
            if r.status_code in (200, 204):
                return True
        return False

    def list_files(self, directory: str) -> list[dict]:
        directory = "/" + directory.strip("/") if directory else "/"
        r = self.s.get(self._u(f"/files/list?directory={quote(directory, safe='/')}"), timeout=self.timeout)
        log.info("Pterodactyl files list dir=%s status=%s body=%s", directory, r.status_code, r.text[:500])
        r.raise_for_status()
        data = r.json().get("data", [])
        out = []
        for item in data:
            attrs = item.get("attributes", item) if isinstance(item, dict) else {}
            if attrs:
                out.append(attrs)
        return out

    def delete_files(self, root: str, files: list[str]) -> None:
        files = [f for f in files if f]
        if not files:
            return
        root = "/" + root.strip("/") if root else "/"
        r = self.s.post(self._u("/files/delete"), json={"root": root, "files": files}, timeout=self.timeout)
        log.info("Pterodactyl files delete root=%s files=%s status=%s body=%s", root, files, r.status_code, r.text[:500])
        if r.status_code not in (200, 202, 204):
            raise RuntimeError(f"File delete failed: {r.status_code} {r.text[:400]}")

    def delete_globs(self, patterns: list[str]) -> int:
        by_dir: dict[str, list[str]] = {}
        for pat in patterns or []:
            pat = str(pat).strip().strip('/')
            if not pat:
                continue
            directory, mask = pat.rsplit('/', 1) if '/' in pat else ('', pat)
            by_dir.setdefault(directory, []).append(mask)

        deleted = 0
        for directory, masks in by_dir.items():
            try:
                entries = self.list_files(directory)
            except Exception as e:
                append_runtime_log(f"file list failed | dir={directory or '/'} | {e}")
                continue
            files = []
            for entry in entries:
                name = str(entry.get('name') or '')
                is_file = bool(entry.get('is_file', False)) or str(entry.get('mode', '')).startswith('-')
                if not name or not is_file:
                    continue
                if any(fnmatch.fnmatch(name, mask) for mask in masks):
                    files.append(name)
            if not files:
                append_runtime_log(f"ptero delete globs | dir={directory or '/'} | matched=0")
                continue
            try:
                self.delete_files(directory, files)
                deleted += len(files)
                append_runtime_log(f"ptero deleted files | dir={directory or '/'} | count={len(files)} | {', '.join(files[:8])}")
            except Exception as e:
                append_runtime_log(f"file delete failed | dir={directory or '/'} | {e}")
        return deleted


def find_candidate_startup_vars(payload: dict) -> List[str]:
    found = []

    def walk(obj):
        if isinstance(obj, dict):
            if "env_variable" in obj:
                found.append(str(obj["env_variable"]))
            if "name" in obj and isinstance(obj["name"], str):
                found.append(str(obj["name"]))
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(payload.get("data") or payload.get("attributes") or payload)

    dedup = []
    for v in found:
        if v not in dedup:
            dedup.append(v)

    priority = []
    exact = ["MAP_URL", "Custom Map URL"]
    for v in exact:
        if v not in priority:
            priority.append(v)

    for v in dedup:
        upper = v.upper()
        if ("MAP" in upper and "URL" in upper) or upper == "URL":
            if v not in priority:
                priority.append(v)

    final = []
    for v in priority + [v for v in dedup if v not in priority]:
        if v not in final:
            final.append(v)
    return final


def _generate_map_task(rust_cfg: dict, seed: int) -> Dict[str, Any]:
    cli = RustMapsCLI(rust_cfg)
    cli.ensure_installed()
    
    settings = load_settings()
    use_staging = False
    try:
        mode, target_at, seconds_left = compute_next_wipe_target(settings)
        if target_at is not None:
            is_force = (target_at.weekday() == 3 and target_at.day <= 7)
            # If less than 48 hours (172800 seconds) remain until the Force wipe
            if is_force and seconds_left <= 172800:
                use_staging = True
    except Exception as e:
        log.error(f"Error checking staging condition for map generation: {e}")
        
    return cli.generate_one(
        seed=seed, 
        size=int(rust_cfg["size"]), 
        saved_config=str(rust_cfg["saved_config"]),
        staging=use_staging
    )



def fill_pool_worker(mode: str = "target", manual_count: int = 0):
    settings = load_settings()
    rust_cfg = settings["rustmaps"]
    target = int(rust_cfg["target_pool_size"])
    # Use RustMaps account capacity more aggressively: auto/manual batches may go up to 7.
    configured_concurrency = max(1, min(7, int(rust_cfg.get("concurrent_generations", 3) or 3)))
    fill_pool_batch_max = max(1, min(7, int(rust_cfg.get("fill_pool_batch_max", 5) or 5)))
    fill_pool_full_immediately = bool(rust_cfg.get("fill_pool_full_immediately", False))
    manual_count = max(1, min(7, int(manual_count or 1)))
    desired_total = target if mode == "target" else 0
    generated_manual = 0

    try:
        update_gen_status(
            running=True,
            stage="auth",
            message="Проверка RustMaps API key" if mode == "target" else f"Ручная генерация {manual_count} карт: проверка RustMaps API key",
            started_at=datetime.utcnow().isoformat() + "Z",
            error=None,
            current_index=0,
            target_index=target if mode == "target" else manual_count,
            last_output=[],
        )
        cli = RustMapsCLI(rust_cfg)
        cli.ensure_installed()
        cli.auth()

        state = reconcile_pool_state()
        worker_epoch = int(state.get("generation_epoch", 0) or 0)
        ready = count_ready_maps(state)

        if mode == "target":
            # Fill-to-target uses the real pool count and current target. This fixes
            # stale progress after clearing the pool while generation is running.
            settings = load_settings()
            rust_cfg = settings["rustmaps"]
            target = int(rust_cfg.get("target_pool_size", target) or target)
            configured_concurrency = max(1, min(7, int(rust_cfg.get("concurrent_generations", configured_concurrency) or configured_concurrency)))
            fill_pool_batch_max = max(1, min(7, int(rust_cfg.get("fill_pool_batch_max", fill_pool_batch_max) or fill_pool_batch_max)))
            fill_pool_full_immediately = bool(rust_cfg.get("fill_pool_full_immediately", fill_pool_full_immediately))
            desired_total = target + pop_queued_extra_generations()
        else:
            desired_total = ready + manual_count

        update_gen_status(
            running=True,
            stage="scan",
            message=(f"Найдено готовых карт: {ready}/{target}" if mode == "target" else f"Ручная генерация: добавить {manual_count} карт"),
            current_index=ready if mode == "target" else 0,
            target_index=desired_total if mode == "target" else manual_count,
        )

        while True:
            # Re-read settings and pool state before every batch. Dashboard actions
            # can change the pool while this worker is alive.
            state = reconcile_pool_state()
            ready = count_ready_maps(state)

            if mode == "target":
                settings = load_settings()
                rust_cfg = settings["rustmaps"]
                target = int(rust_cfg.get("target_pool_size", target) or target)
                configured_concurrency = max(1, min(7, int(rust_cfg.get("concurrent_generations", configured_concurrency) or configured_concurrency)))
                fill_pool_batch_max = max(1, min(7, int(rust_cfg.get("fill_pool_batch_max", fill_pool_batch_max) or fill_pool_batch_max)))
                fill_pool_full_immediately = bool(rust_cfg.get("fill_pool_full_immediately", fill_pool_full_immediately))
                desired_total = max(desired_total, target)
                queued_now = pop_queued_extra_generations()
                if queued_now:
                    desired_total += queued_now
                    append_runtime_log(f"queued extra generations accepted | +{queued_now} | desired_total={desired_total}")

            missing = max(0, desired_total - ready)
            if missing <= 0:
                break

            # RustMaps account concurrency guard. Do not launch more local jobs than
            # configured_concurrency minus fresh remote in-flight jobs from previous batches/restarts.
            state = prune_remote_inflight(state)
            in_flight = remote_inflight_count(state)
            capacity = max(1, min(7, configured_concurrency))
            available_slots = max(0, capacity - in_flight)
            if available_slots <= 0:
                update_gen_status(
                    running=True,
                    stage="wait_capacity",
                    message=f"Ожидание свободных слотов RustMaps | занято {in_flight}/{capacity} | готово {ready}/{desired_total}",
                    current_index=ready if mode == "target" else generated_manual,
                    target_index=desired_total if mode == "target" else manual_count,
                    active_generations=in_flight,
                )
                append_runtime_log(f"rustmaps capacity wait | in_flight={in_flight}/{capacity} ready={ready}/{desired_total}")
                time.sleep(30)
                continue

            if mode == "target":
                desired_batch = missing if fill_pool_full_immediately else min(missing, fill_pool_batch_max)
                batch = min(available_slots, desired_batch, missing)
            else:
                batch = min(available_slots, missing)

            seeds = []
            while len(seeds) < batch:
                seed = random.randint(1, 2_147_483_647)
                if seed not in seeds:
                    seeds.append(seed)

            add_remote_inflight(seeds, worker_epoch)

            update_gen_status(
                running=True,
                stage="generate",
                message=(f"Генерация {batch} карт параллельно | готово {ready}/{desired_total}" if mode == "target"
                         else f"Ручная генерация {batch} карт параллельно | готово {generated_manual}/{manual_count}"),
                current_seed=None,
                current_index=ready if mode == "target" else generated_manual,
                target_index=desired_total if mode == "target" else manual_count,
                active_generations=batch,
            )
            append_runtime_log(
                f"parallel generation batch started | batch={batch} configured={configured_concurrency} in_flight_before={in_flight} desired_max={fill_pool_batch_max} full_now={fill_pool_full_immediately} ready={ready}/{desired_total}"
                if mode == "target" else
                f"manual generation batch started | batch={batch} configured={configured_concurrency} progress={generated_manual}/{manual_count}"
            )

            items = []
            completed_seeds = []
            with ThreadPoolExecutor(max_workers=batch) as ex:
                futures = {ex.submit(_generate_map_task, rust_cfg, seed): seed for seed in seeds}
                for fut in as_completed(futures):
                    seed = futures[fut]
                    completed_seeds.append(seed)
                    try:
                        item = fut.result()
                        items.append(item)
                        append_runtime_log(f"generated map | seed={seed}")
                    except Exception as e:
                        append_runtime_log(f"generate failed | seed={seed} | {e}")
                    finally:
                        remove_remote_inflight([seed])

            current_epoch = int(ensure_state().get("generation_epoch", 0) or 0)
            if current_epoch != worker_epoch:
                for item in items:
                    try:
                        delete_map_files(item, reason="old_generation_epoch", allow_ready=True)
                    except Exception:
                        pass
                append_runtime_log(f"discarded generated maps from old epoch | worker={worker_epoch} current={current_epoch} count={len(items)}")
                update_gen_status(running=False, stage="cancelled", message="Генерация остановлена: пул был очищен или сброшен", active_generations=active_generation_count())
                return

            if items:
                state = reconcile_pool_state()
                cleanup_orphaned_in_vote_maps()
                state = reconcile_pool_state()
                existing = {m.get("map_path") for m in state.get("maps", [])}
                added = 0
                for item in items:
                    if item.get("map_path") not in existing:
                        state["maps"].append(item)
                        existing.add(item.get("map_path"))
                        added += 1
                save_json(POOL_STATE_FILE, state)
                state = reconcile_pool_state()
                ready = count_ready_maps(state)
                if mode == "manual":
                    generated_manual = min(manual_count, ready - max(0, desired_total - manual_count))
                update_gen_status(
                    running=True,
                    stage="generate",
                    message=(f"Пул обновлён: {ready}/{desired_total} | добавлено {added}" if mode == "target"
                             else f"Ручная генерация: {min(manual_count, generated_manual)}/{manual_count} | добавлено {added}"),
                    current_index=ready if mode == "target" else min(manual_count, generated_manual),
                    target_index=desired_total if mode == "target" else manual_count,
                )
            else:
                raise RuntimeError("Ни одна карта в параллельной генерации не была создана")

        final_ready = count_ready_maps(reconcile_pool_state())
        update_gen_status(
            running=False,
            stage="complete",
            message=(f"Пул готов: {final_ready}/{target}" if mode == "target" else f"Ручная генерация завершена: {manual_count}/{manual_count}"),
            current_seed=None,
            current_index=final_ready if mode == "target" else manual_count,
            target_index=target if mode == "target" else manual_count,
            active_generations=0,
            error=None,
        )
    except Exception as e:
        log.exception("fill_pool_worker error: %s", e)
        update_gen_status(
            running=False,
            stage="error",
            message="Ошибка генерации пула",
            error=str(e),
        )


def start_fill_pool(mode: str = "target", manual_count: int = 0) -> bool:
    global _pool_thread
    with _worker_lock:
        if _pool_thread and _pool_thread.is_alive():
            if mode == "manual":
                queued = add_queued_extra_generations(max(1, min(7, int(manual_count or 1))))
                append_runtime_log(f"manual generation queued while worker active | +{manual_count} | queued={queued}")
                update_runtime_status(message=f"Manual generation queued: +{manual_count}", last_action="manual_generation_queued")
                return True
            return False
        _pool_thread = threading.Thread(target=fill_pool_worker, kwargs={"mode": mode, "manual_count": manual_count}, daemon=True)
        _pool_thread.start()
        if mode == "manual":
            append_runtime_log(f"manual generation thread started | count={manual_count}")
            update_runtime_status(message=f"Manual generation started: {manual_count}", last_action="manual_generation_started")
        else:
            append_runtime_log("pool fill thread started")
            update_runtime_status(message="Pool fill thread started", last_action="pool_fill_started")
        return True


def start_manual_generation(count: int) -> bool:
    count = max(1, min(7, int(count or 1)))
    return start_fill_pool(mode="manual", manual_count=count)


async def safe_delete_message(channel: discord.TextChannel, message_id: Optional[int]) -> None:
    if not message_id:
        return
    try:
        msg = await channel.fetch_message(message_id)
        await msg.delete()
    except Exception:
        pass


def _safe_reason_slug(reason: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(reason or "unknown"))[:48] or "unknown"


def _move_to_deleted_maps(src: Path, map_item: dict, reason: str, key: str) -> bool:
    """Soft-delete a generated map artifact by moving it to _deleted_maps.

    This makes destructive dashboard actions reversible from the file manager:
    <downloads_dir>/_deleted_maps/<timestamp>_<reason>_<seed>/...
    """
    try:
        if not src.exists():
            return False
        try:
            downloads_dir = Path(load_settings()["rustmaps"].get("downloads_dir") or BASE_DIR / "rustmaps_vote_pool").resolve()
            rel = src.resolve().relative_to(downloads_dir)
        except Exception:
            rel = Path(src.name)
        seed = str(map_item.get("seed") or "unknown")
        stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        folder = DELETED_MAPS_DIR / f"{stamp}_{_safe_reason_slug(reason)}_{seed}"
        dst = folder / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        # Avoid collisions if several artifacts have the same relative name.
        if dst.exists():
            dst = dst.with_name(dst.stem + "_" + uuid.uuid4().hex[:8] + dst.suffix)
        audit_map_delete(f"{reason} -> moved_to={dst}", map_item, key=key)
        shutil.move(str(src), str(dst))
        return True
    except Exception as e:
        append_runtime_log(f"MAP SOFT DELETE FAILED | reason={reason} | key={key} | seed={map_item.get('seed')} | path={src} | {e}")
        return False


def delete_map_files(map_item: dict, reason: str = "unknown", allow_ready: bool = False) -> bool:
    """Soft-delete map artifacts with audit logging and ready-map protection.

    Ready maps are protected by default. Destructive operations must pass
    allow_ready=True and a clear reason. Files are moved to _deleted_maps,
    not unlinked, so accidental deletes can be recovered manually.
    """
    if is_ready_map_protected(map_item) and not allow_ready:
        append_runtime_log(f"MAP DELETE BLOCKED | reason={reason} | seed={map_item.get('seed')} | ready map is protected")
        return False

    deleted_any = False
    seen = set()
    for key in ["map_path", "image_path", "icons_path", "thumbnail_path"]:
        raw = map_item.get(key)
        if not raw:
            continue
        src = Path(str(raw))
        if str(src) in seen or DELETED_MAPS_DIR in src.parents:
            continue
        seen.add(str(src))
        if src.exists():
            deleted_any = _move_to_deleted_maps(src, map_item, reason, key) or deleted_any

    mp = map_item.get("map_path")
    if mp:
        stem = Path(mp).stem
        parent = Path(mp).parent
        for suffix in ["_download_links.json", "_specs.json"]:
            src = parent / f"{stem}{suffix}"
            if src.exists() and DELETED_MAPS_DIR not in src.parents:
                deleted_any = _move_to_deleted_maps(src, map_item, reason, suffix) or deleted_any
    return deleted_any



def archive_map_files(map_item: dict, reason: str = "wipe_selected") -> bool:
    """Copy the selected/wiped map artifacts into _wiped_maps_archive before destructive actions.

    This is a non-destructive backup: the original files stay in place. Later
    cleanup/delete may move them into _deleted_maps, but the archive keeps a
    copy of the map that was actually used for a wipe.
    """
    copied_any = False
    try:
        seed = str(map_item.get("seed") or "unknown")
        stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        folder = WIPED_MAPS_ARCHIVE_DIR / f"{stamp}_{_safe_reason_slug(reason)}_{seed}"
        folder.mkdir(parents=True, exist_ok=True)
        seen = set()
        for key in ["map_path", "image_path", "icons_path", "thumbnail_path"]:
            raw = map_item.get(key)
            if not raw:
                continue
            src = Path(str(raw))
            if not src.exists() or str(src) in seen or DELETED_MAPS_DIR in src.parents:
                continue
            seen.add(str(src))
            dst = folder / src.name
            if dst.exists():
                dst = dst.with_name(dst.stem + "_" + uuid.uuid4().hex[:8] + dst.suffix)
            shutil.copy2(str(src), str(dst))
            copied_any = True
        mp = map_item.get("map_path")
        if mp:
            stem = Path(mp).stem
            parent = Path(mp).parent
            for suffix in ["_download_links.json", "_specs.json"]:
                src = parent / f"{stem}{suffix}"
                if src.exists():
                    dst = folder / src.name
                    if dst.exists():
                        dst = dst.with_name(dst.stem + "_" + uuid.uuid4().hex[:8] + dst.suffix)
                    shutil.copy2(str(src), str(dst))
                    copied_any = True
        if copied_any:
            append_runtime_log(f"MAP ARCHIVED | reason={reason} | seed={seed} | folder={folder}")
        return copied_any
    except Exception as e:
        append_runtime_log(f"MAP ARCHIVE FAILED | reason={reason} | seed={map_item.get('seed')} | {e}")
        return False



def clear_selected_state(state: dict, keep_error: bool = False) -> dict:
    selected_path = state.get("selected_map_path")
    for m in state.get("maps", []):
        if m.get("map_path") == selected_path and m.get("status") == "selected":
            m["status"] = "ready"
    state["selected_map_path"] = None
    state["selected_at"] = None
    state["winner_message_id"] = None
    state["wipe_attempt_in_progress"] = False
    if not keep_error:
        state["wipe_error"] = None
        state["wipe_error_notified"] = False
    state["scheduled_wipe_mode"] = None
    state["scheduled_wipe_requested_at"] = None
    state["scheduled_wipe_target_at"] = None
    state["vote_window_consumed_target_at"] = None
    return state


def cleanup_stuck_selected_state(max_age_minutes: int = 15) -> bool:
    state = ensure_state()
    selected_path = state.get("selected_map_path")
    if not selected_path or state.get("wipe_attempt_in_progress"):
        return False
    if not state.get("wipe_error"):
        return False
    selected_at = state.get("selected_at")
    if selected_at:
        try:
            from datetime import timezone
            ts = datetime.fromisoformat(selected_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            if (now - ts).total_seconds() < max_age_minutes * 60:
                return False
        except Exception:
            pass
    clear_selected_state(state, keep_error=False)
    save_json(POOL_STATE_FILE, state)
    append_runtime_log("stuck selected state cleared")
    update_runtime_status(message="Зависший selected сброшен", last_action="selected_reset")
    return True


_last_disk_cleanup_ts = 0

def cleanup_old_deleted_and_archived_maps(max_age_days: int = 3):
    global _last_disk_cleanup_ts
    now = time.time()
    # Run once every 6 hours
    if now - _last_disk_cleanup_ts < 21600:
        return
    _last_disk_cleanup_ts = now
    
    append_runtime_log(f"Running disk cleanup for old deleted/archived maps (max_age_days={max_age_days})")
    
    max_age_seconds = max_age_days * 24 * 60 * 60
    cleaned_count = 0

    if DELETED_MAPS_DIR.exists():
        for item in DELETED_MAPS_DIR.iterdir():
            try:
                mtime = item.stat().st_mtime
                if now - mtime > max_age_seconds:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                    cleaned_count += 1
            except Exception as e:
                append_runtime_log(f"Failed to remove deleted map {item.name}: {e}")

    if WIPED_MAPS_ARCHIVE_DIR.exists():
        for item in WIPED_MAPS_ARCHIVE_DIR.iterdir():
            try:
                mtime = item.stat().st_mtime
                if now - mtime > max_age_seconds:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                    cleaned_count += 1
            except Exception as e:
                append_runtime_log(f"Failed to remove archived map {item.name}: {e}")

    if cleaned_count > 0:
        append_runtime_log(f"Disk cleanup completed: removed {cleaned_count} old map folders/files")


def _wipe_paths_from_flags(flags: dict) -> List[str]:
    paths = []
    if flags.get("remove_map"):
        paths.append("server/rust/*.map")
    if flags.get("remove_sav"):
        paths.append("server/rust/*.sav")
    if flags.get("remove_occlusion"):
        paths.append("server/rust/*_occlusion_*.dat")
    if flags.get("remove_bp_db"):
        paths.append("server/rust/player.blueprints*.db")
    if flags.get("remove_bp_wal"):
        paths.append("server/rust/player.blueprints*.db-wal")
    if flags.get("remove_player_identities"):
        paths.append("server/rust/player.identities*.db")
    if flags.get("remove_player_states"):
        paths.append("server/rust/player.states*.db")
    if flags.get("remove_player_tokens"):
        paths.append("server/rust/player.tokens*.db")
    if flags.get("remove_player_deaths"):
        paths.append("server/rust/player.deaths*.db")
    return paths


def get_effective_wipe_flags(mode: Optional[str], settings: dict) -> dict:
    # Legacy fallback for older settings.json
    mode = (mode or "").strip().lower()
    if mode == "ordinary":
        return {
            "remove_map": True, "remove_sav": True, "remove_occlusion": True,
            "remove_bp_db": False, "remove_bp_wal": False,
            "remove_player_identities": False, "remove_player_states": False,
            "remove_player_tokens": False, "remove_player_deaths": False,
        }
    if mode == "full":
        return {
            "remove_map": True, "remove_sav": True, "remove_occlusion": True,
            "remove_bp_db": True, "remove_bp_wal": True,
            "remove_player_identities": False, "remove_player_states": False,
            "remove_player_tokens": False, "remove_player_deaths": False,
        }
    return dict(settings.get("wipe", {}))


def get_effective_wipe_paths(mode: Optional[str], settings: dict) -> List[str]:
    mode = (mode or "ordinary").strip().lower()
    profile_key = "blueprint" if mode in ("full", "blueprint", "bp") else "ordinary"
    profile = (settings.get("wipe_profiles") or {}).get(profile_key) or {}
    paths = profile.get("paths")
    if isinstance(paths, list):
        clean = []
        for item in paths:
            item = str(item).strip()
            if item.startswith("server/rust/") and item not in clean:
                clean.append(item)
        if clean:
            return clean
    return _wipe_paths_from_flags(get_effective_wipe_flags(mode, settings))


def find_specific_startup_vars(payload: dict, keywords: List[str], exact: List[str] | None = None) -> List[str]:
    exact = exact or []
    found = []
    def walk(obj):
        if isinstance(obj, dict):
            if "env_variable" in obj:
                found.append(str(obj["env_variable"]))
            if "name" in obj and isinstance(obj["name"], str):
                found.append(str(obj["name"]))
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)
    walk(payload.get("data") or payload.get("attributes") or payload)
    dedup = []
    for v in found:
        if v not in dedup:
            dedup.append(v)
    out = []
    for v in exact:
        if v in dedup and v not in out:
            out.append(v)
    for v in dedup:
        u = v.upper()
        if any(k.upper() in u for k in keywords):
            if v not in out:
                out.append(v)
    return out


def remove_map_entry_and_files(state: dict, map_item: dict) -> dict:
    delete_map_files(map_item, reason="remove_map_entry", allow_ready=True)
    state["maps"] = [m for m in state.get("maps", []) if m.get("map_path") != map_item.get("map_path")]
    if state.get("selected_map_path") == map_item.get("map_path"):
        state["selected_map_path"] = None
        state["winner_message_id"] = None
    return state

def cleanup_orphaned_in_vote_maps() -> int:
    """Non-destructive cleanup for stale in_vote states.

    Older versions deleted orphaned in_vote maps from disk. That is dangerous
    during Discord/API hiccups or restarts. Now we only restore existing files
    back to ready and remove missing entries from state.
    """
    state = ensure_state()
    vote = state.get("vote")
    active_paths = set(vote.get("candidate_paths", [])) if vote and vote.get("active") else set()
    changed = 0
    keep_selected = state.get("selected_map_path")
    survivors = []
    for item in state.get("maps", []):
        status = item.get("status")
        path = item.get("map_path")
        if status == "in_vote" and path not in active_paths and path != keep_selected:
            if path and Path(path).exists():
                item = dict(item)
                item["status"] = "ready"
                item["message_id"] = None
                survivors.append(item)
                changed += 1
                append_runtime_log(f"orphaned in_vote restored to ready | seed={item.get('seed')}")
            else:
                changed += 1
                append_runtime_log(f"orphaned in_vote removed from state only | missing file | seed={item.get('seed')}")
            continue
        survivors.append(item)
    if changed:
        state["maps"] = survivors
        save_json(POOL_STATE_FILE, state)
        update_runtime_status(message=f"Stale in_vote maps fixed: {changed}", last_action="cleanup_orphaned_safe")
    return changed


def _publish_target_key(target_at) -> Optional[str]:
    """
    Stable key for the currently scheduled vote target, used to prevent
    duplicate publish attempts for the same wipe window.
    """
    if not target_at:
        return None
    try:
        return target_at.isoformat()
    except Exception:
        try:
            return str(target_at)
        except Exception:
            return None


def is_vote_publish_locked_for_target(state: dict, target_at) -> bool:
    key = _publish_target_key(target_at)
    if not key:
        return False

    current_target = state.get("scheduled_wipe_target_at")
    consumed_target = state.get("vote_window_consumed_target_at")
    last_vote_target = state.get("last_vote_target_at")
    in_progress_target = state.get("vote_publish_in_progress_for_target")

    return key in {current_target, consumed_target, last_vote_target, in_progress_target} and bool(
        state.get("vote") or state.get("selected_map_path") or current_target == consumed_target or current_target == last_vote_target or in_progress_target == key
    )


async def cancel_active_vote(channel: Optional[discord.TextChannel], reason: str = "manual_close", consume_window: bool = True, restore_candidates: bool = True):
    state = ensure_state()
    vote = state.get("vote")
    if not vote:
        return False, "Нет активного голосования"

    candidate_paths = list(vote.get("candidate_paths", []))
    message_ids = dict(vote.get("message_ids", {}))

    if channel is not None:
        for map_path in candidate_paths:
            try:
                await safe_delete_message(channel, message_ids.get(map_path))
            except Exception:
                pass
        
        intro_msg_id = vote.get("intro_message_id")
        if intro_msg_id:
            try:
                await safe_delete_message(channel, intro_msg_id)
                append_runtime_log(f"deleted active vote intro message | id={intro_msg_id}")
            except Exception as e:
                log.warning(f"Failed to delete active vote intro message: {e}")


    for item in state.get("maps", []):
        if item.get("map_path") in candidate_paths:
            if restore_candidates and item.get("status") == "in_vote":
                item["status"] = "ready"
            item["message_id"] = None

    state["vote"] = None
    state["winner_message_id"] = None
    state["selected_map_path"] = None
    state["selected_at"] = None
    state["wipe_attempt_in_progress"] = False
    state["vote_publish_in_progress_for_target"] = None

    if consume_window:
        target_iso = state.get("scheduled_wipe_target_at")
        if target_iso:
            state["vote_window_consumed_target_at"] = target_iso
            state["last_vote_target_at"] = target_iso

    save_json(POOL_STATE_FILE, state)
    append_runtime_log(f"vote cancelled | reason={reason} restored={len(candidate_paths)} consume_window={consume_window}")
    update_runtime_status(message="Голосование закрыто и карты возвращены в пул", last_action="vote_cancelled")
    return True, "Голосование закрыто"

async def publish_vote(channel: discord.TextChannel):
    state = reconcile_pool_state()
    removed_unwipable = prune_unwipable_ready_maps(state)
    if removed_unwipable:
        save_json(POOL_STATE_FILE, state)
        log.warning("Ready maps missing map_url (kept, not deleted): %s", removed_unwipable)
        append_runtime_log(f"ready maps missing map_url (kept): {removed_unwipable}")
        update_runtime_status(message=f"Карт без map_url: {removed_unwipable} (не удалялись)", last_action="prune_unwipable_ready")
    settings = load_settings()
    mode, target_at = ensure_scheduled_target(settings, state)
    publish_target_key = _publish_target_key(target_at)

    if not VOTE_PUBLISH_LOCK.acquire(blocking=False):
        append_runtime_log("publish vote skipped | lock busy")
        return False, "Публикация голосования уже выполняется"

    try:
        latest = reconcile_pool_state()
        if publish_target_key and latest.get("vote_publish_in_progress_for_target") == publish_target_key:
            append_runtime_log(f"publish vote skipped | already in progress for {publish_target_key}")
            return False, "Публикация уже выполняется для этого вайпа"

        if publish_target_key:
            latest["vote_publish_in_progress_for_target"] = publish_target_key
            save_json(POOL_STATE_FILE, latest)

        state = reconcile_pool_state()

        # Keep Discord channel clean: previous winner card stays after wipe,
        # but is removed right before a new vote starts.
        if state.get("winner_message_id") and not state.get("selected_map_path"):
            try:
                await safe_delete_message(channel, state.get("winner_message_id"))
                append_runtime_log("previous winner message deleted before new vote")
            except Exception as e:
                append_runtime_log(f"previous winner message delete failed | {e}")
            state = ensure_state()
            state["winner_message_id"] = None
            save_json(POOL_STATE_FILE, state)

        if state.get("vote"):
            append_runtime_log("publish vote skipped | active vote already exists")
            return False, "Голосование уже активно"
        if state.get("selected_map_path"):
            append_runtime_log("publish vote skipped | selected map exists")
            return False, "Есть выбранная карта, сначала завершите текущий вайп"
        if publish_target_key and state.get("vote_window_consumed_target_at") == publish_target_key:
            append_runtime_log(f"publish vote skipped | target already consumed {publish_target_key}")
            return False, "Для этого окна вайпа голосование уже закрыто/завершено"
        if publish_target_key and state.get("last_vote_target_at") == publish_target_key:
            append_runtime_log(f"publish vote skipped | target already published {publish_target_key}")
            return False, "Для этого окна вайпа голосование уже публиковалось"

        candidates = votable_ready_maps(state)
        if len(candidates) < 3:
            append_runtime_log(f"publish vote skipped | ready maps {len(candidates)}/3")
            return False, f"Недостаточно готовых карт: {len(candidates)}/3"

        candidates = sorted(
            candidates,
            key=lambda m: (
                1 if (m.get("icons_path") or m.get("image_path") or m.get("thumbnail_path")) else 0,
                float(m.get("created_at") or 0),
            ),
            reverse=True,
        )
        chosen = candidates[:3]
        chosen_paths = [m["map_path"] for m in chosen]

        for m in state["maps"]:
            if m["map_path"] in chosen_paths:
                m["status"] = "in_vote"



        state["vote"] = {
            "active": True,
            "candidate_paths": chosen_paths,
            "message_ids": {},
            "intro_message_id": None,
            "user_votes": {},
            "started_at": None,
            "duration": int(load_settings()["schedule"].get("vote_duration_minutes", 60)) * 60,
            "emoji": load_settings()["discord"]["reaction_emoji"],
        }
        save_json(POOL_STATE_FILE, state)

        intro = discord.Embed(
            title="UPCOMING WIPE: MAP VOTE",
            description="Ниже 3 карты. Поставь реакцию на одной карте.\nИтоги будут подведены за 1 минуту до вайпа. Если голосов не будет, карта выберется случайно.",
            color=discord.Color.orange(),
        )
        intro_msg = await channel.send(content="@everyone", embed=intro, allowed_mentions=discord.AllowedMentions(everyone=True))
        latest = ensure_state()
        if latest.get("vote"):
            latest["vote"]["intro_message_id"] = intro_msg.id
            save_json(POOL_STATE_FILE, latest)

        emoji = load_settings()["discord"]["reaction_emoji"]

        for idx, m in enumerate(chosen, start=1):
            desc = f"**Map Seed**\n`{m.get('seed')}`\n\n**Map Size**\n`{m.get('size')}`"
            if m.get("map_url"):
                desc += f"\n\n**Map URL**\n{m['map_url']}"

            embed = discord.Embed(title=f"Map #{idx}", description=desc, color=discord.Color.blue())
            img = m.get("icons_path") or m.get("image_path") or m.get("thumbnail_path")
            file = None
            if img and Path(img).exists():
                fname = f"map_{idx}.png"
                file = discord.File(img, filename=fname)
                embed.set_image(url=f"attachment://{fname}")

            msg = (
                await channel.send(content="@everyone", embed=embed, file=file, allowed_mentions=discord.AllowedMentions(everyone=True))
                if file else
                await channel.send(content="@everyone", embed=embed, allowed_mentions=discord.AllowedMentions(everyone=True))
            )
            await msg.add_reaction(emoji)

            latest = ensure_state()
            latest["vote"]["message_ids"][m["map_path"]] = msg.id
            for item in latest["maps"]:
                if item["map_path"] == m["map_path"]:
                    item["message_id"] = msg.id
            save_json(POOL_STATE_FILE, latest)

        if state.get("scheduled_wipe_target_at"):
            state["last_vote_target_at"] = state.get("scheduled_wipe_target_at")
        save_json(POOL_STATE_FILE, state)
        log.info("Vote published from pool.")
        append_runtime_log(f"vote published | candidates=3")
        return True, "Голосование опубликовано"



    finally:
        try:
            latest = reconcile_pool_state()
            if publish_target_key and latest.get("vote_publish_in_progress_for_target") == publish_target_key:
                latest.pop("vote_publish_in_progress_for_target", None)
                save_json(POOL_STATE_FILE, latest)
        except Exception as e:
            append_runtime_log(f"publish vote cleanup error | {e}")
        VOTE_PUBLISH_LOCK.release()

async def cleanup_missing_vote_messages(channel: discord.TextChannel) -> int:
    """
    Soft Discord consistency check.

    Old behavior removed candidates from pool_state when fetch_message failed.
    Discord can temporarily fail/rate-limit/lose cache even while the messages
    still exist, which made the dashboard show only 1 map while Discord had 3.
    Do not mutate vote.candidate_paths here; only log missing/unfetchable messages.
    Real cleanup happens when the vote is finalized/cancelled.
    """
    state = ensure_state()
    vote = state.get("vote")
    if not vote or not vote.get("active"):
        return 0

    candidate_paths = list(vote.get("candidate_paths", []))
    message_ids = dict(vote.get("message_ids", {}))
    missing = []

    for map_path in candidate_paths:
        message_id = message_ids.get(map_path)
        if not message_id:
            missing.append(map_path)
            continue
        try:
            await channel.fetch_message(int(message_id))
        except discord.errors.HTTPException as he:
            missing.append(map_path)
            if he.status == 401:
                log.error("Discord API returned 401 Unauthorized! The bot token is invalid. Please update it in settings.")
                update_runtime_status(message="Ошибка Discord: Невалидный токен (401 Unauthorized)", last_action="discord_auth_error")
            append_runtime_log(f"vote message fetch skipped | map={map_path} | message_id={message_id} | {he}")
        except Exception as e:
            missing.append(map_path)
            append_runtime_log(f"vote message fetch skipped | map={map_path} | message_id={message_id} | {e}")

    if missing:
        append_runtime_log(f"vote message check: {len(missing)} message(s) not fetchable, vote state kept unchanged")
    return len(missing)


def is_time_to_finalize_vote(state: dict, vote: Optional[dict] = None) -> bool:
    """
    Scheduled logic: if a wipe target exists, close voting 60 seconds before wipe.
    Fallback: for manually published votes without schedule, keep the old duration behavior.
    """
    target_dt = _parse_iso_dt(state.get("scheduled_wipe_target_at"))
    if target_dt is not None:
        now_dt = _schedule_now(tzname=getattr(target_dt.tzinfo, "key", None) or str(target_dt.tzinfo))
        try:
            if getattr(target_dt, "tzinfo", None) is None and getattr(now_dt, "tzinfo", None) is not None:
                target_dt = target_dt.replace(tzinfo=now_dt.tzinfo)
            elif getattr(target_dt, "tzinfo", None) is not None and getattr(now_dt, "tzinfo", None) is None:
                now_dt = now_dt.replace(tzinfo=target_dt.tzinfo)
        except Exception:
            pass
        return (target_dt - now_dt).total_seconds() <= 60

    # No schedule target: old manual behavior.
    if not vote or vote.get("started_at") is None:
        return False
    try:
        return now_ts() >= float(vote["started_at"]) + int(vote.get("duration") or 0)
    except Exception:
        return False

async def process_vote_if_expired(channel: discord.TextChannel):
    state = ensure_state()
    if state.get("selected_map_path") or state.get("wipe_attempt_in_progress"):
        append_runtime_log("process_vote_if_expired skipped | wipe already in progress or selected exists")
        return
    vote = state.get("vote")
    if not vote or not vote.get("active"):
        return

    if not is_time_to_finalize_vote(state, vote):
        return

    counts: Dict[str, int] = {p: 0 for p in vote["candidate_paths"]}
    for _, path in vote.get("user_votes", {}).items():
        if path in counts:
            counts[path] += 1

    candidates = [m for m in state["maps"] if m["map_path"] in vote["candidate_paths"]]
    if not candidates:
        try:
            await safe_delete_message(channel, vote.get("intro_message_id"))
        except Exception:
            pass
        state["vote"] = None
        save_json(POOL_STATE_FILE, state)
        return

    max_votes = max(counts.values()) if counts else 0
    if max_votes <= 0:
        # Никто не проголосовал: выбираем одну из карт случайно.
        winner = random.choice(candidates)
        leaders = [winner]
        append_runtime_log(f"vote ended with zero votes; random winner seed={winner.get('seed')}")
    else:
        leaders = [m for m in candidates if counts.get(m["map_path"], 0) == max_votes]
        winner = random.choice(leaders)
    losers = [m for m in candidates if m["map_path"] != winner["map_path"]]

    # Remove the intro/announcement message when voting closes.
    # The winner card remains visible until the next voting starts.
    try:
        await safe_delete_message(channel, vote.get("intro_message_id"))
    except Exception as e:
        append_runtime_log(f"vote intro delete failed | {e}")

    for loser in losers:
        await safe_delete_message(channel, vote["message_ids"].get(loser["map_path"]))
        delete_map_files(loser, reason="vote_loser", allow_ready=True)

    state["maps"] = [m for m in state["maps"] if m["map_path"] not in {x["map_path"] for x in losers}]

    winner_msg_id = vote["message_ids"].get(winner["map_path"])
    try:
        if winner_msg_id:
            msg = await channel.fetch_message(winner_msg_id)
            winner_embed = discord.Embed(title="ПОБЕДИТЕЛЬ ГОЛОСОВАНИЯ", color=discord.Color.green())
            winner_embed.add_field(name="Map Seed", value=str(winner.get("seed") or "—"), inline=False)
            winner_embed.add_field(name="Map Size", value=str(winner.get("size") or "—"), inline=False)
            summary = []
            for idx, c in enumerate(candidates, start=1):
                summary.append(f"Map #{idx}: {counts.get(c['map_path'], 0)} голос(ов)")
            if len(leaders) > 1:
                summary.append("Ничья по голосам — победитель выбран случайно.")
            winner_embed.add_field(name="Итоги", value="\n".join(summary), inline=False)
            if winner.get("map_url"):
                winner_embed.add_field(name="Winning Map URL", value=winner["map_url"], inline=False)

            img = winner.get("icons_path") or winner.get("image_path") or winner.get("thumbnail_path")
            if img and Path(img).exists():
                fname = "winner_map.png"
                file = discord.File(img, filename=fname)
                winner_embed.set_image(url=f"attachment://{fname}")
                await msg.edit(embed=winner_embed, attachments=[file])
            else:
                await msg.edit(embed=winner_embed, attachments=[])

            try:
                await msg.clear_reactions()
            except Exception:
                pass
    except Exception:
        pass

    for m in state["maps"]:
        if m["map_path"] == winner["map_path"]:
            m["status"] = "selected"

    # FIX #3: remember all candidate seeds from this vote so they don't repeat next round
    used_seeds = list(state.get("used_in_vote_seeds") or [])
    for c in candidates:
        seed = c.get("seed")
        if seed is not None and seed not in used_seeds:
            used_seeds.append(seed)
    state["used_in_vote_seeds"] = used_seeds[-20:]  # keep last 20
    state["selected_map_path"] = winner["map_path"]
    state["selected_at"] = datetime.utcnow().isoformat() + "Z"
    state["winner_message_id"] = winner_msg_id
    # Важно: выбранная карта должна ожидать времени вайпа, но это ещё НЕ активная попытка вайпа.
    # Иначе perform_wipe_selected() сам себя блокирует, а cron в момент вайпа видит busy-state.
    state["wipe_attempt_in_progress"] = False
    if state.get("scheduled_wipe_target_at"):
        state["vote_window_consumed_target_at"] = state.get("scheduled_wipe_target_at")
        state["last_vote_target_at"] = state.get("scheduled_wipe_target_at")
    state["vote"] = None
    save_json(POOL_STATE_FILE, state)

    log.info("Vote winner map_path=%s votes=%s leaders=%s", winner["map_path"], counts.get(winner["map_path"], 0), len(leaders))
    append_runtime_log(f"vote winner selected | seed={winner.get('seed')}")
    update_runtime_status(message=f"Winner selected: {winner.get('seed')}", last_action="winner_selected")

    if should_execute_selected_wipe_now(state):
        log.info("winner chosen -> wipe start")
        append_runtime_log("winner chosen -> wipe start")
        await perform_wipe_selected(channel)
    else:
        target = state.get("scheduled_wipe_target_at")
        log.info("winner chosen -> waiting scheduled target %s", target)
        append_runtime_log(f"winner chosen -> waiting scheduled target | target={target}")
        update_runtime_status(message=f"Winner selected, waiting wipe time: {target}", last_action="winner_waiting_target")


def should_execute_selected_wipe_now(state: Optional[dict] = None) -> bool:
    state = state or ensure_state()
    target_dt = _parse_iso_dt(state.get("scheduled_wipe_target_at"))
    if target_dt is None:
        return True
    now_dt = _schedule_now(tzname=getattr(target_dt.tzinfo, "key", None) or str(target_dt.tzinfo))
    try:
        if getattr(target_dt, "tzinfo", None) is None and getattr(now_dt, "tzinfo", None) is not None:
            target_dt = target_dt.replace(tzinfo=now_dt.tzinfo)
        elif getattr(target_dt, "tzinfo", None) is not None and getattr(now_dt, "tzinfo", None) is None:
            now_dt = now_dt.replace(tzinfo=target_dt.tzinfo)
    except Exception:
        pass
    return now_dt >= target_dt


async def perform_wipe_selected(channel: discord.TextChannel):
    state = ensure_state()
    selected_path = state.get("selected_map_path")
    if not selected_path:
        return

    if not should_execute_selected_wipe_now(state):
        append_runtime_log(f"wipe start skipped until scheduled target | target={state.get('scheduled_wipe_target_at')}")
        return

    if state.get("wipe_attempt_in_progress"):
        return

    selected = next((m for m in state["maps"] if m["map_path"] == selected_path), None)
    for m in state.get("maps", []):
        if m.get("map_path") == selected_path:
            m["status"] = "selected"
    if not selected:
        state["selected_map_path"] = None
        state["winner_message_id"] = None
        state["wipe_attempt_in_progress"] = False
        state["wipe_error"] = None
        state["wipe_error_notified"] = False
        save_json(POOL_STATE_FILE, state)
        return

    settings = load_settings()
    p_cfg = settings["pterodactyl"]
    append_runtime_log(f"wipe selected map path: {selected_path}")

    if not selected.get("map_url"):
        log.warning("wipe blocked | selected map has no map_url | seed=%s map_path=%s", selected.get("seed"), selected.get("map_path"))
        state["wipe_error"] = "Selected map has no map_url"
        state["wipe_attempt_in_progress"] = False
        state["selected_map_path"] = None
        if state.get("scheduled_wipe_target_at"):
            state["vote_window_consumed_target_at"] = state.get("scheduled_wipe_target_at")
            state["last_vote_target_at"] = state.get("scheduled_wipe_target_at")
        # remove broken stale map from pool so it cannot be re-voted forever
        state["maps"] = [m for m in state.get("maps", []) if m.get("map_path") != selected_path]
        save_json(POOL_STATE_FILE, state)
        update_runtime_status(message="Выбранная карта без map_url удалена из пула", last_action="wipe_blocked_no_map_url")
        append_runtime_log("wipe blocked: selected map has no map_url; removed from pool")
        return

    if not p_cfg["api_key"] or not p_cfg["server_id"]:
        state["wipe_error"] = "Pterodactyl settings incomplete"
        state["wipe_attempt_in_progress"] = False
        save_json(POOL_STATE_FILE, state)
        update_runtime_status(message="Pterodactyl settings incomplete", last_action="wipe_blocked")
        append_runtime_log("wipe blocked: pterodactyl settings incomplete")
        return

    state["wipe_attempt_in_progress"] = True
    state["wipe_error"] = None
    if state.get("scheduled_wipe_target_at"):
        state["vote_window_consumed_target_at"] = state.get("scheduled_wipe_target_at")
    state.pop("vote_publish_in_progress_for_target", None)
    save_json(POOL_STATE_FILE, state)
    append_runtime_log("wipe_attempt_in_progress=True")

    log.info("wipe start | seed=%s", selected.get('seed'))
    append_runtime_log(f"wipe start | seed={selected.get('seed')}")
    archive_map_files(selected, reason="before_wipe")
    update_runtime_status(message=f"Wipe start: seed {selected.get('seed')}", last_action="wipe_started")

    try:
        api = PterodactylClient(p_cfg)
        log.info("requesting pterodactyl startup config")
        append_runtime_log("requesting pterodactyl startup config")
        startup = api.get_startup()
        append_runtime_log("startup config loaded")

        map_candidates = find_specific_startup_vars(startup, ["MAP URL", "LEVELURL", "CUSTOM MAP URL"], exact=["MAP_URL", "Custom Map URL", "CUSTOM_MAP_URL"])
        remove_candidates = find_specific_startup_vars(startup, ["FILES TO REMOVE", "REMOVE FILES"], exact=["REMOVE_FILES", "Files to remove"])

        append_runtime_log("map url candidates: " + (", ".join(map_candidates) if map_candidates else "none"))
        append_runtime_log("remove files candidates: " + (", ".join(remove_candidates) if remove_candidates else "none"))
        log.info("map url candidates: %s", ", ".join(map_candidates) if map_candidates else "none")
        log.info("remove files candidates: %s", ", ".join(remove_candidates) if remove_candidates else "none")

        updated = False
        update_errors = []

        for name in map_candidates:
            try:
                log.info("trying selected map url update candidate=%s value=%s", name, selected.get("map_url"))
                if selected.get("map_url") and api.try_update_startup_variable(name, selected["map_url"]):
                    updated = True
                    append_runtime_log(f"startup variable updated: {name}")
                    break
            except Exception as e:
                update_errors.append(f"{name}: {e}")

        if not updated:
            append_runtime_log("startup variable update failed for all candidates")
            err = "Could not update startup variable with selected map URL"
            if update_errors:
                err += " | " + " ; ".join(update_errors[-3:])
            state = ensure_state()
            clear_selected_state(state, keep_error=True)
            state["vote_window_consumed_target_at"] = state.get("vote_window_consumed_target_at") or state.get("scheduled_wipe_target_at")
            state["wipe_error"] = err
            state["wipe_error_notified"] = True
            save_json(POOL_STATE_FILE, state)
            update_runtime_status(message=err, last_action="wipe_error")
            append_runtime_log(err)
            return

        wipe_mode = state.get("scheduled_wipe_mode")
        wipe_paths = get_effective_wipe_paths(wipe_mode, settings)
        remove_files_value = " ".join(wipe_paths)
        if remove_files_value and remove_candidates:
            remove_updated = False
            remove_errors = []
            for name in remove_candidates:
                try:
                    if api.try_update_startup_variable(name, remove_files_value):
                        remove_updated = True
                        append_runtime_log(f"files to remove updated: {name}")
                        break
                except Exception as e:
                    remove_errors.append(f"{name}: {e}")
            if not remove_updated:
                append_runtime_log("warning: could not update Files to remove" + ((" | " + " ; ".join(remove_errors[-3:])) if remove_errors else ""))
        elif remove_files_value:
            append_runtime_log("warning: no Files to remove variable found in startup")

        log.info("pterodactyl power stop")
        append_runtime_log("pterodactyl power stop")
        api.power("stop")
        await asyncio.sleep(18)

        # Pterodactyl's startup variable "Files to remove" is usually applied only on reinstall,
        # not on a normal stop/start. Delete the selected wipe files directly through the
        # client Files API so ordinary/BP/full wipes actually remove the old world data.
        if remove_files_value:
            try:
                deleted = api.delete_globs(wipe_paths)
                append_runtime_log(f"pterodactyl direct file delete complete | deleted={deleted}")
            except Exception as e:
                append_runtime_log(f"warning: pterodactyl direct file delete failed | {e}")
                log.warning("pterodactyl direct file delete failed: %s", e)

        log.info("pterodactyl power start")
        append_runtime_log("pterodactyl power start")
        api.power("start")

        append_runtime_log("waiting for server to reach running state before wipe announcement")
        server_running = await api.wait_until_running(timeout_seconds=900, stable_seconds=30)
        if server_running:
            append_runtime_log("server is running; sending wipe announcement")
            wipe_mode_for_notify = state.get("scheduled_wipe_mode")
            send_wipe_webhook(selected, wipe_mode_for_notify)
        else:
            append_runtime_log("wipe announcement skipped: server did not reach running state before timeout")

        # Do NOT delete the winner message after wipe. It stays in Discord
        # until the next voting starts, so the channel remains clean but still
        # shows the currently selected/wiped map.
        append_runtime_log("winner message kept until next vote")
        delete_map_files(selected, reason="wipe_complete", allow_ready=True)
        append_runtime_log("selected map files moved to _deleted_maps; archived copy kept in _wiped_maps_archive")
        state = ensure_state()
        state["maps"] = [m for m in state["maps"] if m["map_path"] != selected_path]
        state["selected_map_path"] = None
        # winner_message_id intentionally remains saved; publish_vote() deletes
        # that old winner card when the next vote starts.
        wipe_mode = state.get("scheduled_wipe_mode") or "ordinary"
        state["last_wipe_at"] = datetime.utcnow().isoformat() + "Z"
        state["last_wipe_mode"] = wipe_mode
        log_wipe_history(wipe_mode, str(selected.get("seed", "")), str(selected.get("size", "")), "Success")
        state["wipe_attempt_in_progress"] = False
        state["wipe_error"] = None
        state["wipe_error_notified"] = False
        state["scheduled_wipe_mode"] = None
        state["scheduled_wipe_requested_at"] = None
        state["scheduled_wipe_target_at"] = None
        # FIX #3: clear used_in_vote_seeds after successful wipe so pool can refill normally
        state["used_in_vote_seeds"] = []
        save_json(POOL_STATE_FILE, state)

        log.info("wipe completed")
        append_runtime_log("wipe completed")
        update_runtime_status(message="Wipe completed", last_action="wipe_completed")
    except Exception as e:
        state = ensure_state()
        clear_selected_state(state, keep_error=True)
        state["wipe_error"] = str(e)
        state["wipe_error_notified"] = True
        save_json(POOL_STATE_FILE, state)
        log.exception("wipe exception")
        append_runtime_log(f"wipe exception: {e}")
        update_runtime_status(message=str(e), last_action="wipe_exception")


intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.reactions = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    global discord_loop
    discord_loop = asyncio.get_running_loop()
    log.info("Discord bot ready as %s", client.user)
    update_runtime_status(discord_ready=True, message=f"Discord bot ready as {client.user}", last_action="discord_ready")
    append_runtime_log(f"Discord bot ready as {client.user}")

    # Delete any vote messages that were left in Discord after a restart.
    # reset_transient_state_on_boot() collects their IDs into orphaned_message_ids.
    try:
        settings = load_settings()
        channel_id_raw = str(settings["discord"]["channel_id"]).strip()
        if channel_id_raw:
            ch = client.get_channel(int(channel_id_raw))
            if ch is None:
                ch = await client.fetch_channel(int(channel_id_raw))
            state = ensure_state()
            orphaned = list(state.get("orphaned_message_ids") or [])
            if orphaned:
                for mid in orphaned:
                    await safe_delete_message(ch, mid)
                state["orphaned_message_ids"] = []
                save_json(POOL_STATE_FILE, state)
                append_runtime_log(f"on_ready: deleted {len(orphaned)} orphaned vote message(s)")
    except Exception as e:
        append_runtime_log(f"on_ready: orphaned message cleanup failed | {e}")

    if not getattr(client, "_worker_started", False):
        client._worker_started = True
        asyncio.create_task(discord_worker_loop())


@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    settings = load_settings()
    emoji = settings["discord"]["reaction_emoji"]
    channel_id = str(settings["discord"]["channel_id"]).strip()
    if not channel_id:
        return
    if payload.channel_id != int(channel_id):
        return
    if str(payload.emoji) != emoji:
        return
    if client.user and payload.user_id == client.user.id:
        return

    state = ensure_state()
    vote = state.get("vote")
    if not vote or not vote.get("active"):
        return

    selected_map_path = None
    for mp, mid in vote.get("message_ids", {}).items():
        if mid == payload.message_id:
            selected_map_path = mp
            break
    if not selected_map_path:
        return

    old_path = vote.get("user_votes", {}).get(str(payload.user_id))
    vote["user_votes"][str(payload.user_id)] = selected_map_path

    channel = client.get_channel(payload.channel_id)
    if channel is None:
        channel = await client.fetch_channel(payload.channel_id)

    if old_path and old_path != selected_map_path:
        old_msg_id = vote["message_ids"].get(old_path)
        if old_msg_id:
            try:
                msg = await channel.fetch_message(old_msg_id)
                user = payload.member or await channel.guild.fetch_member(payload.user_id)
                await msg.remove_reaction(emoji, user)
            except Exception:
                pass

    if vote.get("started_at") is None:
        vote["started_at"] = now_ts()
        append_runtime_log("first vote received; vote remains open until final minute before wipe")
        update_runtime_status(message="Vote received", last_action="vote_received")

    state["vote"] = vote
    save_json(POOL_STATE_FILE, state)


async def update_server_hostname_job(settings: dict, state: dict):
    p_cfg = settings.get("pterodactyl", {})
    if not p_cfg.get("panel_url") or not p_cfg.get("server_id") or not p_cfg.get("api_key"):
        return

    base_name = settings.get("notifications", {}).get("server_name")
    if not base_name or base_name == "YOUR SERVER NAME":
        base_name = "Rust Server"

    from datetime import timezone
    now = datetime.now(timezone.utc)
    
    target_str = state.get("scheduled_wipe_target_at")
    target_dt = None
    if target_str:
        try:
            target_dt = _parse_iso_dt(target_str)
        except Exception:
            pass

    last_wipe_str = state.get("last_wipe_at")
    last_wipe_dt = None
    if last_wipe_str:
        try:
            last_wipe_dt = _parse_iso_dt(last_wipe_str)
        except Exception:
            pass

    show_countdown = False
    time_left_str = ""
    wipe_mode = state.get("scheduled_wipe_mode") or "ordinary"
    
    if target_dt:
        if target_dt.tzinfo is not None:
            now_aware = now.astimezone(target_dt.tzinfo)
        else:
            now_aware = now.replace(tzinfo=None)
            
        diff = target_dt - now_aware
        seconds_left = diff.total_seconds()
        if 0 < seconds_left <= 172800:  # 48 hours (2 days)
            show_countdown = True
            days = int(seconds_left // 86400)
            remaining_after_days = seconds_left % 86400
            hours = int(remaining_after_days // 3600)
            minutes = int((remaining_after_days % 3600) // 60)
            if days > 0:
                time_left_str = f"{days}d {hours}h"
            elif hours > 0:
                time_left_str = f"{hours}h {minutes:02d}m"
            else:
                time_left_str = f"{minutes}m"

    if show_countdown:
        label = "FullWipe" if wipe_mode == "full" else "Wipe"
        new_hostname = f"{base_name} | {label} in {time_left_str}"
    else:
        tzname = schedule_base_timezone(settings)
        try:
            from zoneinfo import ZoneInfo
            display_tz = ZoneInfo(tzname)
        except Exception:
            display_tz = timezone.utc
            
        use_dt = last_wipe_dt.astimezone(display_tz) if last_wipe_dt else now.astimezone(display_tz)
        date_str = use_dt.strftime("%d.%m")
        last_mode = state.get("last_wipe_mode") or "ordinary"

        # "Just" prefix only during the first 24h after wipe
        is_just_wiped = False
        if last_wipe_dt:
            wipe_age_seconds = (now - last_wipe_dt.astimezone(timezone.utc)).total_seconds()
            if 0 <= wipe_age_seconds <= 86400:  # first 24 hours
                is_just_wiped = True

        if last_mode == "full":
            label = "Just FullWiped" if is_just_wiped else "FullWipe"
        else:
            label = "Just Wiped" if is_just_wiped else "Wiped"
        new_hostname = f"{base_name} | {label} {date_str}"

    last_sent_hostname = state.get("last_sent_hostname")
    if last_sent_hostname != new_hostname:
        try:
            api = PterodactylClient(p_cfg)
            api.send_command(f'server.hostname "{new_hostname}"')
            
            try:
                startup = api.get_startup()
                hostname_candidates = find_specific_startup_vars(startup, ["HOSTNAME", "SERVER HOSTNAME", "SERVER NAME"], exact=["HOSTNAME", "server.hostname"])
                hostname_candidates = [n for n in hostname_candidates if " " not in n]
                for name in hostname_candidates:
                    api.try_update_startup_variable(name, new_hostname)
            except Exception as e:
                log.warning("Failed to update HOSTNAME startup variable: %s", e)

            state["last_sent_hostname"] = new_hostname
            save_json(POOL_STATE_FILE, state)
            log.info("Successfully updated server hostname: %s", new_hostname)
        except Exception as e:
            log.warning("Failed to update server hostname: %s", e)


async def send_smm_post_direct(day_name: str, smm_cfg: dict) -> None:
    settings = load_settings()
    bot_token = settings.get("discord", {}).get("token")
    channel_id = smm_cfg.get("channel_id") or settings.get("discord", {}).get("channel_id")
    if not bot_token or not channel_id:
        return

    templates = smm_cfg.get("templates", {}) or {}
    post_desc = templates.get(day_name)
    
    # Replace placeholders dynamically
    if post_desc and "{wipe_timestamp}" in post_desc:
        try:
            state = ensure_state()
            target_dt_str = state.get("scheduled_wipe_target_at")
            if target_dt_str:
                target_dt = _parse_iso_dt(target_dt_str)
                if target_dt:
                    ts = int(target_dt.timestamp())
                    ts_str = f"<t:{ts}:t> (<t:{ts}:R>)"
                    post_desc = post_desc.replace("{wipe_timestamp}", ts_str)
                else:
                    post_desc = post_desc.replace("{wipe_timestamp}", "20:00 (Берлин)")
            else:
                post_desc = post_desc.replace("{wipe_timestamp}", "20:00 (Берлин)")
        except Exception as pe:
            log.warning("SMM placeholder replacement error: %s", pe)
            post_desc = post_desc.replace("{wipe_timestamp}", "20:00 (Берлин)")

    if not post_desc:
        fallbacks = {
            "monday": "Как прошли ваши выходные на сервере? Какие рейды запомнились больше всего?\nДелитесь своими историями и скриншотами лучшего лута в ветке ниже!",
            "tuesday": "Напоминаем про нашу уникальную экономическую систему V-Coins!\nЗарабатывайте монеты за игровое время и PvP в Личном Кабинете на vexonrust.com.",
            "wednesday": "Среда — экватор вайпа! Расскажите, как обстоят дела с вашей базой?\nЕсть ли новые союзники или враги на карте? Пишите в комментариях ниже!",
            "thursday": "Уже завтра выходные и новый промежуточный вайп!\nПора поделиться планами: какую карту вы бы хотели видеть на следующую неделю?",
            "friday": "Запускаем наш еженедельный розыгрыш бонусов в честь выходных!\nНапишите ваш никнейм в ветке обсуждения ниже для участия.",
            "saturday": "Суббота — время для крупномасштабного PvP и рейдов!\nДелитесь скриншотами своих побед и рейдов прямо в этой ветке!",
            "sunday": "Мы стремимся сделать сервер лучше. Если у вас есть предложения по балансу или плагинам, напишите их в ветке ниже!"
        }
        post_desc = fallbacks.get(day_name, "Новый пост!")

    brand_name = settings.get("notifications", {}).get("server_brand") or "RUST SERVER"
    site_url = settings.get("notifications", {}).get("connect_address") or "your-server.com"

    titles = {
        "monday": f"🛒 {brand_name.upper()} — НАШ САЙТ",
        "tuesday": f"📊 {brand_name.upper()} — СТАТИСТИКА ИГРОКОВ",
        "wednesday": f"⚡ {brand_name.upper()} — ОСОБЕННОСТИ",
        "thursday": f"🔄 {brand_name.upper()} — СЕГОДНЯ ВАЙП!",
        "friday": f"💎 {brand_name.upper()} — VIP-ПРИВИЛЕГИИ",
        "saturday": f"⚔️ {brand_name.upper()} — ВРЕМЯ ДЛЯ РЕЙДОВ И БИТВ",
        "sunday": f"🛡️ {brand_name.upper()} — СТАБИЛЬНОСТЬ И ПИНГ"
    }
    thread_names = {
        "monday": "Официальный сайт",
        "tuesday": "Статистика игроков",
        "wednesday": "Особенности серверов",
        "thursday": "Планы на вайп",
        "friday": "VIP привилегии",
        "saturday": "Рейды и PvP",
        "sunday": "Стабильность и пинг"
    }

    title = titles.get(day_name, brand_name.upper())
    thread_name = thread_names.get(day_name, "Обсуждение")

    headers = {
        "Authorization": f"Bot {bot_token}",
        "Content-Type": "application/json"
    }

    embed = {
        "title": title,
        "description": post_desc,
        "color": 13451563,  # CD412B
        "footer": {"text": f"{brand_name} • {site_url}"},
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    payload = {
        "avatar_url": "https://avatars.steamstatic.com/fef49e7fa7e1997310d705b2a6158ff8dc1cdbf5_full.jpg",
        "embeds": [embed]
    }

    if day_name in ["monday", "friday"]:
        payload["content"] = "@everyone"
        payload["allowed_mentions"] = {"parse": ["everyone"]}

    url_msg = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    r = requests.post(url_msg, headers=headers, json=payload, timeout=10)
    if r.status_code == 200:
        msg_id = r.json().get("id")
        url_thread = f"https://discord.com/api/v10/channels/{channel_id}/messages/{msg_id}/threads"
        t_payload = {
            "name": thread_name,
            "auto_archive_duration": 1440
        }
        requests.post(url_thread, headers=headers, json=t_payload, timeout=10)


async def check_and_trigger_smm(channel) -> None:
    settings = load_settings()
    smm_cfg = settings.get("smm", {}) or {}
    if not smm_cfg.get("enabled", False):
        return

    tzname = schedule_base_timezone(settings)
    try:
        import pytz
        tz = pytz.timezone(tzname)
    except Exception:
        tz = timezone.utc

    now = datetime.now(tz)
    date_str = now.strftime("%Y-%m-%d")

    smm_state_file = Path("/home/container/dashboard_data/smm_state.json")
    state = {}
    if smm_state_file.exists():
        try:
            with open(smm_state_file, "r") as sf:
                state = json.load(sf)
        except Exception:
            pass

    if state.get("last_post_date") == date_str:
        return

    post_time_str = smm_cfg.get("post_time", "16:00") or "16:00"
    try:
        hour, minute = map(int, post_time_str.split(":"))
    except Exception:
        hour, minute = 16, 0

    current_time_minutes = now.hour * 60 + now.minute
    target_time_minutes = hour * 60 + minute

    if current_time_minutes >= target_time_minutes:
        weekday = now.weekday()
        days_map = {
            0: "monday",
            1: "tuesday",
            2: "wednesday",
            3: "thursday",
            4: "friday",
            5: "saturday",
            6: "sunday"
        }
        day_name = days_map.get(weekday)
        if day_name:
            await send_smm_post_direct(day_name, smm_cfg)
        state["last_post_date"] = date_str
        try:
            with open(smm_state_file, "w") as sf:
                json.dump(state, sf)
        except Exception as se:
            log.warning("SMM state save error: %s", se)


async def discord_worker_loop():
    await client.wait_until_ready()
    append_runtime_log("discord_worker_loop started")
    update_runtime_status(worker_running=True, message="Discord worker loop started", last_action="worker_start")
    settings = load_settings()
    channel_id = str(settings["discord"]["channel_id"]).strip()
    if not channel_id:
        log.warning("Discord channel_id is empty. Worker idle.")
        return

    channel = client.get_channel(int(channel_id))
    if channel is None:
        channel = await client.fetch_channel(int(channel_id))

    while not client.is_closed():
        try:
            settings_now = load_settings()
            cleanup_days = int(settings_now.get("rustmaps", {}).get("cleanup_deleted_maps_days", 3) or 3)
            cleanup_old_deleted_and_archived_maps(cleanup_days)
            cleanup_stuck_selected_state()
            maybe_arm_vote_window()
            state = reconcile_pool_state()
            slot_mode, slot_target = ensure_scheduled_target(settings_now, state)
            # Force wipe pool pre-cleanup check (48h before the first Thursday of the month)
            if slot_target is not None:
                # Force wipe is Thursday (weekday == 3) and day <= 7
                is_force = (slot_target.weekday() == 3 and slot_target.day <= 7)
                if is_force:
                    tzname = schedule_base_timezone(settings_now)
                    now_slot = _schedule_now(settings_now, tzname=tzname)
                    # Convert slot_target to match timezone of now_slot if necessary
                    try:
                        if getattr(slot_target, "tzinfo", None) is None and getattr(now_slot, "tzinfo", None) is not None:
                            slot_target = slot_target.replace(tzinfo=now_slot.tzinfo)
                        elif getattr(slot_target, "tzinfo", None) is not None and getattr(now_slot, "tzinfo", None) is None:
                            now_slot = now_slot.replace(tzinfo=slot_target.tzinfo)
                    except Exception:
                        pass

                    clear_trigger_time = slot_target - timedelta(hours=48)
                    target_str_dt = slot_target.isoformat()
                    last_cleared_force = state.get("last_cleared_force_wipe")

                    if now_slot >= clear_trigger_time and last_cleared_force != target_str_dt:
                        log.info("Force wipe pool pre-cleanup triggered! Target: %s", target_str_dt)
                        append_runtime_log(f"force wipe pool pre-cleanup triggered | target={target_str_dt}")
                        
                        # Stop active vote if it exists
                        vote = state.get("vote")
                        if vote and isinstance(vote, dict) and vote.get("active"):
                            try:
                                await cancel_active_vote(channel, reason="force_wipe_cleanup", consume_window=False, restore_candidates=False)
                                state = reconcile_pool_state()
                            except Exception as e:
                                log.error(f"Failed to cancel active vote during force cleanup: {e}")


                        # Delete all map files and clear the maps list
                        for map_item in list(state.get("maps", [])):
                            try:
                                state = remove_map_entry_and_files(state, map_item)
                            except Exception as e:
                                log.error("Failed to delete map entry %s: %s", map_item.get("map_path"), e)
                        
                        state["maps"] = []
                        state["selected_map_path"] = None
                        state["winner_message_id"] = None
                        state["last_cleared_force_wipe"] = target_str_dt
                        save_json(POOL_STATE_FILE, state)
                        
                        # Trigger pool fill
                        start_fill_pool()
                        update_runtime_status(message="Force wipe pool pre-cleanup completed", last_action="force_wipe_pool_cleared")
                        state = reconcile_pool_state()
            append_runtime_log(
                f"worker tick | ready={count_ready_maps(state)} vote={bool(state.get('vote'))} selected={bool(state.get('selected_map_path'))} slot_mode={slot_mode} slot_target={(slot_target.isoformat() if slot_target else '-')}"
            )

            if state.get("vote"):
                await process_vote_if_expired(channel)
                state = reconcile_pool_state()

            if state.get("selected_map_path") and not state.get("wipe_error"):
                if should_execute_selected_wipe_now(state):
                    append_runtime_log("selected detected and target reached -> starting wipe")
                    await perform_wipe_selected(channel)
                    state = reconcile_pool_state()
                else:
                    append_runtime_log(f"selected map waiting scheduled wipe target | target={state.get('scheduled_wipe_target_at')}")

            if state.get("vote"):
                await cleanup_missing_vote_messages(channel)
                state = reconcile_pool_state()

            if not state.get("vote") and not state.get("selected_map_path") and not state.get("wipe_attempt_in_progress"):
                current_ready = count_ready_maps(state)
                target = int(settings_now["rustmaps"]["target_pool_size"])
                min_ready = int(settings_now["schedule"].get("publish_when_pool_ready_min", 3) or 3)

                target_dt = _parse_iso_dt(state.get("scheduled_wipe_target_at"))
                if target_dt is not None:
                    now_slot = _schedule_now(tzname=getattr(target_dt.tzinfo, "key", None) or str(target_dt.tzinfo))
                    try:
                        if getattr(target_dt, "tzinfo", None) is None and getattr(now_slot, "tzinfo", None) is not None:
                            target_dt = target_dt.replace(tzinfo=now_slot.tzinfo)
                        elif getattr(target_dt, "tzinfo", None) is not None and getattr(now_slot, "tzinfo", None) is None:
                            now_slot = now_slot.replace(tzinfo=target_dt.tzinfo)
                    except Exception:
                        pass
                    seconds_left = (target_dt - now_slot).total_seconds()
                    before_seconds = int(settings_now["schedule"].get("vote_publish_before_minutes", 5) or 5) * 60
                    append_runtime_log(
                        f"scheduled publish eval | mode={state.get('scheduled_wipe_mode')} seconds_left={int(seconds_left)} before={before_seconds} ready={current_ready}/{target}"
                    )

                    if 0 < seconds_left <= before_seconds:
                        if current_ready >= min_ready:
                            append_runtime_log(f"scheduled wipe publish vote | mode={state.get('scheduled_wipe_mode')} seconds_left={int(seconds_left)}")
                            ok, msg = await publish_vote(channel)
                            if ok:
                                update_runtime_status(message=f"Голосование опубликовано для {state.get('scheduled_wipe_mode')} wipe", last_action="scheduled_vote_published")
                            else:
                                append_runtime_log(f"scheduled publish skipped | {msg}")
                        else:
                            if not (_pool_thread and _pool_thread.is_alive()) and current_ready < target:
                                append_runtime_log(f"scheduled wipe fill pool | ready={current_ready}/{target}")
                                start_fill_pool()
                                update_runtime_status(message="Добивка пула для scheduled wipe", last_action="scheduled_fill_pool")
                    else:
                        if current_ready < target and not (_pool_thread and _pool_thread.is_alive()):
                            start_fill_pool()
                else:
                    if current_ready < target and not (_pool_thread and _pool_thread.is_alive()):
                        start_fill_pool()

            state = reconcile_pool_state()
            if state.get("scheduled_wipe_mode") and state.get("selected_map_path") and not state.get("wipe_error"):
                append_runtime_log(f"scheduled wipe ready to execute | mode={state.get('scheduled_wipe_mode')}")

            target_dt = _parse_iso_dt(state.get("scheduled_wipe_target_at"))
            if state.get("scheduled_wipe_mode") and target_dt and state.get("wipe_error") and state.get("selected_map_path") is None:
                append_runtime_log("scheduled wipe aborted due error")

            # Dynamic server hostname update based on wipe schedule
            try:
                await update_server_hostname_job(settings_now, state)
            except Exception as he:
                log.warning("Hostname update job error: %s", he)

            try:
                await check_and_trigger_smm(channel)
            except Exception as smme:
                log.warning("SMM check error: %s", smme)

        except Exception as e:
            log.exception("Discord worker error: %s", e)
            append_runtime_log(f"worker error: {e}")
            update_runtime_status(message="Worker error", last_action="worker_error")

        await asyncio.sleep(5)





def _cron_matches_now(expr: str, timezone_name: str) -> bool:
    expr = (expr or "").strip()
    if not expr:
        return False
    try:
        trigger = CronTrigger.from_crontab(expr, timezone=timezone_name)
        now = datetime.now(trigger.timezone)
        prev = trigger.get_prev_fire_time(None, now)
        if prev is None:
            return False
        return abs((now - prev).total_seconds()) < 60
    except Exception:
        return False


def _should_skip_ordinary_due_to_full() -> bool:
    settings = load_settings()
    sched_cfg = settings.get("schedule", {})
    timezone_name = schedule_base_timezone(settings)
    try:
        now = _schedule_now(settings, timezone_name)
        full_now = _normal_next_fire(sched_cfg, "full", timezone_name, now - timedelta(seconds=30))
        return bool(full_now and abs((full_now - now).total_seconds()) < 60)
    except Exception:
        return False

def mark_scheduled_wipe(mode: str) -> None:
    state = ensure_state()
    state["scheduled_wipe_mode"] = mode
    state["scheduled_wipe_requested_at"] = datetime.utcnow().isoformat() + "Z"
    save_json(POOL_STATE_FILE, state)

def clear_scheduled_wipe() -> None:
    clear_scheduled_wipe_full()

def send_server_console_command(command: str) -> bool:
    """Send a console command to the Rust server through Pterodactyl Client API."""
    command = str(command or "").strip()
    if not command:
        return False
    try:
        settings = load_settings()
        ptero_cfg = settings.get("pterodactyl", {}) or {}
        if not ptero_cfg.get("panel_url") or not ptero_cfg.get("server_id") or not ptero_cfg.get("api_key"):
            append_runtime_log(f"console command skipped | pterodactyl not configured | {command}")
            return False
        PterodactylClient(ptero_cfg).send_command(command)
        append_runtime_log(f"console command sent | {command}")
        return True
    except Exception as e:
        append_runtime_log(f"console command failed | {command} | {e}")
        return False


def _wipe_announce_job(command: str) -> None:
    send_server_console_command(command)


def schedule_wipe_announcements(settings: Optional[dict] = None) -> None:
    """Schedule server chat warnings before the next wipe using `say`."""
    global scheduler
    if scheduler is None:
        return

    settings = settings or load_settings()
    mode, target_at, _ = compute_next_wipe_target(settings)
    if not mode or not target_at:
        append_runtime_log("wipe announcements skipped | no target")
        return

    try:
        tzname = schedule_base_timezone(settings)
        now = _schedule_now(settings, tzname)
        if getattr(target_at, "tzinfo", None) is not None and getattr(now, "tzinfo", None) is not None:
            now = now.astimezone(target_at.tzinfo)
        elif getattr(target_at, "tzinfo", None) is None and getattr(now, "tzinfo", None) is not None:
            target_at = target_at.replace(tzinfo=now.tzinfo)
    except Exception:
        now = datetime.utcnow()

    label = "FullWipe" if str(mode).lower() == "full" else "Wipe"
    schedule_key = target_at.isoformat().replace(":", "").replace("+", "p").replace("-", "m")
    planned = 0
    for minutes_before in (60, 30, 15, 5, 1):
        run_at = target_at - timedelta(minutes=minutes_before)
        try:
            if run_at <= now:
                continue
        except Exception:
            pass
        command = f"say {label} in {minutes_before} minutes"
        job_id = f"wipe_announce_{schedule_key}_{minutes_before}"[:180]
        try:
            scheduler.add_job(
                _wipe_announce_job,
                trigger="date",
                run_date=run_at,
                args=[command],
                id=job_id,
                replace_existing=True,
                misfire_grace_time=120,
            )
            planned += 1
        except Exception as e:
            append_runtime_log(f"wipe announcement schedule failed | {minutes_before}m | {e}")

    append_runtime_log(f"wipe announcements scheduled | mode={mode} target={target_at.isoformat()} jobs={planned}")


def run_scheduled_wipe(mode: str):
    mode = (mode or "ordinary").strip().lower()
    state = reconcile_pool_state()

    # Если победитель уже выбран и ожидает точного времени вайпа — не блокируем cron.
    # Сам вайп запустит discord_worker_loop на ближайшем тике через perform_wipe_selected().
    if state.get("selected_map_path") and not state.get("wipe_attempt_in_progress") and not state.get("wipe_error"):
        state["scheduled_wipe_mode"] = mode
        state["scheduled_wipe_requested_at"] = datetime.utcnow().isoformat() + "Z"
        # Cron уже наступил. Не сбрасываем selected карту и не переносим цель на завтра.
        if not state.get("scheduled_wipe_target_at"):
            state["scheduled_wipe_target_at"] = _schedule_now(tzname=schedule_base_timezone()).isoformat()
        save_json(POOL_STATE_FILE, state)
        append_runtime_log(f"scheduled wipe due | selected map ready | mode={mode}")
        update_runtime_status(message=f"Время вайпа наступило: выбранная карта готова", last_action="scheduled_wipe_due_selected")
        return

    if state.get("vote") or state.get("wipe_attempt_in_progress") or state.get("vote_publish_in_progress_for_target"):
        append_runtime_log("scheduled wipe skipped | active vote/wipe/publish already in progress")
        update_runtime_status(message="Пропуск scheduled wipe: уже есть активный vote/wipe", last_action="scheduled_wipe_skip_busy")
        return

    if mode == "ordinary" and _should_skip_ordinary_due_to_full():
        append_runtime_log("scheduled wipe skipped | ordinary suppressed because full wipe has priority")
        update_runtime_status(message="Обычный вайп пропущен: приоритет у полного", last_action="scheduled_wipe_skip")
        return

    mark_scheduled_wipe(mode)
    append_runtime_log(f"scheduled wipe armed | mode={mode}")
    update_runtime_status(message=f"Запланирован {mode} wipe", last_action="scheduled_wipe_armed")

def rebuild_scheduler():
    """Worker-цикл сам контролирует расписание, включая anchored */N от даты старта."""
    global scheduler
    settings = load_settings()
    sched_cfg = settings.get("schedule", {})
    timezone = schedule_base_timezone(settings)
    if scheduler is None:
        scheduler = BackgroundScheduler(timezone=timezone)
        scheduler.start(paused=False)
    else:
        try:
            scheduler.remove_all_jobs()
        except Exception:
            pass
        try:
            scheduler.configure(timezone=timezone)
        except Exception:
            pass
    schedule_wipe_announcements(settings)
    
    # Add A2S player tracking job (every 10 minutes)
    try:
        scheduler.add_job(
            track_player_stats,
            'interval',
            minutes=10,
            id='player_stats_tracker',
            replace_existing=True,
            misfire_grace_time=120
        )
    except Exception as e:
        log.warning("Failed to schedule player stats tracking: %s", e)
        
    append_runtime_log("scheduler updated: dashboard worker controls wipe schedule + wipe announcements + player tracking")
    update_runtime_status(message="Scheduler updated", last_action="scheduler_updated")



def tz_offset_label_to_iana(label: str) -> str:
    """Convert UI timezone values to a ZoneInfo-compatible name.

    IANA timezone names are case-sensitive, so Europe/Kyiv and Europe/Berlin
    must not be uppercased. UTC offsets are kept only as a legacy fallback;
    region zones are preferred because they handle summer/winter time.
    """
    raw = (label or "UTC").strip()
    if not raw:
        return "UTC"

    aliases = {
        "Europe/Kiev": "Europe/Kyiv",
        "Kiev": "Europe/Kyiv",
        "Kyiv": "Europe/Kyiv",
        "Berlin": "Europe/Berlin",
    }
    if raw in aliases:
        return aliases[raw]

    if "/" in raw:
        return raw

    compact = raw.upper().replace(" ", "")
    if compact == "UTC":
        return "UTC"
    if compact.startswith("UTC+"):
        try:
            n = int(compact[4:])
            return f"Etc/GMT-{n}"
        except Exception:
            return "UTC"
    if compact.startswith("UTC-"):
        try:
            n = int(compact[4:])
            return f"Etc/GMT+{n}"
        except Exception:
            return "UTC"
    return raw


def schedule_base_timezone(settings: Optional[dict] = None) -> str:
    """Timezone in which cron expressions are interpreted.

    The dashboard timezone selector is used for DISPLAY. The wipe schedule itself
    is intentionally anchored to Berlin time, so 11:50 means 11:50 in Germany.
    To change the anchor later, set schedule.base_timezone in settings.json.
    """
    try:
        settings = settings or load_settings()
        raw = (settings.get("schedule", {}) or {}).get("base_timezone") or (settings.get("schedule", {}) or {}).get("timezone") or "Europe/Berlin"
    except Exception:
        raw = "Europe/Berlin"
    return tz_offset_label_to_iana(raw)


def schedule_display_timezone(settings: Optional[dict] = None) -> str:
    """Timezone selected in the UI for displaying the next wipe time."""
    try:
        settings = settings or load_settings()
        raw = (settings.get("schedule", {}) or {}).get("timezone") or schedule_base_timezone(settings)
    except Exception:
        raw = "Europe/Berlin"
    return tz_offset_label_to_iana(raw)


def reset_scheduled_wipe_target(reason: str = "settings_saved") -> None:
    """Drop cached wipe target after schedule/timezone edits."""
    try:
        state = ensure_state()
        state["scheduled_wipe_mode"] = None
        state["scheduled_wipe_requested_at"] = None
        state["scheduled_wipe_target_at"] = None
        state["vote_window_consumed_target_at"] = None
        state["vote_publish_in_progress_for_target"] = None
        state["last_vote_target_at"] = None
        save_json(POOL_STATE_FILE, state)
        append_runtime_log(f"scheduled target reset | reason={reason}")
    except Exception as e:
        append_runtime_log(f"scheduled target reset failed | reason={reason} | {e}")



def compute_month_wipe_schedule(settings: dict, days: int = 31) -> list[dict]:
    """Return upcoming wipe slots for the next month using normal anchored intervals."""
    schedule_cfg = settings.get("schedule", {})
    base_tzname = schedule_base_timezone(settings)
    display_tzname = schedule_display_timezone(settings)
    now = _schedule_now(settings, base_tzname)
    try:
        from zoneinfo import ZoneInfo
        display_tz = ZoneInfo(display_tzname)
    except Exception:
        display_tz = None

    def _to_display_iso(dt):
        if not dt:
            return None
        try:
            if display_tz is not None:
                if getattr(dt, "tzinfo", None) is None:
                    dt = dt.replace(tzinfo=display_tz)
                else:
                    dt = dt.astimezone(display_tz)
        except Exception:
            pass
        return dt.isoformat()

    try:
        days = max(1, min(93, int(days or 31)))
    except Exception:
        days = 31
    end_at = now + timedelta(days=days)
    by_ts = {}

    for mode in ("ordinary", "full"):
        cursor = now
        guard = 0
        while guard < 80:
            guard += 1
            nxt = _normal_next_fire(schedule_cfg, mode, base_tzname, cursor)
            if not nxt or nxt > end_at:
                break
            try:
                ts = round(float(nxt.timestamp()), 3)
            except Exception:
                ts = float(guard)
            existing = by_ts.get(ts)
            if existing is None or mode == "full":
                by_ts[ts] = (mode, nxt)
            cursor = nxt + timedelta(seconds=1)

    out = []
    for _ts, (mode, dt) in sorted(by_ts.items(), key=lambda x: x[0]):
        out.append({
            "mode": mode,
            "label": "Полный вайп" if mode == "full" else "Обычный вайп",
            "at": _to_display_iso(dt),
        })
    return out


def compute_schedule_preview(settings: dict) -> dict:
    schedule_cfg = settings.get("schedule", {})
    display_tz_label = schedule_cfg.get("timezone", "Europe/Berlin")
    display_tzname = schedule_display_timezone(settings)
    cron_tzname = schedule_base_timezone(settings)
    now = _schedule_now(settings, cron_tzname)

    try:
        from zoneinfo import ZoneInfo
        display_tz = ZoneInfo(display_tzname)
    except Exception:
        display_tz = None

    def _schedule_iso(dt):
        if not dt:
            return None
        try:
            if display_tz is not None:
                if getattr(dt, "tzinfo", None) is None:
                    dt = dt.replace(tzinfo=display_tz)
                else:
                    dt = dt.astimezone(display_tz)
        except Exception:
            pass
        return dt.isoformat()

    state = ensure_state()
    active_mode, active_target = ensure_scheduled_target(settings, state)

    def next_fire(mode: str) -> str:
        try:
            nxt = _normal_next_fire(schedule_cfg, mode, cron_tzname, now)
            return _schedule_iso(nxt) if nxt else "—"
        except Exception:
            return "—"

    next_ordinary = next_fire("ordinary")
    next_full = next_fire("full")

    if active_target is not None and active_mode == "ordinary":
        next_ordinary = active_target.isoformat()
    if active_target is not None and active_mode == "full":
        next_full = active_target.isoformat()

    seconds_left = None
    if active_target is not None:
        try:
            seconds_left = int((active_target - now).total_seconds())
        except Exception:
            seconds_left = None

    return {
        "timezone": display_tz_label,
        "schedule_timezone": cron_tzname,
        "next_ordinary": next_ordinary,
        "next_full": next_full,
        "ordinary_expr": f"{schedule_cfg.get('wipe_time', '11:55')} / каждые {schedule_cfg.get('ordinary_interval_days', 3)} дн.",
        "full_expr": f"{schedule_cfg.get('wipe_time', '11:55')} / каждые {schedule_cfg.get('full_interval_days', 6)} дн.",
        "now": now.isoformat(),
        "active_mode": active_mode,
        "active_target": _schedule_iso(active_target) if active_target else None,
        "active_seconds_left": seconds_left,
        "month": compute_month_wipe_schedule(settings, 31),
    }



def _parse_iso_dt(value: Optional[str]):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None




def _schedule_now(settings: Optional[dict] = None, tzname: Optional[str] = None):
    if tzname is None:
        settings = settings or load_settings()
        tzname = schedule_base_timezone(settings)
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo(tzname))
    except Exception:
        from datetime import timezone as _timezone
        return datetime.now(_timezone.utc)


def _parse_anchor_day_cron(expr: str):
    """
    Для выражений вида: minute hour */N * *
    считает не по дням месяца, а каждые N дней от указанной даты старта.
    """
    parts = (expr or "").strip().split()
    if len(parts) != 5:
        return None
    minute, hour, dom, month, dow = parts
    if month != "*" or dow != "*" or not dom.startswith("*/"):
        return None
    try:
        mi = int(minute); hr = int(hour); step = int(dom[2:])
        if not (0 <= mi <= 59 and 0 <= hr <= 23 and step >= 1):
            return None
        return mi, hr, step
    except Exception:
        return None


def _start_date_dt(date_value: str, hour: int, minute: int, tzname: str):
    date_value = (date_value or "").strip()
    if not date_value:
        return None
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(tzname)
    except Exception:
        tz = None
    try:
        d = datetime.fromisoformat(date_value).date()
    except Exception:
        try:
            d = datetime.strptime(date_value, "%d.%m.%Y").date()
        except Exception:
            return None
    dt = datetime(d.year, d.month, d.day, hour, minute, 0)
    return dt.replace(tzinfo=tz) if tz is not None else dt




def _parse_wipe_time(schedule_cfg: dict):
    """Return (hour, minute) from normal schedule settings.

    New UI uses schedule.wipe_time = HH:MM. Legacy cron values are only used
    as fallback for old settings.json files.
    """
    raw = str((schedule_cfg or {}).get("wipe_time") or "").strip()
    if raw:
        try:
            hh, mm = raw.split(":", 1)
            hour, minute = int(hh), int(mm)
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return hour, minute
        except Exception:
            pass
    # fallback: read time from old cron fields
    for key in ("ordinary_wipe_cron", "full_wipe_cron"):
        parsed = _parse_anchor_day_cron(str((schedule_cfg or {}).get(key) or ""))
        if parsed:
            minute, hour, _step = parsed
            return hour, minute
    return 11, 55


def _interval_days_for_mode(schedule_cfg: dict, mode: str) -> int:
    key = "full_interval_days" if mode == "full" else "ordinary_interval_days"
    fallback_key = "full_wipe_cron" if mode == "full" else "ordinary_wipe_cron"
    try:
        n = int((schedule_cfg or {}).get(key) or 0)
        if n >= 1:
            return n
    except Exception:
        pass
    parsed = _parse_anchor_day_cron(str((schedule_cfg or {}).get(fallback_key) or ""))
    if parsed:
        return max(1, int(parsed[2]))
    return 6 if mode == "full" else 3


def _normal_next_fire(schedule_cfg: dict, mode: str, tzname: str, now_dt):
    """Normal wipe schedule: start date + interval days + single HH:MM time.

    This intentionally does NOT use calendar cron semantics. Example:
    ordinary_start=2026-04-27, ordinary_interval_days=3, wipe_time=11:55
    gives 27.04, 30.04, 03.05, 06.05 ... exactly anchored to the start date.
    """
    hour, minute = _parse_wipe_time(schedule_cfg)
    interval = _interval_days_for_mode(schedule_cfg, mode)
    start_dt = _start_date_dt(_mode_start_date(schedule_cfg, mode), hour, minute, tzname)
    if start_dt is None:
        return None
    try:
        if getattr(now_dt, "tzinfo", None) is not None and getattr(start_dt, "tzinfo", None) is None:
            start_dt = start_dt.replace(tzinfo=now_dt.tzinfo)
        elif getattr(now_dt, "tzinfo", None) is None and getattr(start_dt, "tzinfo", None) is not None:
            now_dt = now_dt.replace(tzinfo=start_dt.tzinfo)
    except Exception:
        pass
    if now_dt <= start_dt:
        return start_dt
    delta_days = (now_dt.date() - start_dt.date()).days
    cycles = max(0, delta_days // interval)
    candidate = start_dt + timedelta(days=cycles * interval)
    if candidate <= now_dt:
        candidate = candidate + timedelta(days=interval)
    return candidate

def _anchored_next_fire(expr: str, tzname: str, now_dt, start_date: str = ""):
    parsed = _parse_anchor_day_cron(expr)
    if not parsed:
        return None
    minute, hour, step_days = parsed
    start_dt = _start_date_dt(start_date, hour, minute, tzname)
    if start_dt is None:
        return None
    try:
        if getattr(now_dt, "tzinfo", None) is not None and getattr(start_dt, "tzinfo", None) is None:
            start_dt = start_dt.replace(tzinfo=now_dt.tzinfo)
        elif getattr(now_dt, "tzinfo", None) is None and getattr(start_dt, "tzinfo", None) is not None:
            now_dt = now_dt.replace(tzinfo=start_dt.tzinfo)
    except Exception:
        pass
    if now_dt <= start_dt:
        return start_dt
    delta_days = (now_dt.date() - start_dt.date()).days
    cycles = delta_days // step_days
    candidate = start_dt + timedelta(days=cycles * step_days)
    if candidate <= now_dt:
        candidate = candidate + timedelta(days=step_days)
    return candidate


def _mode_start_date(schedule_cfg: dict, mode: str) -> str:
    return (schedule_cfg.get(f"{mode}_wipe_start_date") or "").strip()

def _cron_next_fire(expr: str, tzname: str, now_dt, start_date: str = ""):
    expr = (expr or "").strip()
    if not expr:
        return None
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(tzname)
    except Exception:
        tz = tzname
    anchored = _anchored_next_fire(expr, tzname, now_dt, start_date)
    if anchored is not None:
        return anchored
    try:
        trigger = CronTrigger.from_crontab(expr, timezone=tz)
        nxt = trigger.get_next_fire_time(None, now_dt)
        if nxt is not None and getattr(nxt, "tzinfo", None) is None:
            try:
                nxt = nxt.replace(tzinfo=tz if not isinstance(tz, str) else None)
            except Exception:
                pass
        return nxt
    except Exception:
        return None



def get_publishable_wipe_slot(settings: dict):
    schedule_cfg = settings.get("schedule", {})
    tzname = schedule_base_timezone(settings)
    before_minutes = int(schedule_cfg.get("vote_publish_before_minutes", 5) or 5)

    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo(tzname))
    except Exception:
        return None, None, None

    candidates = []
    for mode in ["ordinary", "full"]:
        nxt = _normal_next_fire(schedule_cfg, mode, tzname, now)
        if not nxt:
            continue
        try:
            if getattr(nxt, "tzinfo", None) is None and getattr(now, "tzinfo", None) is not None:
                nxt = nxt.replace(tzinfo=now.tzinfo)
            elif getattr(nxt, "tzinfo", None) is not None and getattr(now, "tzinfo", None) is None:
                now = now.replace(tzinfo=nxt.tzinfo)
        except Exception:
            pass
        seconds_left = (nxt - now).total_seconds()
        mins_left = int(seconds_left // 60)
        if 0 < seconds_left <= (before_minutes * 60):
            candidates.append((mode, nxt, mins_left))

    if not candidates:
        return None, None, None
    candidates.sort(key=lambda x: (x[1], 0 if x[0] == "full" else 1))
    mode, target_at, mins_left = candidates[0]
    return mode, target_at, mins_left



def compute_next_wipe_target(settings: dict):
    schedule_cfg = settings.get("schedule", {})
    tzname = schedule_base_timezone(settings)
    now = _schedule_now(settings, tzname)

    candidates = []
    for mode in ["ordinary", "full"]:
        nxt = _normal_next_fire(schedule_cfg, mode, tzname, now)
        if nxt:
            candidates.append((mode, nxt))
    if not candidates:
        return None, None, None
    candidates.sort(key=lambda x: (x[1], 0 if x[0] == "full" else 1))
    mode, target_at = candidates[0]
    try:
        if getattr(target_at, "tzinfo", None) is None and getattr(now, "tzinfo", None) is not None:
            target_at = target_at.replace(tzinfo=now.tzinfo)
        elif getattr(target_at, "tzinfo", None) is not None and getattr(now, "tzinfo", None) is None:
            now = now.replace(tzinfo=target_at.tzinfo)
    except Exception:
        pass
    try:
        if getattr(target_at, "tzinfo", None) is None and getattr(now, "tzinfo", None) is not None:
            target_at = target_at.replace(tzinfo=now.tzinfo)
        elif getattr(target_at, "tzinfo", None) is not None and getattr(now, "tzinfo", None) is None:
            now = now.replace(tzinfo=target_at.tzinfo)
    except Exception:
        pass
    seconds_left = (target_at - now).total_seconds()
    return mode, target_at, seconds_left


def ensure_scheduled_target(settings: dict, state: Optional[dict] = None):
    state = state or ensure_state()
    current_mode = state.get("scheduled_wipe_mode")
    current_target = _parse_iso_dt(state.get("scheduled_wipe_target_at"))

    schedule_cfg = settings.get("schedule", {})
    tzname = schedule_base_timezone(settings)

    desired_mode, desired_target, _ = compute_next_wipe_target(settings)
    if not desired_mode or not desired_target:
        return None, None

    # If timezone/offset changed, stale saved targets must be discarded.
    # Also fix cached ordinary/full mode when both schedules hit the same time:
    # full wipe has priority, so a cached ordinary target at the same timestamp
    # must be replaced by full.
    target_mismatch = False
    mode_mismatch = False
    if current_target is not None:
        try:
            current_as_desired = current_target.astimezone(desired_target.tzinfo)
            delta = abs((current_as_desired - desired_target).total_seconds())
            if delta > 90:
                target_mismatch = True
            elif current_mode and desired_mode and current_mode != desired_mode:
                mode_mismatch = True
        except Exception:
            target_mismatch = True

    # Если карта уже выбрана и ждёт вайпа, не переносим цель на следующий день
    # после наступления cron-времени. Иначе selected_map_path остаётся, но вайп ждёт завтра.
    if current_mode and current_target and (state.get("selected_map_path") or state.get("wipe_attempt_in_progress")):
        return current_mode, current_target

    keep_current = (
        current_mode
        and current_target
        and not target_mismatch
        and not mode_mismatch
        and (
            state.get("vote")
            or (current_target - _schedule_now(settings, tzname)).total_seconds() > -300
        )
    )
    if keep_current:
        return current_mode, current_target

    target_iso = desired_target.isoformat()
    if state.get("scheduled_wipe_target_at") != target_iso or state.get("scheduled_wipe_mode") != desired_mode or target_mismatch or mode_mismatch:
        # Before overwriting the target, preserve deduplication keys that belong
        # to the NEW desired_target so we never re-publish a vote for a window
        # that was already consumed (e.g. vote ran, then >5min passed and the
        # worker ticked again without an active vote or selected map).
        consumed = state.get("vote_window_consumed_target_at")
        last_voted = state.get("last_vote_target_at")
        state["scheduled_wipe_mode"] = desired_mode
        state["scheduled_wipe_target_at"] = target_iso
        state["scheduled_wipe_requested_at"] = None
        # Keep dedup keys intact so publish_vote() skips this window correctly
        if consumed:
            state["vote_window_consumed_target_at"] = consumed
        if last_voted:
            state["last_vote_target_at"] = last_voted
        save_json(POOL_STATE_FILE, state)
        append_runtime_log(f"scheduled target synced | mode={desired_mode} target={target_iso} mismatch_reset={target_mismatch} mode_reset={mode_mismatch}"
                           f" | consumed={consumed or '-'} last_voted={last_voted or '-'}")
    return desired_mode, desired_target


def get_active_wipe_slot(settings: dict, state: Optional[dict] = None):
    schedule_cfg = settings.get("schedule", {})
    tzname = schedule_base_timezone(settings)
    before_minutes = int(schedule_cfg.get("vote_publish_before_minutes", 5) or 5)

    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo(tzname))
    except Exception:
        return None, None, None, None

    state = state or ensure_state()
    current_target = _parse_iso_dt(state.get("scheduled_wipe_target_at"))
    current_mode = state.get("scheduled_wipe_mode")
    if current_target is not None:
        try:
            mins_left = int((current_target - now).total_seconds() // 60)
            window_start = current_target - timedelta(minutes=before_minutes)
            # freeze current slot while vote/selected/wipe active or until short grace after target
            if (
                window_start <= now <= current_target + timedelta(minutes=max(1, before_minutes))
                or state.get("vote")
                or state.get("selected_map_path")
                or state.get("wipe_attempt_in_progress")
            ):
                return current_mode, current_target, now, mins_left
        except Exception:
            pass

    candidates = []
    for mode in ["ordinary", "full"]:
        nxt = _normal_next_fire(schedule_cfg, mode, tzname, now)
        if not nxt:
            continue
        mins_left = int((nxt - now).total_seconds() // 60)
        candidates.append((mode, nxt, mins_left))
    if not candidates:
        return None, None, now, None
    candidates.sort(key=lambda x: (x[1], 0 if x[0] == "full" else 1))
    mode, target_at, mins_left = candidates[0]
    return mode, target_at, now, mins_left


def find_due_vote_window(settings: dict):
    state = ensure_state()
    mode, target_at, now, mins_left = get_active_wipe_slot(settings, state)
    if not mode or not target_at or now is None:
        return None, None

    schedule_cfg = settings.get("schedule", {})
    before_minutes = int(schedule_cfg.get("vote_publish_before_minutes", 5) or 5)
    window_start = target_at - timedelta(minutes=before_minutes)

    append_runtime_log(
        f"vote window check | mode={mode} target={target_at.isoformat()} now={now.isoformat()} mins_left={mins_left}"
    )

    if window_start <= now < target_at:
        return mode, target_at
    return None, None


def maybe_arm_vote_window() -> bool:
    settings = load_settings()
    state = ensure_state()
    mode, target_at = ensure_scheduled_target(settings, state)
    if not mode or not target_at:
        append_runtime_log("vote window check | no target")
        return False

    schedule_cfg = settings.get("schedule", {})
    before_minutes = int(schedule_cfg.get("vote_publish_before_minutes", 5) or 5)
    tzname = schedule_base_timezone(settings)
    now = _schedule_now(settings, tzname)
    seconds_left = (target_at - now).total_seconds()

    append_runtime_log(
        f"vote window check | mode={mode} target={target_at.isoformat()} now={now.isoformat()} seconds_left={int(seconds_left)} before={before_minutes*60}"
    )

    if not (0 < seconds_left <= before_minutes * 60):
        return False

    if state.get("wipe_attempt_in_progress") or state.get("selected_map_path"):
        append_runtime_log("vote window check | blocked by wipe_attempt_in_progress or selected map")
        return False

    target_iso = target_at.isoformat()
    if state.get("scheduled_wipe_requested_at") and state.get("scheduled_wipe_target_at") == target_iso:
        return False
    if state.get("vote_window_consumed_target_at") == target_iso:
        append_runtime_log(f"vote window check | target already consumed {target_iso}")
        return False

    state["scheduled_wipe_mode"] = mode
    state["scheduled_wipe_target_at"] = target_iso
    state["scheduled_wipe_requested_at"] = datetime.utcnow().isoformat() + "Z"
    save_json(POOL_STATE_FILE, state)
    append_runtime_log(f"vote window armed | mode={mode} target={target_iso} seconds_left={int(seconds_left)}")
    update_runtime_status(message=f"Окно голосования открыто для {mode} wipe", last_action="vote_window_armed")
    log.info("Vote window armed | mode=%s target=%s seconds_left=%s", mode, target_iso, int(seconds_left))
    return True


def clear_scheduled_wipe_full() -> None:
    state = ensure_state()
    state["scheduled_wipe_mode"] = None
    state["scheduled_wipe_requested_at"] = None
    state["scheduled_wipe_target_at"] = None
    state["vote_window_consumed_target_at"] = None
    save_json(POOL_STATE_FILE, state)


def build_dashboard_payload() -> dict:
    settings = load_settings()
    state = reconcile_pool_state()
    generation = load_json(GEN_STATUS_FILE, {
        "running": False, "stage": "idle", "message": "Ожидание",
        "current_seed": None, "updated_at": None, "last_output": [], "error": None, "active_generations": 0,
    })
    runtime = load_json(RUNTIME_STATUS_FILE, {
        "discord_ready": False, "worker_running": False, "message": "Ожидание",
        "last_action": None, "updated_at": None, "log": [],
    })

    pool_maps = []
    selected_seed = None
    for item in state.get("maps", []):
        mp = item.get("map_path")
        preview = pick_preview_path(item)
        badges = [item.get("status", "ready")]
        if item.get("status") == "broken":
            badges.append("broken")
        pool_maps.append({
            "seed": item.get("seed"),
            "size": item.get("size"),
            "status": item.get("status", "ready"),
            "badges": badges,
            "created_at": item.get("created_at") or item.get("downloaded_at") or "",
            "map_url": item.get("map_url"),
            "page_url": item.get("page_url"),
            "map_path": mp,
            "download_url": to_media_url(mp) if mp else "",
            "exists": bool(mp and Path(mp).exists()),
            "preview": to_media_url(preview),
        })
        if state.get("selected_map_path") == mp:
            selected_seed = item.get("seed")

    vote_payload = None
    vote = state.get("vote")
    if vote:
        candidate_paths = vote.get("candidate_paths", [])
        vote_maps = []
        max_votes = 0
        for path in candidate_paths:
            m = next((x for x in state.get("maps", []) if x.get("map_path") == path), None)
            if not m:
                continue
            votes = sum(1 for v in vote.get("user_votes", {}).values() if v == path)
            max_votes = max(max_votes, votes)
            vote_maps.append({
                "seed": m.get("seed"),
                "size": m.get("size"),
                "votes": votes,
                "preview": to_media_url(pick_preview_path(m)),
            })
        for vm in vote_maps:
            vm["is_leader"] = vm["votes"] == max_votes and max_votes > 0
        vote_payload = {
            "active": vote.get("active", False),
            "published_at": vote.get("published_at") or vote.get("started_at"),
            "mode": settings.get("schedule", {}).get("vote_close_mode", "after_first_vote"),
            "time_remaining": 0,
            "maps": vote_maps,
        }

    # После окончания голосования победившая карта остаётся в блоке "Текущее голосование"
    # до успешного вайпа. Это даёт визуальное подтверждение, какая карта ожидает запуска.
    if not vote_payload and state.get("selected_map_path"):
        selected_item = next((x for x in state.get("maps", []) if x.get("map_path") == state.get("selected_map_path")), None)
        if selected_item:
            vote_payload = {
                "active": False,
                "finished": True,
                "published_at": state.get("selected_at"),
                "mode": "winner_waiting_wipe",
                "time_remaining": 0,
                "maps": [{
                    "seed": selected_item.get("seed"),
                    "size": selected_item.get("size"),
                    "votes": None,
                    "preview": to_media_url(pick_preview_path(selected_item)),
                    "is_leader": True,
                    "winner": True,
                }],
            }

    health = {
        "backend": "online",
        "discord": "online" if runtime.get("discord_ready") else "warning",
        "pterodactyl": ("warning" if state.get("wipe_error") else ("online" if load_settings()["pterodactyl"].get("panel_url") and load_settings()["pterodactyl"].get("server_id") and load_settings()["pterodactyl"].get("api_key") else "warning")),
        "rustmaps": "online",
        "issues": [],
    }
    if state.get("wipe_error"):
        health["issues"].append({"level": "error", "message": state.get("wipe_error")})
    if count_ready_maps(state) < int(settings["rustmaps"]["target_pool_size"] or 0):
        health["issues"].append({"level": "info", "message": f"Pool below target: {count_ready_maps(state)}/{int(settings['rustmaps']['target_pool_size'] or 0)}"})
    stale = sum(1 for m in state.get("maps", []) if m.get("status") == "in_vote" and not vote)
    if stale:
        health["issues"].append({"level": "warning", "message": f"Stale in_vote maps: {stale}"})

    integrations = {
        "discord": {"status": "online" if runtime.get("discord_ready") else "warning", "lastSync": runtime.get("updated_at") or "—", "detail": runtime.get("message") or ""},
        "rustmaps": {"status": "online", "lastSync": generation.get("updated_at") or "—", "detail": generation.get("message") or "CLI ready"},
        "pterodactyl": {"status": ("warning" if state.get("wipe_error") else ("online" if load_settings()["pterodactyl"].get("panel_url") and load_settings()["pterodactyl"].get("server_id") and load_settings()["pterodactyl"].get("api_key") else "warning")), "lastSync": runtime.get("updated_at") or "—", "detail": state.get("wipe_error") or "Настроено"},
        "scheduler": {"status": "online", "lastSync": runtime.get("updated_at") or "—", "detail": "Cron settings loaded"},
        "filesystem": {"status": "online", "lastSync": runtime.get("updated_at") or "—", "detail": str(settings["rustmaps"]["downloads_dir"])},
    }

    actual_ready = count_ready_maps(state)
    generation["ready"] = actual_ready
    generation["target"] = int(settings["rustmaps"]["target_pool_size"] or 0)
    generation["active_generations"] = active_generation_count()
    if generation.get("running"):
        generation["current_index"] = actual_ready
        generation["target_index"] = generation["target"]
        msg = str(generation.get("message") or "")
        if "готово" in msg:
            generation["message"] = re.sub(r"готово\s+\d+\s*/\s*\d+", f"готово {actual_ready}/{generation['target']}", msg)
    elif actual_ready >= generation["target"]:
        generation["current_index"] = actual_ready
        generation["target_index"] = generation["target"]
        generation["active_generations"] = 0
        generation["message"] = f"Пул готов: {actual_ready}/{generation['target']}"

    direct_mode, direct_target, direct_mins_left = get_publishable_wipe_slot(settings)
    return {
        "settings": settings,
        "ready_maps": actual_ready,
        "target_pool_size": int(settings["rustmaps"]["target_pool_size"] or 0),
        "selected_seed": selected_seed,
        "pool_maps": pool_maps,
        "vote": vote_payload,
        "generation": generation,
        "runtime": runtime,
        "health": health,
        "integrations": integrations,
        "schedule_preview": compute_schedule_preview(settings),
        "scheduled_wipe_mode": state.get("scheduled_wipe_mode"),
        "scheduled_wipe_requested_at": state.get("scheduled_wipe_requested_at"),
        "wipe_error": state.get("wipe_error"),
        "wipe_history": get_wipe_history(),
        "player_stats": load_json(PLAYER_STATS_FILE, {"history": [], "current_players": 0, "max_players": 0}),
    }



def can_publish_vote_now() -> tuple[bool, str]:
    state = reconcile_pool_state()
    if state.get("vote"):
        return False, "Голосование уже активно"
    if state.get("selected_map_path"):
        return False, "Есть выбранная карта, сначала завершите/сбросьте текущий вайп"
    if state.get("wipe_attempt_in_progress"):
        return False, "Вайп уже запущен, повторное голосование запрещено"
    target_iso = state.get("scheduled_wipe_target_at")
    consumed_iso = state.get("vote_window_consumed_target_at")
    last_vote_target_iso = state.get("last_vote_target_at")
    if target_iso and consumed_iso and target_iso == consumed_iso:
        return False, "Для этого окна вайпа голосование уже было завершено или закрыто"
    if target_iso and last_vote_target_iso and target_iso == last_vote_target_iso:
        return False, "Для этого окна вайпа голосование уже публиковалось"
    candidates = votable_ready_maps(state)
    if len(candidates) < 3:
        return False, f"Недостаточно готовых карт для голосования: {len(candidates)}/3"
    return True, f"Готово к публикации: {len(candidates)} карт"


def clear_wipe_error() -> None:
    state = ensure_state()
    state["wipe_error"] = None
    state["wipe_error_notified"] = False
    save_json(POOL_STATE_FILE, state)


def test_pterodactyl_connection() -> tuple[bool, str]:
    cfg = load_settings()["pterodactyl"]
    panel_url = str(cfg.get("panel_url") or "").strip()
    server_id = str(cfg.get("server_id") or "").strip()
    api_key = str(cfg.get("api_key") or "").strip()
    timeout = int(cfg.get("request_timeout") or 30)

    if not panel_url or not server_id or not api_key:
        return False, "Заполните Panel URL, Server ID и API key"

    headers = {"Authorization": f"Bearer {api_key}", "Accept": "Application/vnd.pterodactyl.v1+json"}
    try:
        r = requests.get(f"{panel_url.rstrip('/')}/api/client", headers=headers, timeout=timeout)
        if r.status_code in (401, 403):
            return False, f"Pterodactyl auth error: HTTP {r.status_code}"
        if r.status_code >= 400:
            return False, f"Pterodactyl client API error: HTTP {r.status_code}"

        r2 = requests.get(f"{panel_url.rstrip('/')}/api/client/servers/{server_id}", headers=headers, timeout=timeout)
        if r2.status_code in (401, 403):
            return False, f"Нет доступа к серверу: HTTP {r2.status_code}"
        if r2.status_code == 404:
            return False, "Server ID не найден"
        if r2.status_code >= 400:
            return False, f"Ошибка чтения сервера: HTTP {r2.status_code}"
        return True, "Pterodactyl подключён"
    except Exception as e:
        return False, f"Pterodactyl exception: {e}"


def test_discord_connection_sync() -> tuple[bool, str]:
    settings = load_settings()
    token = str(settings["discord"].get("token") or "").strip()
    channel_id = str(settings["discord"].get("channel_id") or "").strip()
    if not token or not channel_id:
        return False, "Заполните Discord token и Channel ID"
    if not discord_loop:
        return False, "Discord loop ещё не готов"
    try:
        fut = asyncio.run_coroutine_threadsafe(_get_discord_channel(), discord_loop)
        ch = fut.result(timeout=15)
        return True, f"Discord канал найден: {getattr(ch, 'name', channel_id)}"
    except Exception as e:
        return False, f"Discord exception: {e}"


async def _get_discord_channel():
    settings = load_settings()
    channel_id = str(settings["discord"]["channel_id"]).strip()
    if not channel_id:
        raise RuntimeError("Discord channel_id is empty")
    channel = client.get_channel(int(channel_id))
    if channel is None:
        channel = await client.fetch_channel(int(channel_id))
    return channel


async def _send_discord_test_message():
    channel = await _get_discord_channel()
    await channel.send("✅ Тест подключения Rust Autowipe: Discord подключён.")
    return True, f"Тестовое сообщение отправлено в канал {getattr(channel, 'name', 'unknown')}"


def run_discord_coro(coro, timeout=120):
    # Runs a coroutine on the Discord bot loop from Flask/background threads.
    # Close the coroutine if it cannot be scheduled to avoid "coroutine was never awaited" warnings.
    try:
        if not discord_loop or discord_loop.is_closed():
            try:
                coro.close()
            except Exception:
                pass
            raise RuntimeError("Discord loop not ready")
        fut = asyncio.run_coroutine_threadsafe(coro, discord_loop)
        return fut.result(timeout=timeout)
    except Exception:
        try:
            if hasattr(coro, "cr_frame") and coro.cr_frame is not None:
                coro.close()
        except Exception:
            pass
        raise


def cleanup_broken_and_orphan_maps() -> int:
    """Safe cleanup: do not physically delete suspicious maps during diagnostics.

    - status=broken with an existing .map is moved to state status=quarantined.
      Files stay on disk so the map can be inspected/recovered manually.
    - missing files are removed from state only.
    """
    state = ensure_state()
    changed = 0
    kept = []
    for item in state.get("maps", []):
        mp = item.get("map_path")
        if item.get("status") == "broken":
            if mp and Path(mp).exists():
                q = dict(item)
                q["status"] = "quarantined"
                q["quarantined_at"] = datetime.utcnow().isoformat() + "Z"
                kept.append(q)
                changed += 1
                append_runtime_log(f"MAP QUARANTINED | reason=broken_cleanup | seed={item.get('seed')} | path={mp}")
            else:
                append_runtime_log(f"MAP STATE REMOVE | reason=broken_missing_file | seed={item.get('seed')} | path={mp}")
                changed += 1
            continue
        if mp and not Path(mp).exists() and item.get("status") != "selected":
            # State-only cleanup: never invent a file deletion when the file is already missing.
            append_runtime_log(f"MAP STATE REMOVE | reason=missing_file_cleanup | seed={item.get('seed')} | path={mp}")
            changed += 1
            continue
        kept.append(item)
    state["maps"] = kept
    save_json(POOL_STATE_FILE, state)
    return changed







@app.before_request
def require_dashboard_login():
    # Bypass authorization for local/host triggers
    if request.remote_addr in ["127.0.0.1", "152.53.147.213"]:
        return None
    path = request.path or "/"
    if path in AUTH_PUBLIC_PATHS or path.startswith("/static/") or path.startswith("/public/"):
        return None

    if not is_logged_in():
        session.clear()
        if path.startswith("/api/"):
            return jsonify({"ok": False, "message": "Login required"}), 401
        return redirect("/login")

    now = time.time()
    last_active = float(session.get(AUTH_LAST_ACTIVE_KEY) or 0)
    if last_active and now - last_active > AUTH_IDLE_SECONDS:
        user = session.get(AUTH_SESSION_KEY)
        session.clear()
        try:
            append_runtime_log(f"dashboard auto logout | user={user} | idle>{AUTH_IDLE_SECONDS}s")
        except Exception:
            pass
        if path.startswith("/api/"):
            return jsonify({"ok": False, "message": "Session expired"}), 401
        return redirect("/login?message=Сессия истекла: 60 секунд бездействия.")

    session[AUTH_LAST_ACTIVE_KEY] = now
    session.permanent = False
    return None

@app.route("/login", methods=["GET", "POST"])
def login_route():
    if request.method == "GET":
        return render_frontend("login", "login_url", LOGIN_HTML, error=None, message=request.args.get("message"), username="")
    username = normalize_login(request.form.get("username", ""))
    password_raw = request.form.get("password", "")
    password_trim = password_raw.strip()
    auth = load_auth_state()
    if not username or not password_trim:
        return render_frontend("login", "login_url", LOGIN_HTML, error="Введите логин и пароль.", message=None, username=username), 400

    user_record = auth.get("users", {}).get(username)
    if user_record and (verify_password(password_raw, user_record.get("password", {})) or verify_password(password_trim, user_record.get("password", {}))):
        session.clear()
        session[AUTH_SESSION_KEY] = username
        session[AUTH_LAST_ACTIVE_KEY] = time.time()
        session.permanent = False
        append_runtime_log(f"dashboard login | user={username}")
        return redirect("/")

    pending = auth.get("pending", {}).get(username)
    if pending:
        token_plain = str(pending.get("token_plain") or "")
        token_ok = (token_plain and hmac.compare_digest(password_trim, token_plain)) or verify_password(password_trim, pending.get("token_hash", {})) or verify_password(password_raw, pending.get("token_hash", {}))
        if token_ok:
            session.clear()
            session["pending_setup_user"] = username
            session[AUTH_LAST_ACTIVE_KEY] = time.time()
            session.permanent = False
            append_runtime_log(f"dashboard one-time login accepted | user={username}")
            return redirect("/setup-password")

    append_runtime_log(f"dashboard login failed | user={username or '-'}")
    return render_frontend("login", "login_url", LOGIN_HTML, error="Неверный логин или пароль.", message=None, username=username), 401

@app.route("/setup-password", methods=["GET", "POST"])
def setup_password_route():
    username = normalize_login(session.get("pending_setup_user", ""))
    if not username: return redirect("/login")
    auth = load_auth_state()
    if username not in auth.get("pending", {}):
        session.clear(); return redirect("/login")
    if request.method == "GET":
        return render_frontend("setup_password", "setup_url", SETUP_PASSWORD_HTML, username=username, error=None)
    password = request.form.get("password", "")
    password2 = request.form.get("password2", "")
    if len(password) < 6:
        return render_frontend("setup_password", "setup_url", SETUP_PASSWORD_HTML, username=username, error="Пароль должен быть минимум 6 символов."), 400
    if password != password2:
        return render_frontend("setup_password", "setup_url", SETUP_PASSWORD_HTML, username=username, error="Пароли не совпадают."), 400
    auth.setdefault("users", {})[username] = {"password": hash_password(password), "created_at": datetime.utcnow().isoformat() + "Z"}
    auth.setdefault("pending", {}).pop(username, None)
    save_auth_state(auth)
    session.clear()
    session[AUTH_SESSION_KEY] = username
    session[AUTH_LAST_ACTIVE_KEY] = time.time()
    session.permanent = False
    append_runtime_log(f"dashboard password set | user={username}")
    return redirect("/")

@app.route("/logout", methods=["GET", "POST"])
def logout_route():
    session.clear()
    return redirect("/login?message=Вы вышли из dashboard")

@app.route("/", methods=["GET"])
def index():
    return render_frontend("dashboard", "dashboard_url", DASHBOARD_HTML)

@app.route("/start-fill", methods=["POST"])
def start_fill_route():
    started = start_fill_pool()
    msg = "Запустил добивку пула." if started else "Генерация уже идёт."
    return redirect("/?flash=" + msg)

@app.route("/save-settings", methods=["POST"])
def save_settings_route():
    settings = load_settings()
    settings["discord"]["token"] = request.form.get("discord_token", "").strip()
    settings["discord"]["channel_id"] = request.form.get("discord_channel_id", "").strip()
    settings["discord"]["reaction_emoji"] = request.form.get("discord_reaction_emoji", "✅").strip() or "✅"
    settings["rustmaps"]["api_key"] = request.form.get("rustmaps_api_key", "").strip()
    settings["rustmaps"]["binary"] = request.form.get("rustmaps_binary", "").strip() or str(BASE_DIR / 'rustmaps')
    settings["rustmaps"]["saved_config"] = request.form.get("rustmaps_saved_config", "default").strip() or "default"
    settings["rustmaps"]["downloads_dir"] = request.form.get("rustmaps_downloads_dir", "").strip() or str(BASE_DIR / 'rustmaps_vote_pool')
    settings["pterodactyl"]["panel_url"] = request.form.get("pterodactyl_panel_url", "").strip() or "https://panel.example.com"
    settings["pterodactyl"]["server_id"] = request.form.get("pterodactyl_server_id", "").strip()
    settings["pterodactyl"]["api_key"] = request.form.get("pterodactyl_api_key", "").strip()
    settings["pterodactyl"]["request_timeout"] = int(request.form.get("pterodactyl_request_timeout", "60") or 60)
    settings.setdefault("notifications", {})
    settings["notifications"]["enabled"] = parse_bool(request.form.get("notifications_enabled", "false"), False)
    settings["notifications"]["wipe_webhook_url"] = request.form.get("notifications_wipe_webhook_url", "").strip()
    settings["notifications"]["server_name"] = request.form.get("notifications_server_name", "").strip() or "YOUR SERVER NAME"
    settings["notifications"]["server_brand"] = request.form.get("notifications_server_brand", "").strip() or "YOUR BRAND"
    settings["notifications"]["logo_url"] = request.form.get("notifications_logo_url", "").strip()
    settings["notifications"]["connect_address"] = request.form.get("notifications_connect_address", "").strip()
    settings["schedule"]["timezone"] = request.form.get("schedule_timezone", "UTC").strip() or "UTC"
    settings["schedule"]["wipe_time"] = request.form.get("schedule_wipe_time", "11:55").strip() or "11:55"
    settings["schedule"]["ordinary_interval_days"] = int(request.form.get("schedule_ordinary_interval_days", "3") or 3)
    settings["schedule"]["ordinary_wipe_start_date"] = request.form.get("schedule_ordinary_wipe_start_date", "").strip()
    settings["schedule"]["full_interval_days"] = int(request.form.get("schedule_full_interval_days", "6") or 6)
    settings["schedule"]["full_wipe_start_date"] = request.form.get("schedule_full_wipe_start_date", "").strip()
    settings["schedule"]["vote_publish_before_minutes"] = int(request.form.get("schedule_vote_publish_before_minutes", "60") or 60)
    settings["schedule"]["vote_duration_minutes"] = int(request.form.get("schedule_vote_duration_minutes", "60") or 60)
    settings["schedule"]["vote_close_mode"] = "finalize_before_wipe"
    settings["schedule"]["publish_when_pool_ready_min"] = int(request.form.get("schedule_publish_when_pool_ready_min", "3") or 3)
    settings["schedule"]["auto_publish_vote"] = parse_bool(request.form.get("schedule_auto_publish_vote", "true"), True)
    save_settings(settings)
    reset_scheduled_wipe_target("form_settings_saved")
    rebuild_scheduler()
    try:
        restart_discord_background()
    except Exception as e:
        log.exception("Failed to restart Discord bot on settings update: %s", e)
    return redirect("/")



@app.route("/api/settings", methods=["POST"])
def api_settings_save():
    """JSON settings save endpoint used by the dashboard.

    Older UI buttons used /api/settings but the route was missing in some builds,
    so Flask returned an HTML 404 page and frontend tried to parse it as JSON.
    This endpoint always returns JSON.
    """
    try:
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return jsonify({"ok": False, "message": "Invalid JSON payload"}), 400

        settings = load_settings()
        for key in ("discord", "rustmaps", "pterodactyl", "notifications", "commits", "schedule", "wipe_profiles", "smm"):
            if key in payload and isinstance(payload.get(key), dict):
                settings.setdefault(key, {})
                settings[key].update(payload[key])

        # Normalize commit settings.
        commits = settings.setdefault("commits", {})
        commits["enabled"] = bool(commits.get("enabled", True))
        commits["webhook_url"] = str(commits.get("webhook_url") or "").strip()
        commits["author_user_id"] = re.sub(r"\D", "", str(commits.get("author_user_id") or ""))[:32]
        commits["channel_label"] = str(commits.get("channel_label") or "main").strip() or "main"
        commits["color"] = str(commits.get("color") or "#22dd6a").strip() or "#22dd6a"
        commits["ping_target"] = str(commits.get("ping_target") or "").strip()

        # Normalize common numeric fields to avoid broken JSON values from inputs.
        try: settings["rustmaps"]["target_pool_size"] = int(settings.get("rustmaps", {}).get("target_pool_size") or 10)
        except Exception: settings["rustmaps"]["target_pool_size"] = 10
        try: settings["rustmaps"]["cleanup_deleted_maps_days"] = int(settings.get("rustmaps", {}).get("cleanup_deleted_maps_days") or 3)
        except Exception: settings["rustmaps"]["cleanup_deleted_maps_days"] = 3
        try: settings["rustmaps"]["concurrent_generations"] = int(settings.get("rustmaps", {}).get("concurrent_generations") or 3)
        except Exception: settings["rustmaps"]["concurrent_generations"] = 3
        try: settings["rustmaps"]["fill_pool_batch_max"] = int(settings.get("rustmaps", {}).get("fill_pool_batch_max") or 5)
        except Exception: settings["rustmaps"]["fill_pool_batch_max"] = 5
        try: settings["pterodactyl"]["request_timeout"] = int(settings.get("pterodactyl", {}).get("request_timeout") or 60)
        except Exception: settings["pterodactyl"]["request_timeout"] = 60

        sch = settings.setdefault("schedule", {})
        for nkey, default in (
            ("ordinary_interval_days", 3), ("full_interval_days", 6),
            ("vote_publish_before_minutes", 60), ("vote_duration_minutes", 60),
            ("publish_when_pool_ready_min", 3),
        ):
            try: sch[nkey] = int(sch.get(nkey) or default)
            except Exception: sch[nkey] = default
        sch["wipe_time"] = str(sch.get("wipe_time") or "11:55").strip() or "11:55"
        sch["timezone"] = str(sch.get("timezone") or "UTC").strip() or "UTC"

        save_settings(settings)
        try:
            reset_scheduled_wipe_target("api_settings_saved")
            rebuild_scheduler()
            try:
                restart_discord_background()
            except Exception as dbe:
                log.exception("Failed to restart Discord bot on api settings update: %s", dbe)
        except Exception as e:
            append_runtime_log(f"api settings scheduler rebuild warning | {e}")
        return jsonify({"ok": True, "message": "Настройки сохранены", "settings": settings})
    except Exception as e:
        append_runtime_log(f"api settings save exception | {e}")
        return jsonify({"ok": False, "message": str(e)}), 500


@app.errorhandler(Exception)
def json_api_error_handler(error):
    """Return JSON for API exceptions, but do not turn normal 404s into 500s.

    Previous build raised HTTPException again from inside this handler. Flask then
    converted missing routes like /dashboard-logo into 500 errors, and frontend
    received HTML instead of JSON.
    """
    try:
        code = int(getattr(error, "code", 500) or 500)
    except Exception:
        code = 500

    if str(request.path or "").startswith("/api/"):
        try:
            append_runtime_log(f"api exception | path={request.path} | {error}")
        except Exception:
            pass
        return jsonify({"ok": False, "message": str(error)}), code

    if isinstance(error, HTTPException):
        return error

    raise error


def _commit_color_int(value: str) -> int:
    value = str(value or "#22dd6a").strip()
    if value.startswith("#"):
        value = value[1:]
    try:
        return int(value[:6], 16)
    except Exception:
        return 0x22dd6a


def load_commits() -> List[Dict[str, Any]]:
    data = load_json(COMMITS_FILE, [])
    if isinstance(data, list):
        return data[-200:]
    return []


def save_commits(items: List[Dict[str, Any]]) -> None:
    save_json(COMMITS_FILE, list(items or [])[-200:])


def make_commit_item(payload: Dict[str, Any]) -> Dict[str, Any]:
    settings = load_settings()
    cfg = settings.get("commits", {}) or {}
    # UI uses the field "Текст" as the main commit message. The optional
    # textarea "Дополнительно" must not be required, otherwise publishing a
    # normal one-line update fails with "Commit description is required".
    title = str(payload.get("title") or payload.get("text") or "").strip()
    description = str(payload.get("description") or payload.get("extra") or "").strip()
    if not title and description:
        title, description = description, ""
    if not title:
        raise ValueError("Commit text is required")
    ctype = str(payload.get("type") or "update").strip().lower()[:32] or "update"
    author = str(payload.get("author") or "").strip()[:80]
    author_user_id = re.sub(r"\D", "", str(cfg.get("author_user_id") or ""))[:32]
    project = str(payload.get("project") or cfg.get("channel_label") or "main").strip()[:120]
    version = str(payload.get("version") or "").strip()[:32]
    item = {
        "id": uuid.uuid4().hex[:12],
        "title": title[:4000],
        "description": description[:2000],
        "type": ctype,
        "author": author,
        "author_user_id": author_user_id,
        "project": project,
        "version": version,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "sent_to_discord": False,
        "discord_error": ""
    }
    return item


def _discord_avatar_url(user_id: str, avatar_hash: str) -> str:
    if not user_id or not avatar_hash:
        return ""
    ext = "gif" if str(avatar_hash).startswith("a_") else "png"
    return f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.{ext}?size=128"


def resolve_commit_author(item: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, str]:
    """Resolve author name/avatar from Discord user ID using the bot token.

    The webhook itself still provides the message bot name/avatar. This author
    appears inside the compact embed as the person who released the update.
    """
    user_id = re.sub(r"\D", "", str(item.get("author_user_id") or cfg.get("author_user_id") or ""))[:32]
    fallback_name = str(item.get("author") or (f"User {user_id}" if user_id else "Update"))[:80]
    if not user_id:
        return {"name": fallback_name, "icon_url": "", "user_id": ""}

    token = str((load_settings().get("discord", {}) or {}).get("token") or "").strip()
    if not token:
        return {"name": fallback_name, "icon_url": "", "user_id": user_id}

    try:
        r = requests.get(
            f"https://discord.com/api/v10/users/{user_id}",
            headers={"Authorization": f"Bot {token}"},
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            global_name = str(data.get("global_name") or "").strip()
            username = str(data.get("username") or "").strip()
            name = global_name or username or fallback_name
            icon_url = _discord_avatar_url(user_id, str(data.get("avatar") or ""))
            return {"name": name[:80], "icon_url": icon_url, "user_id": user_id}
        append_runtime_log(f"commit author resolve failed | user_id={user_id} | status={r.status_code}")
    except Exception as e:
        append_runtime_log(f"commit author resolve exception | user_id={user_id} | {e}")
    return {"name": fallback_name, "icon_url": "", "user_id": user_id}




def _commit_ping_payload(value: str) -> tuple[str, dict]:
    """Return Discord content + allowed_mentions for visible or spoiler mentions.

    Supports:
    - @everyone / ||@everyone||
    - @here / ||@here||
    - <@&ROLE_ID> / ||<@&ROLE_ID>||
    - raw role ID
    """
    raw = str(value or '').strip()
    if not raw:
        return '', {}

    unwrapped = raw
    spoiler = False
    if raw.startswith('||') and raw.endswith('||') and len(raw) >= 4:
        spoiler = True
        unwrapped = raw[2:-2].strip()

    if unwrapped in ('@everyone', '@here'):
        content = f'||{unwrapped}||' if spoiler else unwrapped
        return content, {'parse': ['everyone']}

    m = re.search(r'<@&(\d+)>', unwrapped)
    if m:
        role_id = m.group(1)
        content = f'||<@&{role_id}>||' if spoiler else f'<@&{role_id}>'
        return content, {'parse': [], 'roles': [role_id]}

    digits = re.sub(r'\D', '', unwrapped)
    if digits:
        content = f'||<@&{digits}>||' if spoiler else f'<@&{digits}>'
        return content, {'parse': [], 'roles': [digits]}

    return '', {}

def send_commit_to_discord(item: Dict[str, Any]) -> Dict[str, Any]:
    cfg = (load_settings().get("commits", {}) or {})
    webhook = str(cfg.get("webhook_url") or "").strip()
    if not webhook:
        return {"ok": False, "message": "Discord webhook URL is empty"}
    if not webhook.startswith("http://") and not webhook.startswith("https://"):
        return {"ok": False, "message": "Discord webhook URL is invalid"}

    title = str(item.get("title") or "").strip()
    desc = str(item.get("description") or "").strip()
    branch = str(item.get("project") or cfg.get("channel_label") or "main").strip()

    text_parts = []
    if title:
        text_parts.append(title)
    if desc and desc != title:
        text_parts.append(desc)
    commit_text = "\n".join(text_parts).strip() or "Обновление опубликовано."

    resolved_author = resolve_commit_author(item, cfg)
    embed = {
        "description": "⠀\n" + commit_text + "\n⠀",
        "color": _commit_color_int(cfg.get("color")),
        "footer": {"text": branch},
    }
    if resolved_author.get("name"):
        embed["author"] = {"name": resolved_author["name"]}
        if resolved_author.get("icon_url"):
            embed["author"]["icon_url"] = resolved_author["icon_url"]

    # Do not override webhook username/avatar here. Discord will use the
    # webhook's own name and avatar configured in the channel settings.
    ping_content, allowed_mentions = _commit_ping_payload(cfg.get("ping_target") or "")
    body = {"embeds": [embed]}
    if ping_content:
        body["content"] = ping_content
        body["allowed_mentions"] = allowed_mentions

    try:
        r = requests.post(webhook + "?wait=true", json=body, timeout=15)
        if 200 <= r.status_code < 300:
            discord_message_id = None
            try:
                discord_message_id = str(r.json().get("id") or "")
            except Exception:
                pass
            return {"ok": True, "message": "Commit отправлен в Discord", "discord_message_id": discord_message_id}
        return {"ok": False, "message": f"Discord error {r.status_code}: {r.text[:300]}"}
    except Exception as e:
        return {"ok": False, "message": str(e)}



@app.route("/api/commits/check-discord", methods=["POST"])
def api_commits_check_discord():
    """Check which commit messages actually exist in Discord channel.
    Uses Discord bot token + channel_id to fetch messages and verify by message id.
    Updates sent_to_discord / discord_deleted status in commits.json.
    """
    try:
        settings = load_settings()
        token = str((settings.get("discord", {}) or {}).get("token") or "").strip()
        channel_id = str((settings.get("discord", {}) or {}).get("channel_id") or "").strip()
        if not token or not channel_id:
            return jsonify({"ok": False, "message": "Discord token или channel_id не настроены"}), 400

        items = load_commits()
        # Collect all message ids we need to verify
        ids_to_check = {
            str(c["discord_message_id"]): c["id"]
            for c in items
            if c.get("discord_message_id") and c.get("sent_to_discord")
        }

        found_ids = set()
        if ids_to_check:
            # Fetch last 100 messages from channel via bot token
            try:
                r = requests.get(
                    f"https://discord.com/api/v10/channels/{channel_id}/messages?limit=100",
                    headers={"Authorization": f"Bot {token}"},
                    timeout=15,
                )
                if r.status_code == 200:
                    for msg in r.json():
                        found_ids.add(str(msg.get("id", "")))
                else:
                    return jsonify({"ok": False, "message": f"Discord API error {r.status_code}: {r.text[:200]}"}), 400
            except Exception as e:
                return jsonify({"ok": False, "message": f"Discord request failed: {e}"}), 500

            # For messages not found in last 100, try fetching directly
            for discord_msg_id in list(ids_to_check.keys()):
                if discord_msg_id not in found_ids:
                    try:
                        r2 = requests.get(
                            f"https://discord.com/api/v10/channels/{channel_id}/messages/{discord_msg_id}",
                            headers={"Authorization": f"Bot {token}"},
                            timeout=10,
                        )
                        if r2.status_code == 200:
                            found_ids.add(discord_msg_id)
                        # 404 = deleted/not found, other = leave as unknown
                    except Exception:
                        pass

        # Update statuses
        changed = 0
        for c in items:
            dmid = str(c.get("discord_message_id") or "")
            if not dmid:
                continue
            if dmid in found_ids:
                if c.get("discord_deleted"):
                    c["discord_deleted"] = False
                    changed += 1
            else:
                if c.get("sent_to_discord") and not c.get("discord_deleted"):
                    c["discord_deleted"] = True
                    changed += 1

        if changed:
            save_commits(items)
            append_runtime_log(f"commit discord check | updated={changed}")

        return jsonify({"ok": True, "message": f"Проверено. Обновлено статусов: {changed}", "commits": list(reversed(items))})
    except Exception as e:
        append_runtime_log(f"commit check-discord exception | {e}")
        return jsonify({"ok": False, "message": str(e)}), 500


@app.route("/api/commit-settings", methods=["POST"])
def api_commit_settings_save():
    """Dedicated JSON endpoint for commit webhook settings.

    This avoids using the big /api/settings save route from the commit panel, so
    even if general settings change, the commit form always receives JSON and
    never an HTML Flask error page.
    """
    try:
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return jsonify({"ok": False, "message": "Invalid JSON payload"}), 400

        settings = load_settings()
        cfg = settings.setdefault("commits", {})
        cfg["enabled"] = True
        cfg["webhook_url"] = str(payload.get("webhook_url") or "").strip()
        cfg["author_user_id"] = re.sub(r"\D", "", str(payload.get("author_user_id") or ""))[:32]
        cfg["channel_label"] = str(payload.get("channel_label") or "main").strip() or "main"
        cfg["color"] = str(payload.get("color") or "#22dd6a").strip() or "#22dd6a"
        cfg["ping_target"] = str(payload.get("ping_target") or "").strip()
        cfg["send_on_create"] = True
        save_settings(settings)
        append_runtime_log("commit settings saved")
        return jsonify({"ok": True, "message": "Commit-настройки сохранены", "settings": settings})
    except Exception as e:
        append_runtime_log(f"commit settings save exception | {e}")
        return jsonify({"ok": False, "message": str(e)}), 500

@app.route("/api/commits", methods=["GET"])
def api_commits_get():
    return jsonify({"ok": True, "commits": list(reversed(load_commits()))})

@app.route("/api/commits", methods=["POST"])
def api_commits_create():
    try:
        payload = request.get_json(silent=True) or {}
        item = make_commit_item(payload)
        items = load_commits()
        send_now = bool(payload.get("send", True))
        if send_now:
            result = send_commit_to_discord(item)
            item["sent_to_discord"] = bool(result.get("ok"))
            item["discord_error"] = "" if result.get("ok") else result.get("message", "")
            if result.get("discord_message_id"):
                item["discord_message_id"] = result["discord_message_id"]
        items.append(item)
        save_commits(items)
        append_runtime_log(f"commit created | type={item.get('type')} | author_id={item.get('author_user_id')} | sent={item.get('sent_to_discord')} | title={item.get('title')}")
        ok = bool(item.get("sent_to_discord") or not send_now)
        msg = "Commit сохранён" + (" и отправлен" if item.get("sent_to_discord") else ("" if not send_now else f": {item.get('discord_error', '')}"))
        return jsonify({"ok": ok, "message": msg, "commit": item})
    except Exception as e:
        append_runtime_log(f"commit api create exception | {e}")
        return jsonify({"ok": False, "message": str(e)}), 500

@app.route("/api/commits/<commit_id>/send", methods=["POST"])
def api_commits_send(commit_id: str):
    try:
        items = load_commits()
        item = next((x for x in items if x.get("id") == commit_id), None)
        if not item:
            return jsonify({"ok": False, "message": "Commit not found"}), 404
        result = send_commit_to_discord(item)
        item["sent_to_discord"] = bool(result.get("ok"))
        item["discord_error"] = "" if result.get("ok") else result.get("message", "")
        if result.get("discord_message_id"):
            item["discord_message_id"] = result["discord_message_id"]
        save_commits(items)
        return jsonify({"ok": bool(result.get("ok")), "message": result.get("message", ""), "commit": item})
    except Exception as e:
        append_runtime_log(f"commit api send exception | {e}")
        return jsonify({"ok": False, "message": str(e)}), 500


def _current_uploaded_logo_path() -> Optional[Path]:
    try:
        if not UPLOADED_LOGO_DIR.exists():
            return None
        candidates = [x for x in UPLOADED_LOGO_DIR.iterdir() if x.is_file() and x.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".gif")]
        if not candidates:
            return None
        return max(candidates, key=lambda x: x.stat().st_mtime)
    except Exception:
        return None

@app.route("/dashboard-logo", methods=["GET"])
def dashboard_logo_route():
    """Serve locally uploaded dashboard logo.

    Returns 204 when no logo exists. This is intentional: frontend will show
    CLICK/NOT FOUND fallback without Flask producing HTML error pages.
    """
    file_path = _current_uploaded_logo_path()
    if not file_path or not file_path.exists():
        return ("", 204)
    return send_file(str(file_path), max_age=3600)

@app.route("/api/upload_logo", methods=["POST"])
def api_upload_logo_route():
    try:
        f = request.files.get("logo")
        if not f or not getattr(f, "filename", ""):
            return jsonify({"ok": False, "message": "Файл логотипа не выбран"}), 400

        filename = str(f.filename or "logo").strip()
        ext = Path(filename).suffix.lower()
        content_type = str(getattr(f, "mimetype", "") or "").lower()
        allowed_ext = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
        allowed_mime = {"image/png", "image/jpeg", "image/webp", "image/gif"}
        if ext not in allowed_ext or content_type not in allowed_mime:
            return jsonify({"ok": False, "message": "Поддерживаются только PNG, JPG, WEBP или GIF"}), 400

        request.content_length and None
        if request.content_length and request.content_length > 2 * 1024 * 1024 + 4096:
            return jsonify({"ok": False, "message": "Логотип слишком большой. Максимум 2 MB"}), 400

        UPLOADED_LOGO_DIR.mkdir(parents=True, exist_ok=True)
        for old in UPLOADED_LOGO_DIR.iterdir():
            if old.is_file():
                try:
                    old.unlink()
                except Exception:
                    pass

        target = UPLOADED_LOGO_DIR / ("logo" + ext)
        f.save(str(target))
        if target.stat().st_size > 2 * 1024 * 1024:
            try:
                target.unlink()
            except Exception:
                pass
            return jsonify({"ok": False, "message": "Логотип слишком большой. Максимум 2 MB"}), 400

        settings = load_settings()
        settings.setdefault("notifications", {})["logo_url"] = "/dashboard-logo"
        save_settings(settings)
        append_runtime_log(f"dashboard logo uploaded | {target.name} | {target.stat().st_size} bytes")
        return jsonify({"ok": True, "message": "Логотип загружен", "logo_url": "/dashboard-logo", "settings": settings})
    except Exception as e:
        append_runtime_log(f"logo upload exception | {e}")
        return jsonify({"ok": False, "message": str(e)}), 500

@app.route("/media", methods=["GET"])
def media():
    raw_path = (request.args.get("path") or "").strip()
    if not raw_path:
        abort(404)
    base_dir = Path(load_settings().get("rustmaps", {}).get("downloads_dir") or (BASE_DIR / "rustmaps_vote_pool")).resolve()
    file_path = Path(raw_path).resolve()
    if not str(file_path).startswith(str(base_dir)):
        abort(403)
    if not file_path.exists() or not file_path.is_file():
        abort(404)
    return send_file(str(file_path))


def maybe_autopublish_vote_from_http():
    """
    Failsafe: when dashboard is open and polling /api/status, force the same
    pre-wipe publish logic from the HTTP side if worker timing drifted.
    """
    try:
        settings = load_settings()
        state = reconcile_pool_state()

        if state.get("vote") or state.get("selected_map_path") or state.get("wipe_attempt_in_progress"):
            return

        mode, target_at = ensure_scheduled_target(settings, state)
        if not mode or not target_at:
            return
        if is_vote_publish_locked_for_target(state, target_at):
            append_runtime_log(f"http publish skipped | target locked {_publish_target_key(target_at)}")
            return

        before_minutes = int(settings.get("schedule", {}).get("vote_publish_before_minutes", 5) or 5)
        min_ready = int(settings.get("schedule", {}).get("publish_when_pool_ready_min", 3) or 3)
        ready = count_ready_maps(state)
        now = _schedule_now(tzname=getattr(target_at.tzinfo, "key", None) or str(target_at.tzinfo))
        try:
            if getattr(target_at, "tzinfo", None) is None and getattr(now, "tzinfo", None) is not None:
                target_at = target_at.replace(tzinfo=now.tzinfo)
            elif getattr(target_at, "tzinfo", None) is not None and getattr(now, "tzinfo", None) is None:
                now = now.replace(tzinfo=target_at.tzinfo)
        except Exception:
            pass
        seconds_left = (target_at - now).total_seconds()

        append_runtime_log(
            f"http publish eval | mode={mode} target={target_at.isoformat()} seconds_left={int(seconds_left)} ready={ready} before={before_minutes*60}"
        )

        if not (0 < seconds_left <= before_minutes * 60):
            return
        if ready < min_ready:
            return

        ok, msg = can_publish_vote_now()
        if not ok:
            append_runtime_log(f"http publish skipped | {msg}")
            return

        if not discord_loop:
            append_runtime_log("http publish skipped | discord loop not ready")
            return

        result = run_discord_coro(_publish_vote_from_dashboard())
        append_runtime_log(f"http publish result | {result}")
    except Exception as e:
        append_runtime_log(f"http publish exception | {e}")


def _human_duration_ru(seconds: int) -> str:
    seconds = max(0, int(seconds or 0))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}д")
    if hours or parts:
        parts.append(f"{hours}ч")
    if minutes or parts:
        parts.append(f"{minutes}м")
    parts.append(f"{secs}с")
    return " ".join(parts)


@app.route("/public/wipe", methods=["GET"])
def public_wipe_info():
    """Public read-only wipe API. No dashboard login is required."""
    try:
        settings = load_settings()
        state = ensure_state()
        schedule_cfg = settings.get("schedule", {}) or {}

        mode, target_at = ensure_scheduled_target(settings, state)
        if not mode or not target_at:
            resp = jsonify({
                "ok": False,
                "status": "no_schedule",
                "message": "No wipe is scheduled",
            })
            resp.headers["Access-Control-Allow-Origin"] = "*"
            return resp, 404

        base_tzname = schedule_base_timezone(settings)
        display_tzname = schedule_display_timezone(settings)
        now_base = _schedule_now(settings, base_tzname)

        try:
            from zoneinfo import ZoneInfo
            display_tz = ZoneInfo(display_tzname)
        except Exception:
            display_tz = None

        target_display = target_at
        now_display = now_base
        try:
            if display_tz is not None:
                target_display = target_at.astimezone(display_tz) if getattr(target_at, "tzinfo", None) else target_at.replace(tzinfo=display_tz)
                now_display = now_base.astimezone(display_tz) if getattr(now_base, "tzinfo", None) else now_base.replace(tzinfo=display_tz)
        except Exception:
            target_display = target_at
            now_display = now_base

        try:
            seconds_left = int((target_at - now_base).total_seconds())
        except Exception:
            seconds_left = 0
        seconds_left = max(0, seconds_left)

        vote = state.get("vote") or None
        selected_map_path = state.get("selected_map_path")

        payload = {
            "ok": True,
            "status": "ok",
            "wipe_type": mode,
            "wipe_label": "Full wipe" if mode == "full" else "Ordinary wipe",
            "wipe_at": target_display.isoformat(),
            "wipe_at_base": target_at.isoformat(),
            "wipe_timestamp": int(target_at.timestamp()),
            "seconds_left": seconds_left,
            "minutes_left": seconds_left // 60,
            "time_left": _human_duration_ru(seconds_left),
            "timezone": display_tzname,
            "schedule_timezone": base_tzname,
            "server_now": now_display.isoformat(),
            "server_now_base": now_base.isoformat(),
            "vote_active": bool(vote and vote.get("active")),
            "selected_map_ready": bool(selected_map_path),
            "last_wipe_at": state.get("last_wipe_at"),
            "wipe_time": schedule_cfg.get("wipe_time") or "11:55",
            "ordinary_interval_days": schedule_cfg.get("ordinary_interval_days") or 3,
            "full_interval_days": schedule_cfg.get("full_interval_days") or 6,
        }

        resp = jsonify(payload)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Cache-Control"] = "no-store"
        return resp
    except Exception as e:
        resp = jsonify({"ok": False, "status": "error", "message": str(e)})
        resp.headers["Access-Control-Allow-Origin"] = "*"
        return resp, 500


@app.route("/public/status", methods=["GET"])
def public_status_info():
    """Small public status endpoint for website widgets."""
    try:
        settings = load_settings()
        state = ensure_state()
        gen = load_json(GEN_STATUS_FILE, {})
        runtime = load_json(RUNTIME_STATUS_FILE, {})
        ready_count = count_ready_maps(reconcile_pool_state())
        mode, target_at = ensure_scheduled_target(settings, state)
        now_base = _schedule_now(settings, schedule_base_timezone(settings))
        seconds_left = int((target_at - now_base).total_seconds()) if target_at else None
        payload = {
            "ok": True,
            "discord_ready": bool(runtime.get("discord_ready")),
            "worker_running": bool(runtime.get("worker_running")),
            "generation_running": bool(gen.get("running")),
            "ready_maps": ready_count,
            "vote_active": bool((state.get("vote") or {}).get("active")),
            "selected_map_ready": bool(state.get("selected_map_path")),
            "next_wipe_type": mode,
            "next_wipe_at": target_at.isoformat() if target_at else None,
            "seconds_left": max(0, seconds_left) if seconds_left is not None else None,
        }
        resp = jsonify(payload)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Cache-Control"] = "no-store"
        return resp
    except Exception as e:
        resp = jsonify({"ok": False, "status": "error", "message": str(e)})
        resp.headers["Access-Control-Allow-Origin"] = "*"
        return resp, 500


@app.route("/api/status", methods=["GET"])
def api_status():
    maybe_autopublish_vote_from_http()
    return jsonify(build_dashboard_payload())

@app.route("/api/fill-pool", methods=["POST"])

@app.route("/api/deleted_maps", methods=["GET"])
def api_deleted_maps():
    """Small recovery helper: lists soft-deleted files/folders."""
    out = []
    try:
        if DELETED_MAPS_DIR.exists():
            for folder in sorted(DELETED_MAPS_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:50]:
                if not folder.is_dir():
                    continue
                maps = [str(x) for x in folder.rglob("*.map")]
                out.append({
                    "folder": str(folder),
                    "created_at": folder.stat().st_mtime,
                    "map_count": len(maps),
                    "maps": maps[:5],
                })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "items": out}), 500
    return jsonify({"ok": True, "items": out})

def api_fill_pool():
    started = start_fill_pool()
    return jsonify({"ok": started, "message": "Запустил добивку пула." if started else "Генерация уже идёт."})

@app.route("/api/action", methods=["POST"])
def api_action():
    payload = request.get_json(silent=True) or {}
    action = str(payload.get("action") or "").strip()
    try:
        if action == "fill_pool":
            started = start_fill_pool()
            return jsonify({"ok": True, "message": "Pool fill started" if started else "Pool fill already running"})
        if action == "generate_batch":
            count = int(payload.get("count") or 1)
            started = start_manual_generation(count)
            return jsonify({"ok": True, "message": (f"Manual generation started/queued: {max(1, min(7, count))}" if started else "Generation already running")})
        if action == "cleanup_stale":
            if active_generation_count() > 0:
                return jsonify({"ok": False, "message": "Cleanup blocked: generation/RustMaps jobs are active. Wait until generation finishes."})
            removed = cleanup_orphaned_in_vote_maps() + cleanup_broken_and_orphan_maps()
            return jsonify({"ok": True, "message": f"Cleaned stale maps/state: {removed}"})
        if action == "delete_map":
            map_path = payload.get("map_path")
            state = ensure_state()
            if state.get("selected_map_path") == map_path or state.get("wipe_attempt_in_progress"):
                return jsonify({"ok": False, "message": "Cannot delete selected map while a wipe is selected/in progress."}), 409
            vote_paths = set((state.get("vote") or {}).get("candidate_paths") or [])
            if map_path in vote_paths:
                return jsonify({"ok": False, "message": "Cannot delete a map that is currently in an active vote. Close the vote first."}), 409
            removed = 0
            kept = []
            for item in state.get("maps", []):
                if item.get("map_path") == map_path:
                    delete_map_files(item, reason="manual_delete", allow_ready=True); removed += 1
                else:
                    kept.append(item)
            state["maps"] = kept
            save_json(POOL_STATE_FILE, state)
            state = reconcile_pool_state()
            target_now = int(load_settings()["rustmaps"].get("target_pool_size", 10) or 10)
            update_gen_status(current_index=count_ready_maps(state), target_index=target_now, active_generations=active_generation_count())
            return jsonify({"ok": True, "message": f"Deleted maps: {removed} (moved to _deleted_maps)"})
        if action == "clear_pool":
            bump_generation_epoch("clear_pool")
            state = ensure_state()
            removed = 0
            # FIX #2: delete ALL maps (including in_vote/selected), reset vote/selected state
            for item in state.get("maps", []):
                delete_map_files(item, reason="clear_pool", allow_ready=True)
                removed += 1
            state["maps"] = []
            state["vote"] = None
            state["selected_map_path"] = None
            state["selected_at"] = None
            state["winner_message_id"] = None
            state["wipe_attempt_in_progress"] = False
            state["queued_extra_generations"] = 0
            save_json(POOL_STATE_FILE, state)
            state = reconcile_pool_state()
            target_now = int(load_settings()["rustmaps"].get("target_pool_size", 10) or 10)
            update_gen_status(running=False, stage="pool_cleared", message=f"Пул очищен вручную | готово {count_ready_maps(state)}/{target_now}", current_index=count_ready_maps(state), target_index=target_now, active_generations=0)
            append_runtime_log(f"pool cleared manually | removed={removed} | ready={count_ready_maps(state)}/{target_now} | remote_inflight={remote_inflight_count(state)}")
            return jsonify({"ok": True, "message": f"Pool cleared: {removed} (moved to _deleted_maps)"})
        if action == "select_map":
            map_path = str(payload.get("map_path") or "")
            state = reconcile_pool_state()
            item = next((m for m in state.get("maps", []) if m.get("map_path") == map_path and m.get("map_path") and Path(m.get("map_path")).exists()), None)
            if not item:
                return jsonify({"ok": False, "message": "Карта не найдена или файл отсутствует"}), 404
            if not item.get("map_url"):
                return jsonify({"ok": False, "message": "У карты нет map_url, её нельзя поставить на wipe"}), 400
            # Close any local vote state without deleting files/messages. This is manual override.
            state["vote"] = None
            state["selected_map_path"] = map_path
            state["selected_at"] = datetime.utcnow().isoformat() + "Z"
            state["winner_message_id"] = item.get("message_id") or state.get("winner_message_id")
            state["wipe_attempt_in_progress"] = False
            for m in state.get("maps", []):
                if m.get("map_path") == map_path:
                    m["status"] = "selected"
                elif m.get("status") == "selected":
                    m["status"] = "ready"
            save_json(POOL_STATE_FILE, state)
            append_runtime_log(f"manual map selected | seed={item.get('seed')} | path={map_path}")
            return jsonify({"ok": True, "message": f"Карта выбрана для вайпа: seed {item.get('seed')}"})
        if action == "wipe_map_now":
            map_path = str(payload.get("map_path") or "")
            state = reconcile_pool_state()
            item = next((m for m in state.get("maps", []) if m.get("map_path") == map_path and m.get("map_path") and Path(m.get("map_path")).exists()), None)
            if not item:
                return jsonify({"ok": False, "message": "Карта не найдена или файл отсутствует"}), 404
            if not item.get("map_url"):
                return jsonify({"ok": False, "message": "У карты нет map_url, её нельзя поставить на wipe"}), 400
            state["vote"] = None
            state["selected_map_path"] = map_path
            state["selected_at"] = datetime.utcnow().isoformat() + "Z"
            state["scheduled_wipe_mode"] = str(payload.get("wipe_mode") or state.get("scheduled_wipe_mode") or "ordinary")
            state["scheduled_wipe_target_at"] = None
            state["scheduled_wipe_requested_at"] = datetime.utcnow().isoformat() + "Z"
            state["wipe_attempt_in_progress"] = False
            for m in state.get("maps", []):
                if m.get("map_path") == map_path:
                    m["status"] = "selected"
                elif m.get("status") == "selected":
                    m["status"] = "ready"
            save_json(POOL_STATE_FILE, state)
            append_runtime_log(f"manual wipe now requested | seed={item.get('seed')} | path={map_path}")
            if not discord_loop or discord_loop.is_closed():
                return jsonify({"ok": False, "message": "Discord bot is not connected/ready. Cannot start manual wipe announcement."}), 500
            asyncio.run_coroutine_threadsafe(_wipe_selected_from_dashboard(), discord_loop)
            return jsonify({"ok": True, "message": f"Вайп запущен с картой seed {item.get('seed')}"})
        if action == "smm_post_test":
            day_name = str(payload.get("day") or "monday").strip()
            settings = load_settings()
            smm_cfg = settings.get("smm", {}) or {}
            run_discord_coro(send_smm_post_direct(day_name, smm_cfg))
            return jsonify({"ok": True, "message": f"Тестовый анонс для {day_name} отправлен!"})
        if action == "publish_vote":
            ok, msg = can_publish_vote_now()
            if not ok:
                return jsonify({"ok": False, "message": msg})
            result = run_discord_coro(_publish_vote_from_dashboard())
            if isinstance(result, tuple):
                ok2, msg2 = result
                return jsonify({"ok": ok2, "message": msg2})
            return jsonify({"ok": True, "message": "Vote publish requested"})
        if action == "close_vote":
            run_discord_coro(_close_vote_from_dashboard())
            return jsonify({"ok": True, "message": "Vote close requested"})
        if action == "refresh_status":
            return jsonify({"ok": True, "message": "Status refreshed"})
        if action == "test_integrations":
            d_ok, d_msg = test_discord_connection_sync()
            p_ok, p_msg = test_pterodactyl_connection()
            msg = f"Discord: {d_msg} | Pterodactyl: {p_msg}"
            return jsonify({"ok": d_ok and p_ok, "message": msg})
        if action == "test_discord":
            ok, msg = test_discord_connection_sync()
            if not ok:
                return jsonify({"ok": False, "message": msg})
            try:
                result = run_discord_coro(_send_discord_test_message())
                if isinstance(result, tuple):
                    return jsonify({"ok": result[0], "message": result[1]})
                return jsonify({"ok": True, "message": msg})
            except Exception as e:
                return jsonify({"ok": False, "message": f"Discord test send failed: {e}"})
        if action == "test_pterodactyl":
            ok, msg = test_pterodactyl_connection()
            return jsonify({"ok": ok, "message": msg})
        if action == "test_rustmaps":
            try:
                rust = RustMapsCLI(load_settings()["rustmaps"])
                rust.ensure_installed()
                rust.auth()
                return jsonify({"ok": True, "message": "RustMaps API ключ валиден"})
            except Exception as e:
                return jsonify({"ok": False, "message": f"RustMaps error: {e}"})
        if action == "clear_wipe_error":
            clear_wipe_error()
            return jsonify({"ok": True, "message": "Ошибка Pterodactyl очищена"})
        if action == "force_ordinary_wipe":
            run_scheduled_wipe("ordinary")
            return jsonify({"ok": True, "message": "Обычный вайп поставлен в очередь"})
        if action == "force_full_wipe":
            run_scheduled_wipe("full")
            return jsonify({"ok": True, "message": "Полный вайп поставлен в очередь"})
        if action == "clear_scheduled_wipe":
            clear_scheduled_wipe()
            return jsonify({"ok": True, "message": "Очередь scheduled wipe очищена"})
        return jsonify({"ok": False, "message": f"Unsupported action: {action}"}), 400
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500




async def _publish_vote_from_dashboard():
    # publish_vote() already owns VOTE_PUBLISH_LOCK and target de-duplication.
    # Do not lock here, otherwise manual dashboard publishing deadlocks itself
    # and can return 500 / "coroutine was never awaited" in failure paths.
    channel = await _get_discord_channel()
    return await publish_vote(channel)

async def _close_vote_from_dashboard():
    channel = await _get_discord_channel()
    return await cancel_active_vote(channel, reason="dashboard_close", consume_window=True, restore_candidates=True)

async def _wipe_selected_from_dashboard():
    channel = await _get_discord_channel()
    await perform_wipe_selected(channel)
    return True

def start_discord_background():
    settings = load_settings()
    token = settings["discord"]["token"].strip()
    channel_id = settings["discord"]["channel_id"].strip()
    if not token or not channel_id:
        log.warning("Discord token/channel_id missing; discord worker not started.")
        return

    def runner():
        intents = discord.Intents.default()
        intents.guilds = True
        intents.messages = True
        intents.reactions = True
        try:
            client.run(token)
        except Exception as e:
            log.exception("Discord client stopped: %s", e)

    t = threading.Thread(target=runner, daemon=True)
    t.start()


def restart_discord_background():
    global client, discord_loop
    if discord_loop and not discord_loop.is_closed() and client:
        try:
            log.info("Stopping old Discord client...")
            future = asyncio.run_coroutine_threadsafe(client.close(), discord_loop)
            try:
                future.result(timeout=5)
            except Exception:
                pass
        except Exception as e:
            log.warning("Failed to close old Discord client: %s", e)

    discord_loop = None

    intents = discord.Intents.default()
    intents.guilds = True
    intents.messages = True
    intents.reactions = True
    client = discord.Client(intents=intents)

    client.event(on_ready)
    client.event(on_raw_reaction_add)

    start_discord_background()



def reset_transient_state_on_boot() -> None:
    # Safe reset of transient state on boot. Preserves key long-term variables
    # like last_cleared_force_wipe, generation_epoch, queued_extra_generations,
    # last_wipe_at, and hostname caching so they never get lost on restart.
    state = ensure_state()
    active_vote = state.get("vote") or {}
    vote_active = bool(active_vote.get("active"))
    vote_paths = set(active_vote.get("candidate_paths") or [])
    selected_path = state.get("selected_map_path")
    
    preserved_maps = []
    dropped_unwipable = 0
    now_ts = time.time()
    for item in list(state.get("maps", [])):
        m = dict(item)
        mp = m.get("map_path")
        status = str(m.get("status") or "").strip().lower()
        
        # Preserve active statuses
        if vote_active and mp in vote_paths:
            m["status"] = "in_vote"
        elif selected_path and mp == selected_path:
            m["status"] = "selected"
        elif status in {"in_vote", "selected", "preparing"}:
            m["status"] = "ready"
            m["message_id"] = None
            
        created_at = float(m.get("created_at") or 0)
        is_old_enough = (now_ts - created_at) > 120 if created_at else True
        if m.get("status") == "ready" and is_old_enough and (not m.get("map_url")):
            dropped_unwipable += 1
        preserved_maps.append(m)

    # Collect Discord message IDs to delete ONLY if vote is not active
    orphaned_message_ids = list(state.get("orphaned_message_ids", []) or [])
    if not vote_active:
        if active_vote.get("intro_message_id"):
            orphaned_message_ids.append(int(active_vote["intro_message_id"]))
        for mid in (active_vote.get("message_ids") or {}).values():
            try:
                v = int(mid)
                if v not in orphaned_message_ids:
                    orphaned_message_ids.append(v)
            except Exception:
                pass
        state["vote"] = None
        state["selected_map_path"] = None
        state["selected_at"] = None
        state["scheduled_wipe_mode"] = None
        state["scheduled_wipe_requested_at"] = None
        state["scheduled_wipe_target_at"] = None

    state["maps"] = preserved_maps
    state["winner_message_id"] = None
    state["wipe_attempt_in_progress"] = False
    state["wipe_error"] = None
    state["wipe_error_notified"] = False
    state["vote_publish_in_progress_for_target"] = None
    state["orphaned_message_ids"] = orphaned_message_ids

    save_json(POOL_STATE_FILE, state)
    append_runtime_log(
        f"boot cleanup done | preserved_maps={len(preserved_maps)} missing_map_url_kept={dropped_unwipable} | transient_statuses_reset=yes"
    )
    update_runtime_status(
        message="Runtime history cleared after restart; map pool preserved",
        last_action="boot_cleanup",
    )

if __name__ == "__main__":
    if not SETTINGS_FILE.exists():
        save_settings(DEFAULT_SETTINGS)
    reset_transient_state_on_boot()
    if not GEN_STATUS_FILE.exists():
        update_gen_status(running=False, stage="idle", message="Ожидание")
    if not RUNTIME_STATUS_FILE.exists():
        update_runtime_status(discord_ready=False, worker_running=False, message="Ожидание", last_action="init")
    rebuild_scheduler()
    start_admin_console_thread()
    # Start discord background if configured
    start_discord_background()
    port = int(os.getenv("SERVER_PORT", "2973"))
    log.info("Starting dashboard on port %s", port)
    cert_path = Path("/home/container/dashboard_data/cert.pem")
    key_path = Path("/home/container/dashboard_data/key.pem")
    if cert_path.exists() and key_path.exists():
        log.info("Starting Flask with SSL/HTTPS...")
        app.run(host="0.0.0.0", port=port, debug=False, ssl_context=(str(cert_path), str(key_path)))
    else:
        log.info("Starting Flask with HTTP...")
        app.run(host="0.0.0.0", port=port, debug=False)
