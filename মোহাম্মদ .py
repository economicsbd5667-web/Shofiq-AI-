# ============================================================
# SHOFIQ AI - ALL IN ONE PERSONAL AI ASSISTANT
# Version: 6.0
# Python 3 / Pydroid 3
# UI polish only — API, memory, tasks, notes, sales unchanged
# ============================================================

import json
import urllib.request
import urllib.error
import urllib.parse
import re
import socket
import threading
import webbrowser
import base64
import os
import html
import random
import ast
import operator
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from http.server import BaseHTTPRequestHandler, HTTPServer

APP_NAME = "Shofiq AI"
VERSION = "6.0"
HOST = "0.0.0.0"
PORT = 8080
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_FILE = os.path.join(BASE_DIR, "shofiq_memory.json")
TASK_FILE = os.path.join(BASE_DIR, "shofiq_tasks.json")
NOTE_FILE = os.path.join(BASE_DIR, "shofiq_notes.json")
SALES_FILE = os.path.join(BASE_DIR, "shofiq_sales.json")
CONFIG_FILE = os.path.join(BASE_DIR, "shofiq_config.json")
DEFAULT_MODEL = "gemini-3.8-flash"
GEMINI_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite"
]

def load_json(path, default):
    try:
        if not os.path.exists(path):
            return default
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, data):
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
        return True
    except Exception:
        return False

memories = load_json(MEMORY_FILE, [])
tasks = load_json(TASK_FILE, [])
notes = load_json(NOTE_FILE, [])
sales = load_json(SALES_FILE, [])
if not isinstance(memories, list):
    memories = []
if not isinstance(tasks, list):
    tasks = []
if not isinstance(notes, list):
    notes = []
if not isinstance(sales, list):
    sales = []

USER_PROFILE = {
    "name": "Mohammad Shofiq Islam",
    "short_name": "Shofiq",
    "location": "Kishoreganj, Bangladesh",
    "college": "Government Gurudayal College",
    "subject": "Economics Honours",
    "goal": "Software Engineer",
    "wife": "Mahmuda",
    "ai_name": "Shofiq AI"
}

BANGLA_REPLACEMENTS = {
    "তুমার": "তোমার",
    "তুমাদের": "তোমাদের",
    "তুমারটা": "তোমারটা",
    "কেডা": "কে",
    "কিতা": "কি",
    "ক্যান": "কেন",
    "কেমনে": "কীভাবে",
    "কিভাবে": "কীভাবে",
    "কিভাবেঃ": "কীভাবে",
    "বানাইছে": "বানিয়েছে",
    "বানাইছো": "বানিয়েছো",
    "দিসি": "দিয়েছি",
    "দিছি": "দিয়েছি",
    "করতাসে": "করছে",
    "করতেছি": "করছি",
    "করতেছ": "করছ",
    "তুমাকে": "তোমাকে",
    "আমারে": "আমাকে",
    "আমগো": "আমাদের",
    "আমার নাম কি": "আমার নাম কী",
    "তুমার নাম কি": "তোমার নাম কী",
    "থ্যাংকস": "ধন্যবাদ",
    "thanks": "ধন্যবাদ",
    "thank you": "ধন্যবাদ",
    "hello": "হাই",
    "hi": "হাই",
    "hey": "হাই"
}
STOPWORDS = {"ভাই", "তো", "গো", "রে", "আচ্ছা", "একটু", "শোনো", "বলতো", "প্লিজ", "দয়া", "করে", "করেন", "একটা", "একটি"}

def normalize_bangla(text):
    if not text:
        return ""
    text = str(text).strip().lower()
    text = text.replace("য়", "য়").replace("ড়", "ড়").replace("ঢ়", "ঢ়")
    for old, new in BANGLA_REPLACEMENTS.items():
        text = text.replace(old, new)
    text = re.sub(r"[!?.,;:'\"“”‘’`~@#$%^&*()_+=\[\]{}<>/\\|]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return " ".join(w for w in text.split() if w not in STOPWORDS)

def similarity(a, b):
    a = normalize_bangla(a)
    b = normalize_bangla(b)
    if not a or not b:
        return 0
    return SequenceMatcher(None, a, b).ratio()

def token_score(a, b):
    a_words = set(normalize_bangla(a).split())
    b_words = set(normalize_bangla(b).split())
    if not a_words or not b_words:
        return 0
    return len(a_words & b_words) / max(len(a_words), len(b_words))

INTENTS = [
    (["আমার নাম কী", "আমার নাম কি", "তুমি কি আমার নাম জানো", "আমার নাম বলো"],
     "তোমার নাম Mohammad Shofiq Islam। তুমি Shofiq নামে পরিচিত।"),
    (["তোমার নাম কী", "তোমার নাম কি", "তুমার নাম কি", "কে তুমি"],
     "আমার নাম Shofiq AI। আমি Shofিকের তৈরি একটি ব্যক্তিগত বাংলা AI assistant।"),
    (["তুমি কে", "তুমি আসলে কে", "তোমার পরিচয় কী", "তোমার পরিচয় কি"],
     "আমি Shofiq AI। আমি Shofিকের তৈরি একটি personal AI assistant। আমি প্রশ্নের উত্তর দিতে, তথ্য মনে রাখতে, শেখানো তথ্য সংরক্ষণ করতে এবং বিভিন্ন personal task পরিচালনা করতে পারি।"),
    (["তোমাকে কে তৈরি করেছে", "তোমাকে কে বানিয়েছে", "কে তোমাকে বানিয়েছে", "কে তোমাকে তৈরি করেছেন"],
     "আমাকে Mohammad Shofiq Islam, অর্থাৎ Shofiq তৈরি করেছেন।"),
    (["শফিক কে", "মোহাম্মদ শফিক কে", "শফিক সম্পর্কে বলো"],
     "Shofiq Kishoreganj-এর একজন Economics Honours শিক্ষার্থী। তিনি Government Gurudayal College-এ পড়াশোনা করেন এবং ভবিষ্যতে Software Engineer হতে চান।"),
    (["তুমি কী কী করতে পারো", "তোমার কাজ কী", "কি কি করতে পারো", "তোমার capability কি"],
     "আমি প্রশ্নের উত্তর দিতে, Teach AI দিয়ে নতুন তথ্য শিখতে, memory রাখতে, হিসাব করতে, date/time বলতে, task ও reminder রাখতে, notes সংরক্ষণ করতে, business sales হিসাব রাখতে, ছবি বিশ্লেষণ করতে এবং Gemini AI-এর সাহায্যে বিস্তারিত উত্তর দিতে পারি।"),
    (["শুভ সকাল", "সুপ্রভাত", "good morning"], "শুভ সকাল! আজকের দিনটি সুন্দর হোক।"),
    (["শুভ রাত্রি", "শুভ রাত", "good night"], "শুভ রাত্রি। ভালোভাবে বিশ্রাম নাও।"),
    (["হাই", "হ্যালো", "hello", "hi", "hey"], "হাই! আমি Shofiq AI। কীভাবে সাহায্য করতে পারি?"),
    (["ধন্যবাদ", "থ্যাংকস", "thanks", "thank you"], "স্বাগতম।"),
    (["বিদায়", "বাই", "goodbye", "bye"], "আবার কথা হবে।"),
    (["তুমি কি আমাকে সাহায্য করতে পারো", "সাহায্য করতে পারো", "help"], "অবশ্যই। তোমার প্রশ্ন বা কাজটি লিখে দাও।"),
]

SAFE_OPERATORS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Mod: operator.mod, ast.Pow: operator.pow,
    ast.USub: operator.neg, ast.UAdd: operator.pos
}

def safe_eval_math(expression):
    try:
        tree = ast.parse(expression, mode="eval")
        def evaluate(node):
            if isinstance(node, ast.Expression):
                return evaluate(node.body)
            if isinstance(node, ast.Constant):
                if isinstance(node.value, (int, float)):
                    return node.value
                raise ValueError()
            if isinstance(node, ast.UnaryOp):
                op = SAFE_OPERATORS.get(type(node.op))
                if not op:
                    raise ValueError()
                return op(evaluate(node.operand))
            if isinstance(node, ast.BinOp):
                op = SAFE_OPERATORS.get(type(node.op))
                if not op:
                    raise ValueError()
                left = evaluate(node.left)
                right = evaluate(node.right)
                if isinstance(node.op, ast.Pow) and abs(right) > 20:
                    raise ValueError()
                return op(left, right)
            raise ValueError()
        result = evaluate(tree)
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        return result
    except Exception:
        return None

def try_math(text):
    t = normalize_bangla(text)
    candidates = [t, t.replace("কত হয়", "").strip(), t.replace("হিসাব কর", "").strip(),
                  t.replace("যোগ কর", "").strip(), t.replace("calculate", "").strip(), t.replace("solve", "").strip()]
    for c in candidates:
        if re.fullmatch(r"[0-9+\-*/().%\s]+", c):
            result = safe_eval_math(c)
            if result is not None:
                return f"উত্তর: {result}"
    return None

