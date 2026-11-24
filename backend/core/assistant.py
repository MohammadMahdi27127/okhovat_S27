import json
import os
from datetime import timedelta
from urllib import error, request as http

CHOICES = {"kind": ["stats", "guide", "greeting", "unsupported"],
           "scope": ["self", "ring", "peers"],
           "period": ["week", "previous", "today", "yesterday", "compare"]}


def valid(plan):
    return isinstance(plan, dict) and all(plan.get(k) in choices for k, choices in CHOICES.items())


def interpret(message, fallback):
    model = os.getenv("ASSISTANT_OLLAMA_MODEL", "")
    if not model or fallback["kind"] == "unsupported":
        return fallback
    schema = {"type": "object", "required": list(CHOICES), "properties": {
        key: {"type": "string", "enum": values} for key, values in CHOICES.items()}}
    instruction = ("Classify this Persian Okhovat question, including colloquial wording. "
                   "stats means growth reports, exercise, reading or participation. "
                   "Use peers for other members excluding the speaker, ring for the whole own ring. "
                   "Default to self and current week. compare means equivalent week-to-date periods. "
                   "Use guide for site directions, greeting for small talk and unsupported for "
                   "other time ranges, other rings, named individuals or unrelated tasks.")
    payload = {"model": model, "stream": False, "format": schema, "options": {"temperature": 0},
               "messages": [{"role": "system", "content": instruction}, {"role": "user", "content": message}]}
    url = os.getenv("ASSISTANT_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/") + "/api/chat"
    try:
        req = http.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        with http.urlopen(req, timeout=5) as response:
            raw=response.read(65537)
            if len(raw)>65536:
                return fallback
            result = json.loads(json.loads(raw)["message"]["content"])
        return result if valid(result) else fallback
    except (error.URLError, TimeoutError, OSError, ValueError, TypeError, KeyError, RecursionError):
        return fallback


def periods(period, today):
    one = timedelta(days=1)
    saturday = today - (today.weekday() + 2) % 7 * one
    week = 7 * one
    if period == "previous":
        return [(saturday-week, saturday-one)]
    if period in ("today", "yesterday"):
        day = today if period == "today" else today-one
        return [(day, day)]
    result = [(saturday, today)]
    if period == "compare":
        result.append((saturday-week, today-week))
    return result


