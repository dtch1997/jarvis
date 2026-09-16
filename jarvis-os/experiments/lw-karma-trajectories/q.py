import json, sys, urllib.request
def gql(q, v=None):
    req = urllib.request.Request("https://www.lesswrong.com/graphql",
        data=json.dumps({"query": q, "variables": v or {}}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "jarvis-research/0.1 (dtch009@gmail.com)"})
    return json.load(urllib.request.urlopen(req, timeout=60))
if __name__ == "__main__":
    print(json.dumps(gql(sys.stdin.read()), indent=1))
