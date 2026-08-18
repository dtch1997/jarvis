from __future__ import annotations
import datetime as dt, os, subprocess
from pathlib import Path
from . import config
from .http import request

API="https://slack.com/api/"
def _call(method, **params):
    token=os.environ["SLACK_MAILROOM_TOKEN"]
    result=request(API+method, token=token, method="POST", data=params, slack=True)
    if not result.get("ok"): raise RuntimeError(f"Slack {method}: {result.get('error')}")
    return result

def history(channel: str, oldest: float) -> list[dict]:
    out=[]; cursor=None
    while True:
        p={"channel":channel,"oldest":str(oldest),"limit":200,"inclusive":True}
        if cursor: p["cursor"]=cursor
        r=_call("conversations.history", **p); out += r.get("messages", [])
        cursor=r.get("response_metadata",{}).get("next_cursor")
        if not cursor: break
    # Thread replies are not returned by history.
    top=list(out)
    for m in top:
        if m.get("reply_count"):
            replies=_call("conversations.replies", channel=channel, ts=m["ts"], limit=200).get("messages",[])
            out += replies[1:]
    return [m for m in out if m.get("user")==config.DANIEL_USER_ID and not m.get("bot_id")]

def react(channel: str, ts: str) -> None:
    try: _call("reactions.add", channel=channel, timestamp=ts, name="white_check_mark")
    except RuntimeError as e:
        if "already_reacted" not in str(e): raise

def reply(channel: str, thread_ts: str, text: str) -> None:
    _call("chat.postMessage", channel=channel, thread_ts=thread_ts, text=text)

def permalink(channel: str, ts: str) -> str:
    try: return _call("chat.getPermalink", channel=channel, message_ts=ts)["permalink"]
    except Exception: return f"slack://{channel}/{ts}"

def download_audio(file: dict, id_: str) -> tuple[str,str,str|None]:
    ext=Path(file.get("name", "audio.m4a")).suffix or ".m4a"
    original=config.audio_dir()/f"{id_}{ext}"; wav=config.audio_dir()/f"{id_}.wav"
    token=os.environ["SLACK_MAILROOM_TOKEN"]
    import urllib.request
    req=urllib.request.Request(file["url_private_download"],headers={"Authorization":f"Bearer {token}"})
    with urllib.request.urlopen(req,timeout=120) as r: original.write_bytes(r.read())
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i",str(original),"-ar","16000","-ac","1",str(wav)],check=True)
    from .transcribe import transcribe
    transcript=transcribe(wav)
    target=f"gcs:alignment-team-general-storage/daniel/jarvis/mailroom/audio/{original.name}"
    subprocess.run(["rclone","copyto",str(original),target],check=True)
    auto=file.get("transcription",{}).get("transcript") or file.get("transcription_text")
    return transcript, "gs://alignment-team-general-storage/daniel/jarvis/mailroom/audio/"+original.name, auto

def iso(ts: str) -> str: return dt.datetime.fromtimestamp(float(ts),dt.timezone.utc).isoformat()
