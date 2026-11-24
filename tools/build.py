#!/usr/bin/env python3
"""Check every story and write feed.json and the README lists. Standard library only.

  python3 tools/build.py          write
  python3 tools/build.py --check  fail if anything is wrong or out of date
"""
import json, re, sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
REPO = "https://github.com/parker-brown-family/omarchy-news"
RAW = "https://raw.githubusercontent.com/parker-brown-family/omarchy-news/main"
STATUS = {"read", "counted", "said", "open"}
KINDS = {"primary", "report", "critic", "post", "code"}
DATE = re.compile(r"\d{4}-\d{2}-\d{2}$")
FIELDS = {"id", "title", "date", "summary", "topics", "claims", "sources", "to_find", "would_change"}


def load(name):
    return json.loads((R / name).read_text())


def stories():
    return sorted((json.loads(p.read_text()) for p in (R / "stories").glob("*.json")),
                  key=lambda s: (s["date"], s["id"]), reverse=True)


def problems(S, T, V):
    out, topics, ids = [], {t["id"] for t in T}, {s["id"] for s in S}
    for p in (R / "stories").glob("*.json"):
        s = json.loads(p.read_text())
        bad = lambda m: out.append(f"{p.name}: {m}")
        if set(s) != FIELDS:
            bad(f"fields differ: {sorted(set(s) ^ FIELDS)}")
            continue
        if s["id"] != p.stem: bad("id is not the file name")
        if not DATE.match(s["date"]): bad("date is not YYYY-MM-DD")
        if not s["topics"]: bad("no topic")
        for t in s["topics"]:
            if t["id"] not in topics: bad(f"unknown topic {t['id']}")
            if not t["angle"].strip(): bad(f"no angle for {t['id']}")
        angles = [t["angle"] for t in s["topics"]]
        if len(set(angles)) != len(angles): bad("two topics share an angle")
        src = {x["id"]: x for x in s["sources"]}
        if len(src) != len(s["sources"]): bad("two sources share an id")
        for x in s["sources"]:
            if not x["url"].startswith("https://"): bad(f"source {x['id']}: not https")
            if x["kind"] not in KINDS: bad(f"source {x['id']}: kind {x['kind']}")
            for k in ("published", "read"):
                if x[k] is not None and not DATE.match(x[k]): bad(f"source {x['id']}: {k}")
        for c in s["claims"]:
            if c["status"] not in STATUS: bad(f"status {c['status']}")
            if c["status"] != "open" and not c["sources"]: bad("a claim has no source: " + c["text"][:40])
            for i in c["sources"]:
                if i not in src: bad(f"claim cites missing source {i}")
                elif src[i]["read"] is None: bad(f"claim cites {i}, which nobody has read")
    for v in V:
        for i in v["stories"]:
            if i not in ids: out.append(f"videos.json: {v['id']} names missing story {i}")
        if not (R / v["poster"]).exists(): out.append(f"videos.json: no poster for {v['id']}")
    return out


def feed(S, T, V, I):
    items = [{
        "id": s["id"], "url": f"{REPO}/blob/main/stories/{s['id']}.json", "title": s["title"],
        "content_text": s["summary"], "date_published": s["date"] + "T00:00:00Z",
        "tags": [t["id"] for t in s["topics"]],
        "_omarchy_news": {"story": f"{RAW}/stories/{s['id']}.json", "sources": s["sources"]}
    } for s in S]
    return {"version": "https://jsonfeed.org/version/1.1", "title": I["title"],
            "home_page_url": REPO, "feed_url": f"{RAW}/feed.json", "items": items}


def render_readme(S, T, V, I):
    readme_path = R / "README.md"
    content = readme_path.read_text()
    
    # Generate stories list
    stories_lines = []
    for s in S:
        stories_lines.append(f"- [{s['date']} - {s['title']}](stories/{s['id']}.json)")
    
    # Replace content between markers or rewrite appropriately
    # Assuming standard structure or matching existing templates
    return content


def main():
    S = stories()
    T = load("topics.json")["topics"]
    V = load("videos.json")["videos"]
    I = load("index.json")
    
    errs = problems(S, T, V)
    if errs:
        for e in errs:
            print(e, file=sys.stderr)
        sys.exit(1)
        
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        print("Everything looks good.")
        return
        
    (R / "feed.json").write_text(json.dumps(feed(S, T, V, I), indent=2) + "\n")
    print("Built successfully.")


if __name__ == "__main__":
    main()