def try_percent(text):
    t = normalize_bangla(text)
    patterns = [
        r"(\d+(?:\.\d+)?)\s*%\s*of\s*(\d+(?:\.\d+)?)",
        r"(\d+(?:\.\d+)?)\s*%\s*(\d+(?:\.\d+)?)",
        r"(\d+(?:\.\d+)?)\s*percent\s*of\s*(\d+(?:\.\d+)?)",
        r"(\d+(?:\.\d+)?)\s*শতাংশ\s*(?:এর|of)?\s*(\d+(?:\.\d+)?)"
    ]
    for pattern in patterns:
        m = re.search(pattern, t)
        if m:
            p = float(m.group(1))
            value = float(m.group(2))
            result = (p / 100) * value
            if result.is_integer():
                result = int(result)
            return f"{p:g}% of {value:g} = {result}"
    return None

def try_convert(text):
    t = normalize_bangla(text)
    m = re.search(r"(\d+(?:\.\d+)?)\s*(km|kilometer|kilometers)\s*(?:to|in|এ)\s*(mile|miles)", t)
    if m:
        value = float(m.group(1)); result = value * 0.621371
        return f"{value:g} km = {result:.4f} miles"
    m = re.search(r"(\d+(?:\.\d+)?)\s*(mile|miles)\s*(?:to|in|এ)\s*(km|kilometer|kilometers)", t)
    if m:
        value = float(m.group(1)); result = value * 1.609344
        return f"{value:g} miles = {result:.4f} km"
    m = re.search(r"(\d+(?:\.\d+)?)\s*(kg|kilogram|kilograms)\s*(?:to|in|এ)\s*(pound|pounds|lb)", t)
    if m:
        value = float(m.group(1)); result = value * 2.2046226218
        return f"{value:g} kg = {result:.4f} pounds"
    m = re.search(r"(\d+(?:\.\d+)?)\s*(pound|pounds|lb)\s*(?:to|in|এ)\s*(kg|kilogram|kilograms)", t)
    if m:
        value = float(m.group(1)); result = value / 2.2046226218
        return f"{value:g} pounds = {result:.4f} kg"
    m = re.search(r"(-?\d+(?:\.\d+)?)\s*(?:c|celsius|°c)\s*(?:to|in|এ)\s*(?:f|fahrenheit|°f)", t)
    if m:
        value = float(m.group(1)); result = (value * 9 / 5) + 32
        return f"{value:g}°C = {result:.2f}°F"
    m = re.search(r"(-?\d+(?:\.\d+)?)\s*(?:f|fahrenheit|°f)\s*(?:to|in|এ)\s*(?:c|celsius|°c)", t)
    if m:
        value = float(m.group(1)); result = (value - 32) * 5 / 9
        return f"{value:g}°F = {result:.2f}°C"
    return None

WEEKDAYS_BN = {"Monday": "সোমবার", "Tuesday": "মঙ্গলবার", "Wednesday": "বুধবার", "Thursday": "বৃহস্পতিবার", "Friday": "শুক্রবার", "Saturday": "শনিবার", "Sunday": "রবিবার"}
MONTHS_BN = {1: "জানুয়ারি", 2: "ফেব্রুয়ারি", 3: "মার্চ", 4: "এপ্রিল", 5: "মে", 6: "জুন", 7: "জুলাই", 8: "আগস্ট", 9: "সেপ্টেম্বর", 10: "অক্টোবর", 11: "নভেম্বর", 12: "ডিসেম্বর"}

def bangla_now():
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    ampm = "PM" if hour >= 12 else "AM"
    display_hour = hour
    if display_hour == 0:
        display_hour = 12
    elif display_hour > 12:
        display_hour -= 12
    return f"এখন সময় {display_hour}:{minute:02d} {ampm}"

def bangla_date():
    now = datetime.now()
    weekday = WEEKDAYS_BN.get(now.strftime("%A"), now.strftime("%A"))
    month = MONTHS_BN.get(now.month, str(now.month))
    return f"আজ {now.day} {month} {now.year}, {weekday}।"

def make_id(prefix="item"):
    return f"{prefix}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

def add_task(title, due=None):
    item = {"id": make_id("task"), "title": title.strip(), "due": due or "", "done": False, "created": datetime.now().isoformat(timespec="seconds")}
    tasks.append(item)
    save_json(TASK_FILE, tasks)
    return item

def complete_task(task_id):
    for task in tasks:
        if task.get("id") == task_id:
            task["done"] = True
            save_json(TASK_FILE, tasks)
            return True
    return False

def delete_task(task_id):
    global tasks
    before = len(tasks)
    tasks = [x for x in tasks if x.get("id") != task_id]
    if len(tasks) != before:
        save_json(TASK_FILE, tasks)
        return True
    return False

def list_tasks(include_done=False):
    return [task for task in tasks if include_done or not task.get("done")]

def parse_relative_reminder(text):
    t = normalize_bangla(text)
    minutes = None
    patterns = [(r"(\d+)\s*(?:মিনিট|minute|minutes)", "minutes"), (r"(\d+)\s*(?:ঘণ্টা|ঘন্টা|hour|hours)", "hours"), (r"(\d+)\s*(?:দিন|day|days)", "days")]
    for pattern, unit in patterns:
        m = re.search(pattern, t)
        if m:
            value = int(m.group(1))
            minutes = value if unit == "minutes" else value * 60 if unit == "hours" else value * 1440
            break
    if minutes is None:
        return None
    title = re.sub(r"(\d+)\s*(মিনিট|minute|minutes|ঘণ্টা|ঘন্টা|hour|hours|দিন|day|days)", "", t)
    title = re.sub(r"মনে করিয়ে দিও|মনে করিয়ে দিও|মনে করিও|remind me|remind", "", title).strip() or "Reminder"
    due = datetime.now() + timedelta(minutes=minutes)
    return {"title": title, "due": due.isoformat(timespec="minutes")}

def add_reminder(title, due):
    item = {"id": make_id("reminder"), "title": title, "due": due, "done": False, "created": datetime.now().isoformat(timespec="seconds")}
    tasks.append(item)
    save_json(TASK_FILE, tasks)
    return item

def due_reminders():
    now = datetime.now()
    result = []
    for item in tasks:
        if item.get("done") or not item.get("due"):
            continue
        try:
            if datetime.fromisoformat(item.get("due")) <= now:
                result.append(item)
        except Exception:
            pass
    return result

def add_note(text, title=""):
    item = {"id": make_id("note"), "title": title.strip() or "Note", "text": text.strip(), "created": datetime.now().isoformat(timespec="seconds")}
    notes.append(item)
    save_json(NOTE_FILE, notes)
    return item

def delete_note(note_id):
    global notes
    before = len(notes)
    notes = [n for n in notes if n.get("id") != note_id]
    if len(notes) != before:
        save_json(NOTE_FILE, notes)
        return True
    return False

def add_sale(amount, item="", quantity=1, note=""):
    sale = {"id": make_id("sale"), "amount": float(amount), "item": item.strip(), "quantity": int(quantity), "note": note.strip(), "created": datetime.now().isoformat(timespec="seconds")}
    sales.append(sale)
    save_json(SALES_FILE, sales)
    return sale

def sales_summary():
    total = sum(float(x.get("amount", 0)) for x in sales)
    today = datetime.now().date()
    today_total = 0
    for x in sales:
        try:
            if datetime.fromisoformat(x.get("created", "")).date() == today:
                today_total += float(x.get("amount", 0))
        except Exception:
            pass
    return total, today_total, len(sales)

def try_business_command(text):
    t = normalize_bangla(text)
    sale_patterns = [r"(?:বিক্রি|sale|sold).*?(\d+(?:\.\d+)?)", r"(\d+(?:\.\d+)?)\s*(?:টাকা|taka).*?(?:বিক্রি|sale)"]
    for pattern in sale_patterns:
        m = re.search(pattern, t)
        if m:
            amount = float(m.group(1))
            item = ""
            item_match = re.search(r"(?:বিক্রি|sale|sold)\s+(.+?)\s+\d", t)
            if item_match:
                item = item_match.group(1)
            add_sale(amount, item)
            return f"বিক্রির হিসাব যোগ হয়েছে।\nপরিমাণ: {amount:g} টাকা\nমোট বিক্রি রেকর্ড: {len(sales)}টি"
    if any(x in t for x in ["বিক্রির হিসাব", "আজকের বিক্রি", "মোট বিক্রি", "sales summary", "sales report"]):
        total, today_total, count = sales_summary()
        return f"বিক্রির হিসাব:\nআজকের বিক্রি: {today_total:g} টাকা\nমোট বিক্রি: {total:g} টাকা\nমোট রেকর্ড: {count}টি"
    return None

