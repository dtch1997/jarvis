import json, datetime as dt, time
from q import gql
FIELDS = """_id title slug postedAt createdAt baseScore maxBaseScore voteCount commentCount wordCount
 af afBaseScore frontpageDate curatedDate isEvent shortform question draft userId
 scoreExceeded2Date scoreExceeded30Date scoreExceeded45Date scoreExceeded75Date scoreExceeded125Date scoreExceeded200Date"""
start = dt.date(2023, 8, 15); end = dt.date(2026, 8, 14)
out = open("posts.jsonl", "w"); n = 0
d = start
while d < end:
    e = min(d + dt.timedelta(days=14), end)
    for attempt in range(4):
        try:
            r = gql('{ posts(input: {terms: {view: "new", limit: 1000, after: "%s", before: "%s"}}) { results { %s } } }' % (d, e, FIELDS))
            res = r["data"]["posts"]["results"]; break
        except Exception as ex:
            print("retry", d, ex); time.sleep(5 * (attempt + 1))
    for p in res: out.write(json.dumps(p) + "\n")
    n += len(res); print(d, len(res), n, flush=True)
    d = e; time.sleep(0.5)
out.close()
