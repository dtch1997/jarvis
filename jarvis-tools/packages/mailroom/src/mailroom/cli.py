from __future__ import annotations
import argparse,json,subprocess,sys,time
def main(argv=None):
    p=argparse.ArgumentParser(prog="mailroom"); sub=p.add_subparsers(dest="cmd",required=True)
    for name in ("ingest","route"):
        q=sub.add_parser(name);q.add_argument("--check",action="store_true")
        if name=="route":q.add_argument("--max-calls",type=int)
    rn=sub.add_parser("render");rn.add_argument("--stale",action="store_true");sub.add_parser("status");sv=sub.add_parser("serve");sv.add_argument("--port",type=int);sv.add_argument("--no-tunnel",action="store_true")
    a=p.parse_args(argv)
    if a.cmd=="ingest":
        from .ingest import ingest,check
        if a.check: ok,msg=check();print(msg);return 0 if ok else 1
        print(json.dumps(ingest(),indent=2));return 0
    if a.cmd=="route":
        from .route import route,check
        if a.check:ok,msg=check();print(msg);return 0 if ok else 1
        print(json.dumps(route(a.max_calls),indent=2));return 0
    if a.cmd=="render":
        from .dashboard import render_markdown
        text=render_markdown(stale=a.stale);print(text)
        if text.count("\n-"):
            subprocess.run(["flare","mailroom digest: new activity — see /a/mailroom/","--sev","info"],check=False)
        return 0
    if a.cmd=="status":
        from .ingest import check as ic
        from .route import check as rc
        print(ic()[1]);print(rc()[1]);return 0
    from .server import serve
    s=serve(a.port,not a.no_tunnel);print(f"local: {s.local_url}",flush=True);print(f"PUBLIC: {s.url}",flush=True)
    try:
        while True:time.sleep(1)
    except KeyboardInterrupt:s.stop()
    return 0
if __name__=="__main__":sys.exit(main())