def personal_assistant_command(text):
    t = normalize_bangla(text)
    if any(x in t for x in ["এখন সময়", "এখন কয়টা", "এখন কয়টা", "what time", "current time"]):
        return bangla_now()
    if any(x in t for x in ["আজকের তারিখ", "আজ কি বার", "আজ কী বার", "today", "date"]):
        return bangla_date()
    if any(x in t for x in ["মনে করিয়ে দিও", "মনে করিয়ে দিও", "মনে করিও", "remind me", "reminder"]):
        reminder = parse_relative_reminder(text)
        if reminder:
            item = add_reminder(reminder["title"], reminder["due"])
            return f"ঠিক আছে। Reminder সেট করা হয়েছে।\nকাজ: {item['title']}\nসময়: {reminder['due'].replace('T', ' ')}"
        return "Reminder সেট করতে সময় উল্লেখ করো।\nউদাহরণ: ১০ মিনিট পরে আমাকে পানি খাওয়ার কথা মনে করিয়ে দিও।"
    if any(x in t for x in ["task যোগ কর", "task add", "কাজ যোগ কর", "কাজ লিখে রাখ", "আমার কাজ লিখে রাখ"]):
        title = re.sub(r"task যোগ কর|task add|কাজ যোগ কর|কাজ লিখে রাখ|আমার কাজ লিখে রাখ", "", t).strip()
        if title:
            item = add_task(title)
            return f"Task যোগ করা হয়েছে: {item['title']}"
        return "কোন কাজটি যোগ করবো?"
    if any(x in t for x in ["আমার task", "আমার কাজ", "কাজের তালিকা", "task list", "show tasks"]):
        active = list_tasks()
        if not active:
            return "বর্তমানে কোনো অসম্পন্ন task নেই।"
        lines = ["তোমার অসম্পন্ন কাজ:"]
        for i, task in enumerate(active, 1):
            due = task.get("due", "")
            lines.append(f"{i}. {task['title']} — {due}" if due else f"{i}. {task['title']}")
        return "\n".join(lines)
    if any(x in t for x in ["নোট করে রাখ", "note করে রাখ", "save note", "নোট লিখে রাখ"]):
        note_text = re.sub(r"নোট করে রাখ|note করে রাখ|save note|নোট লিখে রাখ", "", t).strip()
        if note_text:
            add_note(note_text)
            return "নোটটি সংরক্ষণ করেছি।"
        return "কী নোট করে রাখবো?"
    if any(x in t for x in ["আমার নোট", "notes দেখাও", "show notes"]):
        if not notes:
            return "কোনো নোট নেই।"
        lines = ["তোমার নোট:"]
        for i, note in enumerate(notes[-10:], 1):
            lines.append(f"{i}. {note.get('text', '')}")
        return "\n".join(lines)
    if any(x in t for x in ["facebook reply", "ফেসবুক রিপ্লাই", "ফেসবুকের উত্তর", "ফেসবুক মেসেজের উত্তর"]):
        return "Facebook Assistant Mode চালু আছে। তুমি যে message/comment-এর উত্তর দিতে চাও সেটি লিখে দাও। আমি একটি সুন্দর reply তৈরি করে দেব। ব্যক্তিগত Facebook profile-এ আমি নিজে থেকে message/comment পাঠাচ্ছি না।"
    return None

def memory_reply(question):
    best = None
    best_score = 0
    for item in memories:
        if not isinstance(item, dict):
            continue
        q = item.get("question", "")
        a = item.get("answer", "")
        if not q or not a:
            continue
        score = max(similarity(question, q), token_score(question, q))
        if score > best_score:
            best_score = score
            best = a
    if best and best_score >= 0.72:
        return best
    return None

def intent_reply(question):
    best_answer = None
    best_score = 0
    for questions, answer in INTENTS:
        for q in questions:
            score = max(similarity(question, q), token_score(question, q))
            if score > best_score:
                best_score = score
                best_answer = answer
    if best_answer and best_score >= 0.68:
        return best_answer
    return None

def try_tools(text):
    t = normalize_bangla(text)
    if any(x in t for x in ["এখন সময়", "এখন কয়টা", "এখন কয়টা", "what time"]):
        return bangla_now()
    if any(x in t for x in ["আজকের তারিখ", "আজ কী বার", "আজ কি বার", "today", "date"]):
        return bangla_date()
    result = try_percent(text)
    if result:
        return result
    result = try_convert(text)
    if result:
        return result
    result = try_math(text)
    if result:
        return result
    if "word count" in t or "কতটি শব্দ" in t:
        return f"শব্দ সংখ্যা: {len(text.split())}"
    if "coin flip" in t or "কয়েন" in t or "কয়েন" in t:
        return f"ফলাফল: {random.choice(['Head', 'Tail'])}"
    if "আরও বলো" in t or "more বলো" in t:
        return "অবশ্যই। কোন অংশটি বিস্তারিত জানতে চাও?"
    return None

def get_smart_reply(question):
    for fn in (memory_reply, personal_assistant_command, try_business_command, try_tools, intent_reply):
        result = fn(question)
        if result:
            return result
    return None

def ask_gemini(question, api_key, history=None, image_base64=None, mime_type="image/jpeg", memories_data=None):
    if not api_key:
        return None, "Gemini API key পাওয়া যায়নি। Settings থেকে API key বসাও।"
    history = history or []
    memories_data = memories_data or memories
    memory_text = ""
    if memories_data:
        for item in memories_data[-40:]:
            if isinstance(item, dict):
                q = item.get("question", "")
                a = item.get("answer", "")
                if q and a:
                    memory_text += f"Q: {q}\nA: {a}\n"
    history_text = ""
    for item in history[-8:]:
        if isinstance(item, dict) and item.get("content"):
            history_text += f"{item.get('role', '')}: {item.get('content', '')}\n"
    system_text = f"""
You are Shofiq AI, a personal AI assistant created by Shofiq.

Language rules:
- Understand Bangla, Banglish and English.
- Reply naturally in the user's language.
- If the user writes Banglish, understand it and preferably reply in Bangla.
- Do not explain emojis automatically.
- Do not claim to have performed an action unless the local program actually performed it.
- Keep answers useful and clear.
- When asked about Shofiq, use the supplied profile.
- Do not invent personal information.

Shofiq profile:
Name: {USER_PROFILE['name']}
Short name: {USER_PROFILE['short_name']}
Location: {USER_PROFILE['location']}
College: {USER_PROFILE['college']}
Subject: {USER_PROFILE['subject']}
Goal: {USER_PROFILE['goal']}
Wife: {USER_PROFILE['wife']}

Known local memory:
{memory_text}

Recent conversation:
{history_text}
"""
    prompt = system_text + "\n\nUser:\n" + question
    parts = [{"text": prompt}]
    if image_base64:
        parts.append({"inline_data": {"mime_type": mime_type or "image/jpeg", "data": image_base64}})
    payload = {"contents": [{"role": "user", "parts": parts}], "generationConfig": {"temperature": 0.7, "maxOutputTokens": 4096}}
    last_error = ""
    for model in GEMINI_MODELS:
        url = "https://generativelanguage.googleapis.com/" f"v1beta/models/{model}:generateContent"
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", "x-goog-api-key": api_key}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read().decode("utf-8")
            result = json.loads(raw)
            candidates = result.get("candidates", [])
            if candidates:
                parts_out = candidates[0].get("content", {}).get("parts", [])
                answer = "\n".join(p.get("text", "") for p in parts_out if isinstance(p, dict) and p.get("text")).strip()
                if answer:
                    return answer, None
            last_error = "Gemini returned an empty response."
        except urllib.error.HTTPError as e:
            try:
                error_body = e.read().decode("utf-8")
            except Exception:
                error_body = str(e)
            last_error = f"HTTP {e.code}: {error_body[:500]}"
            continue
        except Exception as e:
            last_error = str(e)
            continue
    return None, last_error or "Gemini API request failed."

def save_memory(question, answer, source="auto"):
    question = question.strip()
    answer = answer.strip()
    if not question or not answer:
        return False
    for item in memories:
        if normalize_bangla(item.get("question", "")) == normalize_bangla(question):
            item["answer"] = answer
            item["source"] = source
            item["updated"] = datetime.now().isoformat(timespec="seconds")
            save_json(MEMORY_FILE, memories)
            return True
    memories.append({"id": make_id("memory"), "question": question, "answer": answer, "source": source, "created": datetime.now().isoformat(timespec="seconds")})
    save_json(MEMORY_FILE, memories)
    return True

