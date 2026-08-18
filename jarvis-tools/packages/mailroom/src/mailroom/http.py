from __future__ import annotations
import json, time, urllib.error, urllib.parse, urllib.request

def request(url: str, *, token: str, method="GET", data=None, params=None, slack=False, retries=6):
    if params: url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    headers={"Authorization": f"Bearer {token}"}
    if data is None:
        body = None
    elif slack:
        # Slack Web API is happiest with form-encoding (JSON bodies reject some
        # scalar fields like conversations.replies' `ts` as invalid_arguments).
        form = {k: ("true" if v is True else "false" if v is False else v)
                for k, v in data.items() if v is not None}
        body = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    else:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                payload = r.read()
            return json.loads(payload) if payload else {}
        except urllib.error.HTTPError as e:
            # Honor Retry-After on 429/503; back off on transient 5xx.
            if e.code in (429, 500, 502, 503) and attempt < retries:
                wait = float(e.headers.get("Retry-After") or 0) or min(2 ** attempt, 30)
                time.sleep(wait + 0.5)
                continue
            raise
