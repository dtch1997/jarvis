"""Smoke tests for the jarvis2 pod reaper, against a stub RunPod — no real pods.

The real CLI runs as a subprocess on a throwaway copy of the jarvis2 tree. A
local HTTP server stands in for RunPod REST v2 (paginated GET /pods, DELETE
/pods/{id}) and, like the real API, 403s python-urllib's default User-Agent.
`flare` and `claude` are fakes on PATH; flares land in a JSONL file.

    python3 jarvis2/tests/test_pod_reaper.py      # or: pytest jarvis2/tests
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

CLI = Path(__file__).resolve().parent.parent / "bin" / "jarvis"
SLUG = "sdf-probe"


def pod(pid, name, status="RUNNING", cost=1.0, gpu=None):
    return {"id": pid, "name": name, "status": status, "cost": cost, "gpu": gpu}


class StubRunpod:
    """Just enough RunPod REST v2 for the reaper, recording every request."""

    def __init__(self, pods):
        self.pods = list(pods)
        self.requests = []   # (method, path, user_agent, authorization)
        self.fail = None     # HTTP status to answer everything with
        self.fail_delete = None
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def reply(self, code, body=None):
                data = json.dumps(body).encode() if body is not None else b""
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def gate(self):
                ua = self.headers.get("User-Agent", "")
                stub.requests.append((self.command, self.path, ua,
                                      self.headers.get("Authorization")))
                if ua.startswith("Python-urllib"):
                    return self.reply(403, {"title": "Forbidden"}) or True
                if stub.fail:
                    return self.reply(stub.fail, {"title": "boom"}) or True
                return False

            def do_GET(self):
                if self.gate():
                    return
                url = urlsplit(self.path)
                if url.path != "/pods":
                    return self.reply(404, {"detail": "The requested path was not found."})
                start = int(parse_qs(url.query).get("cursor", ["0"])[0])
                page = stub.pods[start:start + 2]  # tiny pages: exercise the cursor loop
                nxt = str(start + 2) if start + 2 < len(stub.pods) else None
                self.reply(200, {"pods": page,
                                 "pagination": {"hasNextPage": bool(nxt), "nextCursor": nxt}})

            def do_DELETE(self):
                if self.gate():
                    return
                if stub.fail_delete:
                    return self.reply(stub.fail_delete, {"title": "boom"})
                pid = self.path.rsplit("/", 1)[-1]
                if not any(p["id"] == pid for p in stub.pods):
                    return self.reply(404, {"detail": "pod not found"})
                stub.pods = [p for p in stub.pods if p["id"] != pid]
                self.reply(204)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def calls(self, method=None):
        return [(m, p) for m, p, _, _ in self.requests if method in (None, m)]


class ReaperTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jarvis2-reaper-"))
        root = self.tmp / "jarvis2"
        (root / "bin").mkdir(parents=True)
        shutil.copy(CLI, root / "bin" / "jarvis")
        self.cli = root / "bin" / "jarvis"
        self.projects = root / "projects"
        self.projects.mkdir()
        fake = self.tmp / "fakebin"
        fake.mkdir()
        self.flare_log = self.tmp / "flares.jsonl"
        (fake / "flare").write_text(
            f"#!{sys.executable}\nimport json, os, sys\n"
            "with open(os.environ['FLARE_LOG'], 'a') as f:\n"
            "    f.write(json.dumps(sys.argv[1:]) + '\\n')\n")
        (fake / "claude").write_text(
            "#!/bin/sh\necho '{\"total_cost_usd\": 0.01, \"result\": \"ok\", \"is_error\": false}'\n")
        for f in fake.iterdir():
            f.chmod(0o755)
        self.stub = StubRunpod([
            pod("aaa111", "bellhop-sdf-probe-train", cost=15.96,
                gpu={"count": 4, "id": "NVIDIA H200"}),
            pod("bbb222", "bellhop-sdf-probe-eval", cost=2.0),
            pod("ccc333", "bellhop-sdf-probe-v2-sweep", cost=3.0),  # sibling project's
            pod("ddd444", "sdf-probe-old", status="EXITED", cost=3.49),
            pod("eee555", "foyer-relay", cost=0.03),
        ])
        self.env = {k: v for k, v in os.environ.items()
                    if k not in ("RUNPOD_API_KEY", "JARVIS2_TICK_ID")}
        self.env.update(JARVIS2_RUNPOD_API=self.stub.url, RUNPOD_API_KEY="test-key",
                        FLARE_LOG=str(self.flare_log),
                        PATH=f"{fake}{os.pathsep}{os.environ.get('PATH', '')}")
        self.make_project(SLUG)
        self.make_project("sdf-probe-v2", status="paused")  # never ticks under a bare `jarvis tick`

    def tearDown(self):
        self.stub.server.shutdown()
        self.stub.server.server_close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---------------------------------------------------------------- helpers

    def make_project(self, slug, status="active", mode="research", usd=20.0,
                     hours=None, log=()):
        pdir = self.projects / slug
        pdir.mkdir()
        toml = f'slug = "{slug}"\n'
        if mode == "explore":
            toml += 'mode = "explore"\n'
        toml += f"[budget]\nusd = {usd}\n" + (f"hours = {hours}\n" if hours else "")
        (pdir / "project.toml").write_text(toml)
        self.write_state(slug, {"status": status, "status_reason": "", "ticks": 1,
                                "last_tick_start": None, "last_tick_id": None})
        (pdir / "log.jsonl").write_text("".join(json.dumps(e) + "\n" for e in log))
        return pdir

    def state(self, slug=SLUG):
        return json.loads((self.projects / slug / "state.json").read_text())

    def write_state(self, slug, st):
        (self.projects / slug / "state.json").write_text(json.dumps(st))

    def log(self, slug=SLUG, event=None):
        lines = (self.projects / slug / "log.jsonl").read_text().splitlines()
        return [e for e in map(json.loads, lines) if event in (None, e["event"])]

    def flares(self, sev=None):
        if not self.flare_log.exists():
            return []
        out = []
        for line in self.flare_log.read_text().splitlines():
            argv = json.loads(line)
            s = argv[argv.index("--sev") + 1] if "--sev" in argv else "info"
            if sev in (None, s):
                out.append((s, argv[0]))
        return out

    def jarvis(self, *args, env=None):
        proc = subprocess.run([sys.executable, str(self.cli), *args], env=env or self.env,
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, f"jarvis {args} failed:\n{proc.stderr}")
        return proc

    def backdate_reap(self, slug=SLUG):
        st = self.state(slug)
        st["reap_due"] = (datetime.now().astimezone() - timedelta(minutes=1)).isoformat()
        self.write_state(slug, st)

    # ------------------------------------------------------------------ tests

    def test_blocked_pages_held_pods_then_sweep_terminates_released_after_grace(self):
        self.jarvis("persisted", SLUG, "bbb222", "--note", "gs://bucket/sdf-probe/eval")
        self.assertEqual(self.stub.requests, [], "persisted must not call RunPod")

        self.jarvis("outcome", SLUG, "blocked", "--note", "need an HF token")
        self.assertEqual(self.stub.calls("DELETE"), [], "nothing terminates at the transition")
        reap = self.log(event="pods_reaped")[-1]
        self.assertEqual(reap["trigger"], "blocked")
        self.assertEqual(sorted(reap["live"]), ["aaa111", "bbb222"])  # not the sibling's, not EXITED
        self.assertEqual(reap["paged"], ["aaa111"])
        self.assertEqual(reap["scheduled"], ["bbb222"])
        self.assertEqual(reap["usd_per_hr"], 17.96)
        self.assertEqual(self.state()["reap_due"], reap["reap_due"])
        pages = self.flares("page")
        self.assertEqual(len(pages), 1)
        self.assertIn("aaa111", pages[0][1])
        self.assertIn("$15.96/hr", pages[0][1])
        self.assertNotIn("ccc333", pages[0][1])
        self.assertTrue(all(ua.startswith("curl/") and auth == "Bearer test-key"
                            for _, _, ua, auth in self.stub.requests))
        self.assertIn("pod reaper: released pods terminate after",
                      self.jarvis("status", SLUG).stdout)

        n = len(self.stub.requests)
        self.jarvis("tick")  # inside the grace: the sweep does not even call RunPod
        self.assertEqual(len(self.stub.requests), n)

        self.backdate_reap()
        self.jarvis("tick")
        self.assertEqual(self.stub.calls("DELETE"), [("DELETE", "/pods/bbb222")])
        self.assertEqual({p["id"] for p in self.stub.pods},
                         {"aaa111", "ccc333", "ddd444", "eee555"})
        swept = self.log(event="pods_reaped")[-1]
        self.assertEqual((swept["trigger"], swept["terminated"]), ("grace expired", ["bbb222"]))
        self.assertNotIn("reap_due", self.state())
        self.assertTrue(any("bbb222" in m for s, m in self.flares("info")))

        n = len(self.stub.requests)
        self.jarvis("tick")
        self.assertEqual(len(self.stub.requests), n, "a finished reap does not re-poll")

    def test_resume_inside_grace_cancels_the_reap(self):
        self.jarvis("persisted", SLUG, "bbb222", "--note", "no unique state")
        self.jarvis("pause", SLUG)
        self.assertIn("reap_due", self.state())
        self.jarvis("resume", SLUG)
        self.assertNotIn("reap_due", self.state())
        self.jarvis("tick")
        self.assertEqual(self.stub.calls("DELETE"), [])

    def test_sweep_spares_a_project_resumed_by_other_means(self):
        self.jarvis("persisted", SLUG, "bbb222", "--note", "no unique state")
        self.jarvis("pause", SLUG)
        self.backdate_reap()
        st = self.state()
        st["status"] = "active"  # e.g. an older CLI resumed it without clearing reap_due
        st["last_tick_start"] = datetime.now().astimezone().isoformat()  # not due a tick
        self.write_state(SLUG, st)
        self.jarvis("tick")
        self.assertEqual(self.stub.calls("DELETE"), [])
        self.assertNotIn("reap_due", self.state())

    def test_runpod_failures_never_break_the_command(self):
        self.stub.fail = 500
        self.jarvis("pause", SLUG)
        self.assertEqual(self.state()["status"], "paused")
        self.assertIn("error", self.log(event="pods_reaped")[-1])
        self.assertTrue(any("could not check RunPod" in m for _, m in self.flares("warn")))

        env = {k: v for k, v in self.env.items() if k != "RUNPOD_API_KEY"}
        self.jarvis("drop", SLUG, env=env)
        self.assertEqual(self.state()["status"], "dropped")
        self.assertTrue(any("RUNPOD_API_KEY" in m for _, m in self.flares("warn")))

        env = {**self.env, "JARVIS2_RUNPOD_API": "http://127.0.0.1:9"}  # nothing listens
        self.jarvis("outcome", "sdf-probe-v2", "blocked", "--note", "x", env=env)
        self.assertEqual(self.state("sdf-probe-v2")["status"], "blocked")

    def test_failed_sweep_keeps_the_reap_for_the_next_tick(self):
        self.jarvis("persisted", SLUG, "bbb222", "--note", "no unique state")
        self.jarvis("pause", SLUG)
        self.backdate_reap()
        self.stub.fail = 503
        self.jarvis("tick")
        self.assertIn("reap_due", self.state())
        self.stub.fail, self.stub.fail_delete = None, 500
        self.jarvis("tick")
        self.assertIn("reap_due", self.state())
        self.assertEqual(self.log(event="pods_reaped")[-1]["failed"], ["bbb222"])
        self.assertTrue(any("could not terminate" in m and "bbb222" in m
                            for _, m in self.flares("warn")))
        self.stub.fail_delete = None
        self.jarvis("tick")
        self.assertNotIn("reap_due", self.state())
        self.assertNotIn("bbb222", {p["id"] for p in self.stub.pods})

    def test_already_terminated_pod_counts_as_reaped(self):
        self.jarvis("persisted", SLUG, "bbb222", "--note", "no unique state")
        self.jarvis("drop", SLUG)
        self.backdate_reap()
        self.stub.pods = [p for p in self.stub.pods if p["id"] != "bbb222"]  # gone by hand
        self.jarvis("tick")
        self.assertEqual(self.stub.calls("DELETE"), [])
        self.assertNotIn("reap_due", self.state())

    def test_persisted_on_a_stopped_project_starts_the_grace(self):
        st = self.state()
        st["status"] = "blocked"
        self.write_state(SLUG, st)
        out = self.jarvis("persisted", SLUG, "bbb222", "aaa111", "--note", "gs://x").stdout
        self.assertIn("is blocked", out)
        self.assertIn("reap_due", self.state())
        self.assertEqual(len(self.log(event="pod_persisted")), 2)
        self.backdate_reap()
        self.jarvis("tick")
        self.assertEqual(sorted(self.stub.calls("DELETE")),
                         [("DELETE", "/pods/aaa111"), ("DELETE", "/pods/bbb222")])

    def test_explore_soft_block_leaves_pods_alone_until_it_sticks(self):
        shutil.rmtree(self.projects / SLUG)
        self.make_project(SLUG, mode="explore", log=[
            {"event": "outcome", "tick": "t1", "outcome": "progress", "note": ""}])
        self.jarvis("outcome", SLUG, "blocked", "--note", "HF down?")
        self.assertEqual(self.stub.requests, [])
        self.assertEqual(self.log(event="pods_reaped"), [])
        self.jarvis("outcome", SLUG, "blocked", "--note", "HF down, confirmed")
        self.assertEqual(self.log(event="pods_reaped")[-1]["paged"], ["aaa111", "bbb222"])

    def test_budget_exhaustion_reaps(self):
        shutil.rmtree(self.projects / SLUG)
        self.make_project(SLUG, log=[{"event": "tick_end", "cost_usd": 25.0}])
        self.jarvis("tick", SLUG)
        self.assertEqual(self.state()["status"], "blocked")
        self.assertEqual(self.log(event="pods_reaped")[-1]["trigger"], "budget exhausted")
        self.assertEqual(len(self.flares("page")), 1)

    def test_finish_exploration_reaps(self):
        shutil.rmtree(self.projects / SLUG)
        self.make_project(SLUG, mode="explore", hours=0.5,
                          log=[{"event": "wave_end", "wall_s": 3600}])
        self.jarvis("tick", SLUG)
        self.assertEqual(self.state()["status"], "done")
        self.assertEqual(self.log(event="pods_reaped")[-1]["trigger"], "hours delivered")

    def test_research_done_reaps_and_no_pods_means_no_flare(self):
        self.stub.pods = [p for p in self.stub.pods if SLUG not in p["name"]]
        self.jarvis("outcome", SLUG, "done", "--note", "report written")
        reap = self.log(event="pods_reaped")[-1]
        self.assertEqual((reap["trigger"], reap["live"]), ("done", []))
        self.assertEqual(self.flares("page"), [])
        self.assertFalse(any("live pod" in m for _, m in self.flares()))


if __name__ == "__main__":
    unittest.main()