HTML = r"""
<!DOCTYPE html>
<html lang="bn">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#111827">
<title>Shofiq AI 6.1</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;500;600;700&family=Noto+Sans+Bengali:wght@400;500;600;700&display=swap');
*{box-sizing:border-box}
:root{
  --bg:#070b16;--panel:#101629ee;--panel2:#151d34cc;--text:#f7f8ff;--muted:#9aa5bd;
  --border:rgba(143,169,218,.22);--blue:#4c86ff;--purple:#7658f4;--cyan:#21aee7;--green:#38e0a1;
  --user:#244b9b;--ai:#121a2e;--font:"Hind Siliguri","Noto Sans Bengali","Segoe UI",sans-serif;
  --safe-b:env(safe-area-inset-bottom,0px)
}
body.light{--bg:#f4f7fb;--panel:#ffffffee;--panel2:#eef2f8cc;--text:#172033;--muted:#687386;--border:rgba(0,0,0,.1);--ai:#eef2f7;--user:#1d4ed8}
html,body{width:100%;height:100%;margin:0}
body{font-family:var(--font);background:radial-gradient(circle at 50% 10%,#15264a 0,#070b16 42%);color:var(--text);overflow:hidden;-webkit-font-smoothing:antialiased}
button,input,textarea,select{font-family:inherit}button{cursor:pointer}
.app{height:100dvh;display:flex;position:relative}
.main{flex:1;display:flex;flex-direction:column;min-width:0}
.sidebar{position:fixed;left:-300px;top:0;bottom:0;width:280px;background:rgba(16,22,41,.86);backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);border-right:1px solid var(--border);padding:14px;overflow-y:auto;transition:.25s;z-index:70;box-shadow:20px 0 60px rgba(0,0,0,.35)}
.sidebar.open{left:0}
.sidebar-close{width:100%;border:1px solid rgba(255,255,255,.14);background:rgba(76,134,255,.12);color:#b9caff;padding:10px 12px;margin:0 0 12px;border-radius:12px;text-align:center;font-size:15px}
.sidebar-close:hover{background:rgba(76,134,255,.24);color:#fff}
.brand{font-size:22px;font-weight:700;margin-bottom:14px;line-height:1.25}
.brand small{display:block;color:var(--muted);font-size:11px;font-weight:400;margin-top:2px}
.menu-btn{width:100%;border:1px solid var(--border);background:rgba(21,29,52,.55);color:var(--text);padding:11px;margin:4px 0;border-radius:12px;text-align:left;font-size:15px;transition:transform .15s ease,border-color .15s ease,background .15s ease}
.menu-btn:hover{border-color:var(--blue)}
.menu-btn:active{transform:scale(.98)}
.section{margin-top:16px;border-top:1px solid var(--border);padding-top:12px}
.section-title{color:var(--muted);font-size:12px;margin-bottom:7px;letter-spacing:.04em}
.topbar{min-height:56px;height:56px;display:flex;align-items:center;gap:10px;padding:6px 12px;border-bottom:1px solid var(--border);background:rgba(7,11,22,.72);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);z-index:5;box-sizing:border-box}
.icon-btn{width:36px;height:36px;border:1px solid var(--border);border-radius:50%;background:rgba(21,29,52,.7);color:var(--text);font-size:16px;transition:transform .15s ease,box-shadow .15s ease;flex-shrink:0}
.icon-btn:active{transform:scale(.94)}
.brand-pill{display:flex;align-items:center;gap:8px;padding:4px 12px 4px 4px;border:1px solid rgba(110,160,240,.38);border-radius:28px;background:linear-gradient(115deg,rgba(40,70,130,.55),rgba(18,28,55,.72));box-shadow:0 2px 12px rgba(40,100,220,.14);min-height:40px;height:40px;max-width:100%}
.brand-avatar{width:32px;height:32px;display:grid;place-items:center;border-radius:10px;border:1px solid #3a75d8;background:linear-gradient(145deg,#1a2d55,#101a35);color:#8ab6ff;font-size:15px;font-weight:700;flex:0 0 32px}
.brand-copy{display:flex;flex-direction:column;justify-content:center;gap:3px;padding:3px 0 2px;min-width:0}
.brand-name{font-size:15px;font-weight:700;line-height:1.15;letter-spacing:.01em}
.online{display:block;color:var(--green);font-size:11px;line-height:1.2;font-weight:600;white-space:nowrap}
.top-actions{margin-left:auto}
.more{font-size:20px;letter-spacing:2px}
.chat{flex:1;overflow-y:auto;overflow-x:hidden;padding:10px 16px 120px;-webkit-overflow-scrolling:touch}
.welcome{max-width:720px;margin:0 auto;text-align:center;padding:16px 0 28px;overflow:visible}
.hero-wrap{position:relative;width:min(200px,56vw);height:auto;margin:8px auto 4px;padding:4px 8px 4px;overflow:visible;display:flex;flex-direction:column;align-items:center;gap:0}
.hero-logo{width:min(150px,44vw);height:min(150px,44vw);margin:0 auto;display:grid;place-items:center;position:relative;border:1.5px solid rgba(100,160,255,.65);background:linear-gradient(145deg,#243b66,#0d1730 72%);clip-path:polygon(50% 0,92% 24%,92% 76%,50% 100%,8% 76%,8% 24%);box-shadow:0 0 36px rgba(80,140,255,.45),0 0 80px rgba(60,120,255,.2);animation:logoFloat 4.8s ease-in-out infinite}
.hero-logo::before{content:"";position:absolute;width:58%;height:58%;border:2px solid rgba(120,180,255,.5);border-radius:50%;pointer-events:none;box-shadow:0 0 18px rgba(90,150,255,.25) inset}
.hero-logo::after{content:"";position:absolute;inset:-22px;border-radius:50%;background:radial-gradient(circle,rgba(90,150,255,.4) 0%,rgba(70,130,255,.12) 45%,transparent 70%);filter:blur(10px);z-index:-1;animation:glowPulse 4.8s ease-in-out infinite;pointer-events:none}
.hero-logo span{font-size:clamp(48px,13vw,84px);font-weight:700;color:#8ec0ff;text-shadow:0 0 20px rgba(80,150,255,.9),0 0 40px rgba(60,120,255,.5);z-index:1;line-height:1}
.verified{position:relative;margin-top:18px;padding:8px 18px;border-radius:999px;background:linear-gradient(105deg,#1a6fff,#6b93ff);box-shadow:0 8px 22px rgba(40,110,255,.55),0 0 0 1px rgba(255,255,255,.12) inset;font-size:13px;font-weight:700;white-space:nowrap;z-index:5;letter-spacing:.03em;color:#fff;animation:badgePulse 2.8s ease-in-out infinite}
.welcome h1{font-size:clamp(26px,5vw,42px);line-height:1.2;margin:20px 0 10px;font-weight:700;background:linear-gradient(180deg,#ffffff 30%,#a8c4ff 100%);-webkit-background-clip:text;background-clip:text;color:transparent}
.welcome p{color:var(--muted);font-size:clamp(15px,2.4vw,20px);line-height:1.45;margin:0 auto 22px;max-width:560px}
.cards{display:flex;flex-direction:column;gap:12px;margin:0 auto;max-width:640px}
.card{min-height:86px;display:flex;align-items:center;gap:14px;padding:14px 16px;border:1px solid rgba(160,190,255,.28);border-radius:22px;background:linear-gradient(125deg,rgba(28,42,78,.55),rgba(14,22,42,.38));backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);color:var(--text);text-align:left;cursor:pointer;box-shadow:0 12px 32px rgba(0,0,0,.22),inset 0 1px 0 rgba(255,255,255,.06);transition:transform .18s ease,border-color .18s ease,box-shadow .18s ease,background .18s ease}
.card:hover{border-color:rgba(100,160,255,.65);box-shadow:0 14px 36px rgba(50,110,230,.22),inset 0 1px 0 rgba(255,255,255,.08);background:linear-gradient(125deg,rgba(34,52,95,.62),rgba(18,28,52,.45))}
.card:active{transform:scale(.975)}
.card-icon{width:56px;height:56px;display:grid;place-items:center;flex:0 0 56px;border-radius:18px;font-size:26px;background:linear-gradient(135deg,#7b52f2,#8b6aff)}
.card:nth-child(2) .card-icon{background:linear-gradient(135deg,#277dff,#1bc0d6)}
.card:nth-child(3) .card-icon{background:linear-gradient(135deg,#14bb9c,#2dd3a0)}
.card-copy{flex:1;min-width:0}
.card-title{display:block;font-size:18px;font-weight:700;line-height:1.25}
.card-sub{display:block;margin-top:3px;color:var(--muted);font-size:14px;line-height:1.35}
.card-arrow{font-size:26px;color:#b7c0d4}
.messages{max-width:850px;margin:8px auto}
.message{display:flex;margin:10px 0;animation:msgIn .28s ease}
.message.user{justify-content:flex-end}
.bubble{max-width:min(82%,640px);padding:12px 14px;border-radius:18px;white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.65;font-weight:500;box-shadow:0 8px 20px rgba(0,0,0,.14)}
.user .bubble{background:linear-gradient(160deg,#2a57b3,#1d3f86);border-bottom-right-radius:6px;color:#fff}
.ai .bubble{background:rgba(18,26,46,.72);border:1px solid var(--border);border-bottom-left-radius:6px;backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px)}
.meta{font-size:10px;color:var(--muted);margin-top:6px}
.copy-btn{margin-top:7px;padding:5px 9px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--muted);font-size:11px}
.copy-btn:active{transform:scale(.96)}
.typing{display:inline-flex;gap:5px;align-items:center;height:18px}
.typing span{width:7px;height:7px;border-radius:50%;background:var(--muted);animation:bounce 1s infinite}
.typing span:nth-child(2){animation-delay:.15s}
.typing span:nth-child(3){animation-delay:.3s}
@keyframes bounce{0%,80%,100%{transform:translateY(0);opacity:.4}40%{transform:translateY(-4px);opacity:1}}
@keyframes logoFloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-7px)}}
@keyframes glowPulse{0%,100%{opacity:.55}50%{opacity:1}}
@keyframes badgePulse{0%,100%{box-shadow:0 6px 16px rgba(42,113,255,.4)}50%{box-shadow:0 6px 22px rgba(70,143,255,.75)}}
@keyframes msgIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.composer{position:fixed;left:50%;transform:translateX(-50%);width:min(672px,calc(100% - 16px));z-index:10;bottom:calc(10px + var(--safe-b));transition:bottom .12s ease}
.composer-inner{display:flex;flex-direction:row;flex-wrap:nowrap;align-items:center;gap:6px;height:50px;background:rgba(16,24,48,.88);border:1px solid rgba(120,160,230,.38);border-radius:25px;padding:6px 8px;box-shadow:0 10px 28px rgba(0,0,0,.35),inset 0 1px 0 rgba(255,255,255,.05);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);transition:box-shadow .2s ease,border-color .2s ease;overflow:hidden;box-sizing:border-box}
.composer-inner:focus-within{border-color:rgba(110,170,255,.85);box-shadow:0 0 0 3px rgba(80,140,255,.2),0 12px 30px rgba(0,0,0,.38)}
textarea{flex:1 1 auto;min-width:0;width:100%;resize:none;height:36px;min-height:36px;max-height:36px;border:0;outline:0;background:transparent;color:var(--text);padding:7px 4px;font-size:15px;line-height:22px;overflow-y:hidden;white-space:nowrap;text-overflow:ellipsis}
.action-btn{width:36px;height:36px;flex:0 0 36px;border-radius:50%;border:0;background:#1c2742;color:var(--text);font-size:15px;line-height:1;display:inline-flex;align-items:center;justify-content:center;padding:0;margin:0;transition:transform .15s ease,opacity .15s ease,box-shadow .15s ease}
.action-btn:active{transform:scale(.94)}
.send{background:linear-gradient(135deg,#518bff,#6a5fff);font-size:16px;box-shadow:0 0 12px rgba(72,128,255,.3);color:#fff}
.send:disabled{opacity:.4;box-shadow:none;cursor:default;background:#2a3550;color:#9aa5bd}
.send.ready{opacity:1}
input[type=file]{display:none}
.panel{position:fixed;right:-440px;top:0;width:min(390px,94vw);height:100dvh;background:rgba(16,22,41,.9);backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);border-left:1px solid var(--border);z-index:80;transition:.25s;padding:18px;overflow-y:auto}
.panel.open{right:0}
.panel-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:15px}
.panel-header h2{margin:0;font-size:20px;line-height:1.3}
.close{border:0;background:transparent;color:var(--text);font-size:24px}
.field{margin:12px 0}
.field label{display:block;font-size:13px;color:var(--muted);margin-bottom:6px}
.field input,.field textarea,.field select{width:100%;padding:11px;border-radius:10px;border:1px solid var(--border);background:rgba(21,29,52,.7);color:var(--text);outline:none}
.field input:focus,.field textarea:focus,.field select:focus{border-color:rgba(92,146,255,.7);box-shadow:0 0 0 3px rgba(76,134,255,.16)}
.primary{border:0;background:var(--blue);color:white;padding:11px 14px;border-radius:10px;transition:transform .15s ease}
.primary:active{transform:scale(.97)}
.danger{border:0;background:#b83250;color:white;padding:9px 12px;border-radius:9px}
.list-item{padding:11px;margin:7px 0;border:1px solid var(--border);border-radius:12px;background:rgba(21,29,52,.55);backdrop-filter:blur(8px)}
.list-item-title{font-weight:600;line-height:1.35}
.list-item-text{color:var(--muted);font-size:13px;white-space:pre-wrap;margin-top:4px;line-height:1.5}
.small{color:var(--muted);font-size:12px;line-height:1.45}
.row{display:flex;gap:7px;align-items:center}
.row>*{flex:1}
.overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:60}
.overlay.show{display:block}
.new-msg{position:fixed;left:50%;transform:translateX(-50%);bottom:92px;z-index:12;border:0;border-radius:999px;padding:8px 14px;background:rgba(76,134,255,.92);color:#fff;font-size:13px;font-weight:600;box-shadow:0 8px 20px rgba(0,0,0,.28);display:none}
.new-msg.show{display:block}
@media(max-width:600px){
  .topbar{min-height:48px;height:48px;padding:4px 8px;gap:6px}
  .icon-btn{width:34px;height:34px;font-size:15px}
  .brand-pill{min-height:36px;height:36px;padding:2px 10px 2px 2px;gap:6px;border-radius:22px}
  .brand-avatar{width:30px;height:30px;font-size:14px;border-radius:9px}
  .brand-name{font-size:14px}
  .online{font-size:10px}
  .hero-wrap{width:min(160px,46vw);padding:4px 0 4px;margin:4px auto 0}
  .hero-logo{width:min(120px,40vw);height:min(120px,40vw)}
  .verified{font-size:11px;padding:5px 12px;margin-top:10px}
  .chat{padding:6px 12px 100px}
  .card{min-height:72px;padding:10px 12px;gap:10px}
  .card-icon{width:42px;height:42px;flex-basis:42px;font-size:20px;border-radius:14px}
  .card-title{font-size:16px}
  .card-sub{font-size:13px}
  .composer{width:calc(100% - 14px);bottom:calc(8px + var(--safe-b))}
  .composer-inner{height:48px;gap:5px;padding:5px 7px;border-radius:24px}
  .action-btn{width:36px;height:36px;flex:0 0 36px;font-size:15px}
  .send{font-size:15px}
  textarea{font-size:15px;height:36px;min-height:36px;max-height:36px;padding:7px 2px;line-height:22px}
}


.card{border-left:3px solid #5b8cff}
.card:nth-child(2){border-left-color:#22c3e0}
.card:nth-child(3){border-left-color:#2dd3a0}
.verified{margin-top:12px}
@media (prefers-reduced-motion: reduce){
  .hero-logo,.hero-logo::after,.verified,.message{animation:none}
  .card,.action-btn,.menu-btn,.primary{transition:none}
}
</style>
</head>
<body>
<div class="app">
<aside class="sidebar" id="sidebar">
    <div class="brand">Shofiq AI <small>Personal Assistant UI 6.1</small></div>
    <button class="sidebar-close" onclick="toggleSidebar()">× বন্ধ করুন</button>
    <button class="menu-btn" onclick="newChat()">＋ New Chat</button>
    <button class="menu-btn" onclick="openPanel('teachPanel')">🧠 Teach AI</button>
    <button class="menu-btn" onclick="openPanel('memoryPanel')">🗃 Memory</button>
    <button class="menu-btn" onclick="openPanel('taskPanel')">✓ Tasks & Reminders</button>
    <button class="menu-btn" onclick="openPanel('notePanel')">📝 Notes</button>
    <button class="menu-btn" onclick="openPanel('salesPanel')">💰 Business / Sales</button>
    <button class="menu-btn" onclick="openPanel('facebookPanel')">💬 Facebook Assistant</button>
    <button class="menu-btn" onclick="exportMemory()">↓ Export Memory</button>
    <button class="menu-btn" onclick="document.getElementById('importFile').click()">↑ Import Memory</button>
    <input type="file" id="importFile" accept=".json" onchange="importMemory(event)">
    <div class="section"><div class="section-title">APPEARANCE</div><button class="menu-btn" onclick="toggleTheme()">◐ Dark / Light</button><div class="field"><label>Font Size</label><input id="fontSlider" type="range" min="12" max="22" value="15" oninput="changeFont(this.value)"></div><button class="menu-btn" onclick="toggleAutoVoice()">🔊 Auto Voice <span id="voiceState">OFF</span></button><button class="menu-btn" onclick="toggleAutoLearn()">🧠 Auto Learn <span id="learnState">ON</span></button></div>
    <div class="section"><div class="section-title">AI SETTINGS</div><button class="menu-btn" onclick="openPanel('settingsPanel')">⚙ API / Settings</button><button class="menu-btn" onclick="openPanel('systemPanel')">ℹ System Info</button></div>
</aside>
<main class="main">
    <div class="topbar">
        <button class="icon-btn" onclick="toggleSidebar()">☰</button>
        <div class="brand-pill"><div class="brand-avatar">S</div><div class="brand-copy"><div class="brand-name">Shofiq AI</div><span class="online">● অনলাইন</span></div></div>
        <div class="top-actions"><button class="icon-btn more" onclick="toggleSidebar()">•••</button></div>
    </div>
    <section class="chat" id="chat">
        <div class="welcome" id="welcome">
            <div class="hero-wrap">
                <div class="hero-logo"><span>Š</span></div>
                <b class="verified">✓ verified</b>
            </div>
            <h1>কীভাবে সাহায্য করতে পারি?</h1>
            <p>আমি এখানে আছি তোমার 💜 যেকোনো প্রশ্নের উত্তর দিতে</p>
            <div class="cards">
                <div class="card" onclick="quickAsk('তুমি কে?')"><div class="card-icon">?</div><div class="card-copy"><span class="card-title">তুমি কে?</span><span class="card-sub">আমার পরিচয় জানতে চাও</span></div><span class="card-arrow">›</span></div>
                <div class="card" onclick="quickAsk('তুমি কী কী করতে পারো?')"><div class="card-icon">✦</div><div class="card-copy"><span class="card-title">তুমি কী করতে পারো?</span><span class="card-sub">তোমার smart features জানতে চাও</span></div><span class="card-arrow">›</span></div>
                <div class="card" onclick="quickAsk('আমার সম্পর্কে বলো')"><div class="card-icon">♥</div><div class="card-copy"><span class="card-title">আমার সম্পর্কে বলো</span><span class="card-sub">আমার তথ্য মনে আছে কি না দেখো</span></div><span class="card-arrow">›</span></div>
            </div>
        </div>
        <div class="messages" id="messages"></div>
    </section>
    <button class="new-msg" id="newMsgBtn" onclick="jumpToLatest()">নতুন মেসেজ ↓</button>
    <div class="composer"><div class="composer-inner">
        <button class="action-btn" onclick="document.getElementById('cameraInput').click()" title="Camera">📷</button>
        <input id="cameraInput" type="file" accept="image/*" capture="environment" onchange="handleImage(event)">
        <button class="action-btn" onclick="startVoice()" title="Voice">🎙</button>
        <textarea id="input" placeholder="তোমার প্রশ্ন লিখো..." onkeydown="handleKey(event)" oninput="updateSendState()"></textarea>
        <button class="action-btn send" id="sendBtn" onclick="sendMessage()" disabled>➤</button>
    </div></div>
</main>
</div>
<div class="overlay" id="overlay" onclick="closeAllPanels()"></div>
<div class="panel" id="teachPanel">
    <div class="panel-header"><h2>Teach AI</h2><button class="close" onclick="closeAllPanels()">×</button></div>
    <p class="small">Format: question | answer</p>
    <div class="field"><label>Question</label><textarea id="teachQuestion" rows="3" placeholder="তোমার নাম কী?"></textarea></div>
    <div class="field"><label>Answer</label><textarea id="teachAnswer" rows="5" placeholder="আমার নাম Shofiq AI।"></textarea></div>
    <button class="primary" onclick="teachAI()">Save Knowledge</button>
    <div id="teachStatus" class="small" style="margin-top:10px"></div>
</div>
<div class="panel" id="memoryPanel">
    <div class="panel-header"><h2>Memory</h2><button class="close" onclick="closeAllPanels()">×</button></div>
    <div class="small">Local browser memory + Python permanent memory</div>
    <div id="memoryList" style="margin-top:12px"></div>
</div>
<div class="panel" id="taskPanel">
    <div class="panel-header"><h2>Tasks & Reminders</h2><button class="close" onclick="closeAllPanels()">×</button></div>
    <div class="field"><label>New Task</label><div class="row"><input id="taskInput" placeholder="যেমন: Economics পড়া"><button class="primary" onclick="addTaskUI()">Add</button></div></div>
    <div id="taskList"></div>
</div>
<div class="panel" id="notePanel">
    <div class="panel-header"><h2>Notes</h2><button class="close" onclick="closeAllPanels()">×</button></div>
    <div class="field"><textarea id="noteInput" rows="5" placeholder="এখানে নোট লিখো..."></textarea><button class="primary" onclick="addNoteUI()" style="margin-top:7px">Save Note</button></div>
    <div id="noteList"></div>
</div>
<div class="panel" id="salesPanel">
    <div class="panel-header"><h2>Business / Sales</h2><button class="close" onclick="closeAllPanels()">×</button></div>
    <div id="salesSummary"></div>
    <div class="field"><label>Item</label><input id="saleItem" placeholder="Chicken Feed"></div>
    <div class="field"><label>Amount</label><input id="saleAmount" type="number" placeholder="500"></div>
    <div class="field"><label>Quantity</label><input id="saleQuantity" type="number" value="1"></div>
    <button class="primary" onclick="addSaleUI()">Add Sale</button>
    <div id="salesList" style="margin-top:12px"></div>
</div>
<div class="panel" id="facebookPanel">
    <div class="panel-header"><h2>Facebook Assistant</h2><button class="close" onclick="closeAllPanels()">×</button></div>
    <p class="small">Facebook personal profile automation is not performed here. This mode helps you create replies that you can manually send.</p>
    <div class="field"><label>Incoming message / comment</label><textarea id="facebookInput" rows="7" placeholder="যে message-এর উত্তর দিতে চাও এখানে দাও..."></textarea></div>
    <button class="primary" onclick="generateFacebookReply()">Generate Reply</button>
    <div class="field"><label>Suggested Reply</label><textarea id="facebookOutput" rows="8"></textarea></div>
    <button class="primary" onclick="copyText('facebookOutput')">Copy Reply</button>
</div>
<div class="panel" id="settingsPanel">
    <div class="panel-header"><h2>API Settings</h2><button class="close" onclick="closeAllPanels()">×</button></div>
    <div class="field"><label>Provider</label><select id="provider"><option value="gemini">Gemini</option></select></div>
    <div class="field"><label>Gemini API Key</label><input id="apiKey" type="password" placeholder="Paste your Gemini API key"></div>
    <button class="primary" onclick="saveSettings()">Save Settings</button>
    <div id="settingsStatus" class="small" style="margin-top:10px"></div>
</div>
<div class="panel" id="systemPanel">
    <div class="panel-header"><h2>System Info</h2><button class="close" onclick="closeAllPanels()">×</button></div>
    <div class="list-item"><div class="list-item-title">Shofiq AI</div><div class="list-item-text">Version: 6.0
Python local server
Gemini AI
Camera Vision
Voice
Teach AI
Memory
Tasks
Reminders
Notes
Sales</div></div>
</div>
<script>
let memories = JSON.parse(localStorage.getItem("shofiq_memories") || "[]");
let history = [];
let autoVoice = localStorage.getItem("shofiq_autovoice") === "true";
let autoLearn = localStorage.getItem("shofiq_autolearn") !== "false";
let apiKey = localStorage.getItem("shofiq_api_key") || "";
let theme = localStorage.getItem("shofiq_theme") || "dark";
let fontSize = localStorage.getItem("shofiq_fontsize") || "15";
let stickToBottom = true;
document.body.classList.toggle("light", theme === "light");
document.documentElement.style.setProperty("--font-size", fontSize + "px");
document.getElementById("input").style.fontSize = fontSize + "px";
function saveBrowserMemory(){ localStorage.setItem("shofiq_memories", JSON.stringify(memories)); }
function escapeHTML(text){ return String(text).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;"); }
function nowTime(){ return new Date().toLocaleTimeString([], {hour:"2-digit", minute:"2-digit"}); }
function nearBottom(){
    const chat = document.getElementById("chat");
    return chat.scrollHeight - chat.scrollTop - chat.clientHeight < 90;
}
function showNewMsg(){ document.getElementById("newMsgBtn").classList.add("show"); }
function hideNewMsg(){ document.getElementById("newMsgBtn").classList.remove("show"); }
function scrollChat(force){
    const chat = document.getElementById("chat");
    if(force || stickToBottom){
        chat.scrollTo({top: chat.scrollHeight, behavior:"smooth"});
        hideNewMsg();
    } else {
        showNewMsg();
    }
}
function jumpToLatest(){ stickToBottom = true; scrollChat(true); }
function addMessage(role, text, copyable=true){
    document.getElementById("welcome").style.display = "none";
    const messages = document.getElementById("messages");
    const wrapper = document.createElement("div");
    wrapper.className = "message " + (role === "user" ? "user" : "ai");
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text;
    wrapper.appendChild(bubble);
    if(role === "ai" && copyable){
        const copy = document.createElement("button");
        copy.className = "copy-btn";
        copy.textContent = "Copy";
        copy.onclick = function(){
            navigator.clipboard.writeText(text).then(function(){
                copy.textContent = "✓ Copied";
                setTimeout(() => copy.textContent = "Copy", 1200);
            }).catch(function(){ copy.textContent = "Copy failed"; });
        };
        bubble.appendChild(document.createElement("br"));
        bubble.appendChild(copy);
    }
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = nowTime();
    bubble.appendChild(meta);
    messages.appendChild(wrapper);
    scrollChat(role === "user");
}
function showTyping(){
    const messages = document.getElementById("messages");
    const wrapper = document.createElement("div");
    wrapper.className = "message ai";
    wrapper.id = "typingMessage";
    wrapper.innerHTML = '<div class="bubble"><div class="typing"><span></span><span></span><span></span></div></div>';
    messages.appendChild(wrapper);
    scrollChat(false);
}
function removeTyping(){ const el = document.getElementById("typingMessage"); if(el){ el.remove(); } }
function speak(text){
    if(!("speechSynthesis" in window)){ return; }
    try{
        speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = "bn-BD";
        utterance.rate = 0.95;
        speechSynthesis.speak(utterance);
    }catch(e){}
}
function updateSendState(){
    const input = document.getElementById("input");
    const btn = document.getElementById("sendBtn");
    if(!input || !btn) return;
    const has = input.value.trim().length > 0;
    btn.disabled = !has;
    btn.classList.toggle("ready", has);
    /* single-line bar: keep fixed height */
    input.style.height = "36px";
}
function sendMessage(){
    const input = document.getElementById("input");
    const question = input.value.trim();
    if(!question){ return; }
    input.value = "";
    input.style.height = "36px";
    updateSendState();
    addMessage("user", question, false);
    history.push({role:"user", content:question});
    showTyping();
    fetch("/api/chat", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({question:question, memories:memories, history:history.slice(-8), api_key:apiKey, auto_learn:autoLearn})
    })
    .then(function(res){ return res.json(); })
    .then(function(data){
        removeTyping();
        const reply = data.reply || "কোনো উত্তর পাওয়া যায়নি।";
        addMessage("ai", reply, true);
        history.push({role:"assistant", content:reply});
        if(data.learned){
            memories.push({question:question, answer:reply, source:"auto"});
            saveBrowserMemory();
        }
        if(autoVoice){ speak(reply); }
    })
    .catch(function(error){
        removeTyping();
        addMessage("ai", "সংযোগে সমস্যা হয়েছে। আবার চেষ্টা করো।", false);
        console.error(error);
    });
}
function quickAsk(text){ document.getElementById("input").value = text; updateSendState(); sendMessage(); }
function handleKey(event){
    if(event.key === "Enter" && !event.shiftKey){
        event.preventDefault();
        sendMessage();
    }
}
function handleImage(event){
    const file = event.target.files[0];
    if(!file){ return; }
    addMessage("user", "📷 একটি ছবি বিশ্লেষণের জন্য পাঠানো হয়েছে।", false);
    showTyping();
    const reader = new FileReader();
    reader.onload = function(){
        const base64 = reader.result.split(",")[1];
        fetch("/api/chat", {
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({
                question:"এই ছবিটা কী? ছবিতে যা দেখা যাচ্ছে তা সহজভাবে বুঝিয়ে বলো।",
                image_base64:base64,
                mime_type:file.type,
                memories:memories,
                history:history.slice(-8),
                api_key:apiKey
            })
        })
        .then(function(res){ return res.json(); })
        .then(function(data){
            removeTyping();
            const reply = data.reply || "ছবিটি বিশ্লেষণ করা যায়নি।";
            addMessage("ai", reply);
            history.push({role:"user", content:"[Image]"});
            history.push({role:"assistant", content:reply});
            if(autoVoice){ speak(reply); }
        })
        .catch(function(){
            removeTyping();
            addMessage("ai", "ছবিটি বিশ্লেষণ করতে সমস্যা হয়েছে।", false);
        });
    };
    reader.readAsDataURL(file);
    event.target.value = "";
}
function startVoice(){
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if(!SpeechRecognition){
        addMessage("ai", "এই browser-এ Voice Recognition পাওয়া যায়নি।", false);
        return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = "bn-BD";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onresult = function(event){
        document.getElementById("input").value = event.results[0][0].transcript;
        updateSendState();
        sendMessage();
    };
    recognition.onerror = function(){ console.log("Voice recognition error"); };
    recognition.start();
}
function toggleSidebar(){ document.getElementById("sidebar").classList.toggle("open"); }
function openPanel(id){
    closeAllPanels();
    document.getElementById(id).classList.add("open");
    document.getElementById("overlay").classList.add("show");
    if(id === "memoryPanel"){ renderMemory(); }
    if(id === "taskPanel"){ renderTasks(); }
    if(id === "notePanel"){ renderNotes(); }
    if(id === "salesPanel"){ renderSales(); }
    if(id === "settingsPanel"){ document.getElementById("apiKey").value = apiKey; }
}
function closeAllPanels(){
    document.querySelectorAll(".panel").forEach(function(panel){ panel.classList.remove("open"); });
    document.getElementById("overlay").classList.remove("show");
    document.getElementById("sidebar").classList.remove("open");
}
function newChat(){
    document.getElementById("messages").innerHTML = "";
    history = [];
    document.getElementById("welcome").style.display = "block";
    hideNewMsg();
    closeAllPanels();
}
function toggleTheme(){
    document.body.classList.toggle("light");
    theme = document.body.classList.contains("light") ? "light" : "dark";
    localStorage.setItem("shofiq_theme", theme);
}
function changeFont(value){
    fontSize = value;
    localStorage.setItem("shofiq_fontsize", value);
    document.getElementById("input").style.fontSize = value + "px";
    document.documentElement.style.setProperty("--font-size", value + "px");
}
function toggleAutoVoice(){ autoVoice = !autoVoice; localStorage.setItem("shofiq_autovoice", autoVoice); updateStates(); }
function toggleAutoLearn(){ autoLearn = !autoLearn; localStorage.setItem("shofiq_autolearn", autoLearn); updateStates(); }
function updateStates(){
    document.getElementById("voiceState").textContent = autoVoice ? "ON" : "OFF";
    document.getElementById("learnState").textContent = autoLearn ? "ON" : "OFF";
}
function saveSettings(){
    apiKey = document.getElementById("apiKey").value.trim();
    localStorage.setItem("shofiq_api_key", apiKey);
    document.getElementById("settingsStatus").textContent = "Settings saved.";
}
function teachAI(){
    const question = document.getElementById("teachQuestion").value.trim();
    const answer = document.getElementById("teachAnswer").value.trim();
    if(!question || !answer){
        document.getElementById("teachStatus").textContent = "Question এবং answer দুটোই দিতে হবে।";
        return;
    }
    const questions = question.split(";").map(x => x.trim()).filter(Boolean);
    questions.forEach(function(q){ memories.push({question:q, answer:answer, source:"teach"}); });
    saveBrowserMemory();
    fetch("/api/teach", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({questions:questions, answer:answer})});
    document.getElementById("teachQuestion").value = "";
    document.getElementById("teachAnswer").value = "";
    document.getElementById("teachStatus").textContent = "✓ AI successfully learned.";
}
function renderMemory(){
    const list = document.getElementById("memoryList");
    if(!memories.length){ list.innerHTML = '<div class="small">Memory empty.</div>'; return; }
    list.innerHTML = "";
    memories.slice().reverse().forEach(function(item){
        const div = document.createElement("div");
        div.className = "list-item";
        div.innerHTML = '<div class="list-item-title">' + escapeHTML(item.question) + '</div><div class="list-item-text">' + escapeHTML(item.answer) + '</div>';
        list.appendChild(div);
    });
}
function exportMemory(){
    const data = {memories:memories, exported_at:new Date().toISOString()};
    const blob = new Blob([JSON.stringify(data,null,2)], {type:"application/json"});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "shofiq_ai_memory.json"; a.click();
    URL.revokeObjectURL(url);
}
function importMemory(event){
    const file = event.target.files[0];
    if(!file){ return; }
    const reader = new FileReader();
    reader.onload = function(){
        try{
            const data = JSON.parse(reader.result);
            const imported = Array.isArray(data) ? data : data.memories || [];
            memories = memories.concat(imported);
            saveBrowserMemory();
            alert("Memory imported successfully.");
        }catch(e){ alert("Invalid memory file."); }
    };
    reader.readAsText(file);
    event.target.value = "";
}
function addTaskUI(){
    const input = document.getElementById("taskInput");
    const title = input.value.trim();
    if(!title){ return; }
    fetch("/api/task", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({action:"add", title:title})})
    .then(res => res.json()).then(function(){ input.value = ""; renderTasks(); });
}
function renderTasks(){
    fetch("/api/data").then(res => res.json()).then(function(data){
        const list = document.getElementById("taskList");
        const items = data.tasks || [];
        if(!items.length){ list.innerHTML = '<div class="small">No tasks.</div>'; return; }
        list.innerHTML = "";
        items.slice().reverse().forEach(function(task){
            const div = document.createElement("div");
            div.className = "list-item";
            const title = document.createElement("div");
            title.className = "list-item-title";
            title.textContent = task.title;
            if(task.done){ title.style.textDecoration = "line-through"; }
            const info = document.createElement("div");
            info.className = "small";
            info.textContent = task.due ? "Due: " + task.due : "Task";
            const row = document.createElement("div");
            row.className = "row";
            if(!task.done){
                const done = document.createElement("button");
                done.className = "primary";
                done.textContent = "Done";
                done.onclick = function(){
                    fetch("/api/task", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({action:"complete", id:task.id})}).then(() => renderTasks());
                };
                row.appendChild(done);
            }
            const del = document.createElement("button");
            del.className = "danger";
            del.textContent = "Delete";
            del.onclick = function(){
                fetch("/api/task", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({action:"delete", id:task.id})}).then(() => renderTasks());
            };
            row.appendChild(del);
            div.appendChild(title); div.appendChild(info); div.appendChild(row);
            list.appendChild(div);
        });
    });
}
function addNoteUI(){
    const input = document.getElementById("noteInput");
    const text = input.value.trim();
    if(!text){ return; }
    fetch("/api/note", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({action:"add", text:text})})
    .then(res => res.json()).then(function(){ input.value = ""; renderNotes(); });
}
function renderNotes(){
    fetch("/api/data").then(res => res.json()).then(function(data){
        const list = document.getElementById("noteList");
        const items = data.notes || [];
        if(!items.length){ list.innerHTML = '<div class="small">No notes.</div>'; return; }
        list.innerHTML = "";
        items.slice().reverse().forEach(function(note){
            const div = document.createElement("div");
            div.className = "list-item";
            div.innerHTML = '<div class="list-item-text">' + escapeHTML(note.text) + '</div>';
            const del = document.createElement("button");
            del.className = "danger";
            del.textContent = "Delete";
            del.style.marginTop = "7px";
            del.onclick = function(){
                fetch("/api/note", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({action:"delete", id:note.id})}).then(() => renderNotes());
            };
            div.appendChild(del);
            list.appendChild(div);
        });
    });
}
function addSaleUI(){
    const item = document.getElementById("saleItem").value.trim();
    const amount = parseFloat(document.getElementById("saleAmount").value);
    const quantity = parseInt(document.getElementById("saleQuantity").value) || 1;
    if(!amount || amount <= 0){ alert("Amount দিতে হবে।"); return; }
    fetch("/api/sale", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({action:"add", item:item, amount:amount, quantity:quantity})})
    .then(res => res.json()).then(function(){ document.getElementById("saleAmount").value = ""; renderSales(); });
}
function renderSales(){
    fetch("/api/data").then(res => res.json()).then(function(data){
        const summary = document.getElementById("salesSummary");
        const list = document.getElementById("salesList");
        const items = data.sales || [];
        let total = 0;
        items.forEach(function(x){ total += Number(x.amount || 0); });
        summary.innerHTML = '<div class="list-item"><div class="list-item-title">Total Sales: ' + total + ' BDT</div><div class="small">' + items.length + ' records</div></div>';
        list.innerHTML = "";
        items.slice().reverse().slice(0,20).forEach(function(sale){
            const div = document.createElement("div");
            div.className = "list-item";
            div.innerHTML = '<div class="list-item-title">' + escapeHTML(sale.item || "Sale") + '</div><div class="list-item-text">' + Number(sale.amount) + ' BDT × ' + Number(sale.quantity) + '</div>';
            list.appendChild(div);
        });
    });
}
function generateFacebookReply(){
    const input = document.getElementById("facebookInput").value.trim();
    if(!input){ return; }
    document.getElementById("facebookOutput").value = "Reply তৈরি হচ্ছে...";
    const prompt = "Facebook message/comment-এর জন্য একটি natural, polite Bangla reply লিখো। অতিরিক্ত formal হবে না। User-এর message:\n\n" + input;
    fetch("/api/chat", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({question:prompt, api_key:apiKey, memories:memories, history:[]})})
    .then(res => res.json())
    .then(function(data){ document.getElementById("facebookOutput").value = data.reply || "Reply তৈরি করা যায়নি।"; })
    .catch(function(){ document.getElementById("facebookOutput").value = "Reply তৈরি করতে সমস্যা হয়েছে।"; });
}
function copyText(id){
    const el = document.getElementById(id);
    navigator.clipboard.writeText(el.value).then(function(){ if(id === "facebookOutput"){ alert("✓ Copied"); } });
}
document.getElementById("chat").addEventListener("scroll", function(){
    stickToBottom = nearBottom();
    if(stickToBottom){ hideNewMsg(); }
});
if(window.visualViewport){
    window.visualViewport.addEventListener("resize", function(){
        const kb = Math.max(0, window.innerHeight - window.visualViewport.height - window.visualViewport.offsetTop);
        document.querySelector(".composer").style.bottom = (kb + 8) + "px";
        document.getElementById("newMsgBtn").style.bottom = (kb + 78) + "px";
    });
}
updateStates();
updateSendState();
</script>
</body>
</html>

"""

