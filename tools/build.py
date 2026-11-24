/bin/env python3
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
    return {
        "version": "https://jsonfeed.org/version/1.1",
        "title": I["title"], "home_page_url": REPO, "feed_url": f"{RAW}/feed.json",
        "description": I["description"], "items": items
    }


def render_readme(S, T, V, I):
    lines = [
        f"# {I['title']}",
        "",
        I["description"],
        "",
        "## Stories",
        ""
    ]
    for s in S:
        lines.append(f"- [{s['title']}](stories/{s['id']}.json) ({s['date']})")
    lines.append("")
    lines.append("## Topics")
    lines.append("")
    for t in T:
        lines.append(f"- **{t['name']}**: {t['description']}")
    lines.append("")
    return "\n".join(lines)


def main():
    S = stories()
    meta = load("meta.json")
    T = meta["topics"]
    V = load("videos.json")
    I = meta["info"]

    errs = problems(S, T, V)
    if errs:
        for e in errs:
            print(e, file=sys.stderr)
        sys.exit(1)

    new_feed = feed(S, T, V, I)
    new_readme = render_readme(S, T, V, I)

    if "--check" in sys.argv:
        current_feed = json.loads((R / "feed.json").read_text()) if (R / "feed.json").exists() else None
        current_readme = (R / "README.md").read_text() if (R / "README.md").exists() else None

        if current_feed != new_feed or current_readme != new_readme:
            print("feed.json or README.md is out of date. Run python3 tools/build.py", file=sys.stderr)
            sys.exit(1)
        print("Everything is up to date.")
    else:
        (R / "feed.json").write_text(json.dumps(new_feed, indent=2) + "\n")
        (R / "README.md").write_text(new_readme)
        print("Wrote feed.json and README.md")


if __name__ == "__main__":
    main()