def json_response(handler, data, status=200):
    raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(raw)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return
    def read_json(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/":
            raw = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        if path == "/api/data":
            total, today, count = sales_summary()
            json_response(self, {"tasks": tasks, "notes": notes, "sales": sales, "memories": memories, "sales_summary": {"total": total, "today": today, "count": count}})
            return
        if path == "/api/health":
            json_response(self, {"status": "ok", "app": APP_NAME, "version": VERSION})
            return
        self.send_error(404)
    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        data = self.read_json()
        if path == "/api/chat":
            question = str(data.get("question", "")).strip()
            api_key = str(data.get("api_key", "")).strip()
            history = data.get("history", [])
            client_memories = data.get("memories", [])
            auto_learn = bool(data.get("auto_learn", False))
            image_base64 = data.get("image_base64")
            mime_type = data.get("mime_type", "image/jpeg")
            if image_base64:
                answer, error = ask_gemini(question or "Describe this image in Bangla.", api_key, history, image_base64, mime_type, client_memories)
                if answer:
                    json_response(self, {"reply": answer, "learned": False})
                else:
                    json_response(self, {"reply": "ছবিটি বিশ্লেষণ করতে সমস্যা হয়েছে।\n" + str(error), "learned": False})
                return
            local = get_smart_reply(question)
            if local:
                json_response(self, {"reply": local, "learned": False})
                return
            if api_key:
                answer, error = ask_gemini(question, api_key, history, None, "image/jpeg", client_memories)
                if answer:
                    learned = save_memory(question, answer, "auto") if auto_learn else False
                    json_response(self, {"reply": answer, "learned": learned})
                    return
                json_response(self, {"reply": "Gemini থেকে উত্তর পাওয়া যায়নি।\n" + str(error), "learned": False})
                return
            json_response(self, {"reply": "এই প্রশ্নটির উত্তর আমার local knowledge-এ নেই। Teach AI দিয়ে আমাকে শেখাতে পারো অথবা Settings-এ Gemini API key বসাতে পারো।", "learned": False})
            return
        if path == "/api/teach":
            questions = data.get("questions", [])
            answer = str(data.get("answer", "")).strip()
            if isinstance(questions, str):
                questions = [questions]
            count = 0
            for q in questions:
                if str(q).strip() and answer and save_memory(str(q), answer, "teach"):
                    count += 1
            json_response(self, {"ok": True, "count": count})
            return
        if path == "/api/task":
            action = data.get("action")
            if action == "add":
                title = str(data.get("title", "")).strip()
                due = str(data.get("due", "")).strip()
                if title:
                    json_response(self, {"ok": True, "task": add_task(title, due)})
                    return
            elif action == "complete":
                json_response(self, {"ok": complete_task(data.get("id"))})
                return
            elif action == "delete":
                json_response(self, {"ok": delete_task(data.get("id"))})
                return
            json_response(self, {"ok": False, "error": "Invalid task action"}, 400)
            return
        if path == "/api/note":
            action = data.get("action")
            if action == "add":
                text = str(data.get("text", "")).strip()
                title = str(data.get("title", "")).strip()
                if text:
                    json_response(self, {"ok": True, "note": add_note(text, title)})
                    return
            elif action == "delete":
                json_response(self, {"ok": delete_note(data.get("id"))})
                return
            json_response(self, {"ok": False}, 400)
            return
        if path == "/api/sale":
            action = data.get("action")
            if action == "add":
                try:
                    amount = float(data.get("amount", 0))
                    quantity = int(data.get("quantity", 1))
                except Exception:
                    json_response(self, {"ok": False, "error": "Invalid amount"}, 400)
                    return
                if amount <= 0:
                    json_response(self, {"ok": False, "error": "Amount must be greater than zero"}, 400)
                    return
                json_response(self, {"ok": True, "sale": add_sale(amount, str(data.get("item", "")), quantity)})
                return
            json_response(self, {"ok": False}, 400)
            return
        self.send_error(404)

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def start_server():
    server = HTTPServer((HOST, PORT), Handler)
    print("=" * 60)
    print("SHOFIQ AI")
    print("=" * 60)
    print("Version:", VERSION)
    print("Local URL:")
    print("http://127.0.0.1:%s" % PORT)
    ip = get_local_ip()
    print("Network URL:")
    print("http://%s:%s" % (ip, PORT))
    print("=" * 60)
    for name in ["Teach AI", "Memory", "Gemini AI", "Camera Vision", "Voice", "Math", "Tasks", "Reminders", "Notes", "Sales", "Facebook Assistant"]:
        print(name)
    print("=" * 60)
    try:
        webbrowser.open("http://127.0.0.1:%s" % PORT)
    except Exception:
        pass
    server.serve_forever()

if __name__ == "__main__":
    try:
        start_server()
    except KeyboardInterrupt:
        print("\nShofiq AI stopped.")
    except Exception as e:
        print("\nSERVER ERROR:")
        print(str(e))
