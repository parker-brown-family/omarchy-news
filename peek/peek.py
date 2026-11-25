#!/usr/bin/env python3
"""What is being built in Omarchy, read from the code. Standard library and git only.

  python3 peek/peek.py scan [--days 21]      clone or fetch every repository in repos.json and list what landed
  python3 peek/peek.py rank [--cap 0.03]     order the list by how much a person would notice it (optional, needs a key)
  python3 peek/peek.py show [--top 20]       print the list by lane
  python3 peek/peek.py check <edition.json>  read every change an edition names again, at today's code

Nothing here predicts a release. A change is named only after it is in a project's default branch, and `check` measures
how many of the lines it added are still there, because merged work gets taken out again.

No key is needed or kept in this repository. `rank` sends public titles and descriptions to Jev (a TypeSafe model) through
OpenRouter with YOUR key, from the environment variable OPENROUTER_API_KEY. Without it, everything else works and scores
stay null. Clones live in ~/.cache/omarchy-news; set OMARCHY_NEWS_CACHE to move them.
"""
import concurrent.futures as cf, datetime as dt, json, os, re, subprocess, sys, threading, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = Path(os.environ.get("OMARCHY_NEWS_CACHE", Path.home() / ".cache/omarchy-news"))
REPOS = json.loads((HERE / "repos.json").read_text())
OUT = CACHE / "changes.json"
BOT = re.compile(r"\[bot\]|omarchybot|dependabot|renovate", re.I)
CHORE = re.compile(r"^(update translations|bump |pin |release |tests?:|docs?[:/]|acceptance:|backport|merge branch|revert the version)|\b(flaky|lint|typo|changelog|\bCI\b|release notes|unit tests?|shell tests?)\b", re.I)
GONE = re.compile(r"^(revert\b|remove\b|drop\b)", re.I)
arg = lambda n, d: type(d)(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d


def git(repo, *a, check=True):
    r = subprocess.run(["git", "-C", str(CACHE / repo.replace("/", "_")), *a], capture_output=True, text=True, errors="replace")
    if check and r.returncode: raise RuntimeError(f"{repo}: git {a[0]}: {r.stderr.strip()[:200]}")
    return r.stdout


def fetch(repo, days):
    d, since = CACHE / repo.replace("/", "_"), (dt.date.today() - dt.timedelta(days=max(days, 60))).isoformat()
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    base = os.environ.get("OMARCHY_NEWS_REMOTE", "https://github.com/{}.git")     # set to an ssh form if you clone that way
    cmd = ["git", "-C", str(d), "fetch", "-q", "--filter=blob:none", "origin", "+HEAD:refs/heads/peek"] if d.exists() else \
          ["git", "clone", "-q", "--bare", "--single-branch", "--filter=blob:none", f"--shallow-since={since}", base.format(repo), str(d)]
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if r.returncode: raise RuntimeError(f"{repo}: {r.stderr.strip()[:300]}")
    if "refs/heads/peek" not in git(repo, "for-each-ref"): git(repo, "update-ref", "refs/heads/peek", "HEAD")


def landed(R, days):
    """Every change on the default branch in the window, one row per pull request or direct commit."""
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for rec in git(R["repo"], "log", "--first-parent", f"--since={since}", "--format=%H%x1f%cs%x1f%an%x1f%s%x1f%b%x1e", "peek").split("\x1e"):
        if rec.count("\x1f") != 4: continue
        sha, day, who, title, body = rec.strip("\n").split("\x1f")
        pr = re.search(r"\(#(\d+)\)\s*$", title) or re.match(r"Merge pull request #(\d+)", title)
        if title.startswith("Merge pull request"): title = next((l for l in body.splitlines() if l.strip()), title)
        title = re.sub(r"\s*\(#\d+\)\s*$", "", title)
        rows.append({"repo": R["repo"], "lane": R["lane"], "run_by": R["run_by"], "sha": sha, "day": day, "who": who, "title": title,
                     "body": re.sub(r"(?im)^(co-authored-by|signed-off-by):.*$", "", body).strip()[:900], "pr": int(pr.group(1)) if pr else None,
                     "url": f"https://github.com/{R['repo']}/" + (f"pull/{pr.group(1)}" if pr else f"commit/{sha}"),
                     "models_credited": sorted(set(re.findall(r"(?im)^co-authored-by:\s*((?:claude|codex|gemini|opus|gpt|grok|kimi|qwen)[^<\n]*)", body))),
                     "skip": "bot" if BOT.search(who) else "chore" if CHORE.search(title) else "removal" if GONE.match(title) else None, "scores": None})
    return rows


def survival(repo, sha):
    """Of the lines this change added outside tests and translations, how many are still in the same files. null when it added none."""
    added, f = {}, None
    for l in git(repo, "show", "--first-parent", "-m", "--format=", "--no-color", "-M", "--unified=0", sha).splitlines():
        if l.startswith("+++ "): f = l[6:] if l.startswith("+++ b/") else None
        elif l.startswith("+") and f and not re.search(r"(^|/)(tests?|i18n|locale|translations?)/|\.(json|lock|svg|md|po|ts)$", f):
            s = l[1:].strip()
            if len(s) > 12 and not s.startswith(("#", "//", "*", "--")): added.setdefault(f, []).append(s)
    if not added: return {"added": 0, "still": None, "share": None, "files": 0, "files_gone": None}
    n = still = gone = 0
    for path, lines in added.items():
        now = git(repo, "show", f"peek:{path}", check=False)
        if not now: gone += 1
        have = {x.strip() for x in now.splitlines()}
        n += len(lines); still += sum(x in have for x in lines)
    return {"added": n, "still": still, "share": round(still / n, 3), "files": len(added), "files_gone": gone}


def scan():
    days, rows, failed = arg("--days", 21), [], {}
    CACHE.mkdir(parents=True, exist_ok=True)
    def one(R):
        fetch(R["repo"], days); return landed(R, days)
    with cf.ThreadPoolExecutor(4) as ex:
        for R, fu in [(R, ex.submit(one, R)) for R in REPOS]:
            try: rows += fu.result()
            except Exception as e: failed[R["repo"]] = str(e)       # a repository we could not read is named, never counted as quiet
    OUT.write_text(json.dumps({"read": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "days": days, "failed": failed, "changes": rows}, indent=1, ensure_ascii=False))
    for R in REPOS:
        m = [r for r in rows if r["repo"] == R["repo"]]
        print(f"{R['repo']:32} " + ("COULD NOT READ " + failed[R["repo"]] if R["repo"] in failed else f"{len(m):4} landed, {sum(not r['skip'] for r in m):4} to read, {sum(r['skip'] == 'removal' for r in m):3} removals"))
    return 1 if failed else 0


Q = {
 "noticed": {"type": "score", "instructions": "Someone uses this software every day and never reads its code. How much would they notice the change that `title` and `body` describe?",
   "criteria": ["they would not notice it: a refactor, a test, a build step, a rare fix or a change for one hardware model", "they would notice a small improvement to something they already do", "they would notice something new they can do, or something they do every day becoming clearly different"]},
 "delight": {"type": "score", "instructions": "If that person saw the change in `title` and `body` demonstrated for ten seconds, what would it look like to them?",
   "criteria": ["nothing to see, or a correction of something that was broken", "useful and plain", "striking, playful, beautiful or surprisingly fast"]},
 "explains": {"type": "noul", "instructions": "`title` and `body` together say what a person can now do or see, in enough detail to explain it to someone who has never used this software."},
}


def ask(state, key):
    """One batched call to Jev. A failure comes back as None, never as a score."""
    q = {k: dict(v) for k, v in Q.items()}
    req = urllib.request.Request("https://openrouter.ai/api/v1/systemone", data=json.dumps({"model": "jev-latest", "state": state, "questions": q}).encode(),
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r: return json.loads(r.read())
    except Exception as e: return {"error": type(e).__name__}


def rank():
    key, cap, D = os.environ.get("OPENROUTER_API_KEY"), arg("--cap", .03), json.loads(OUT.read_text())
    todo = [r for r in D["changes"] if not r["skip"] and r["scores"] is None]
    if not key: print(f"OPENROUTER_API_KEY is not set: {len(todo)} changes stay unscored, and `show` lists them newest first"); return 0
    lock, spent, calls, unpriced, errors = threading.Lock(), [0.0], [0], [0], {}
    def one(r):
        with lock:
            if spent[0] >= cap: errors["cap"] = errors.get("cap", 0) + 1; return
        p = ask({"project": r["repo"].split("/")[1], "title": r["title"][:200], "body": r["body"][:600] or "(no description)"}, key)
        c, a = (p.get("usage") or {}).get("cost"), p.get("answers") or {}
        with lock:
            calls[0] += 1
            if c is None: unpriced[0] += 1; c = .0001        # a call with no price is charged high, never zero
            spent[0] += c
            if p.get("error"): errors[p["error"]] = errors.get(p["error"], 0) + 1
        v = {k: a.get(k, {}).get("score" if Q[k]["type"] == "score" else "noul") for k in Q}
        if all(x is not None for x in v.values()): r["scores"] = v
    with cf.ThreadPoolExecutor(12) as ex: list(ex.map(one, todo))
    got = [r for r in todo if r["scores"]]
    D["rank"] = {"asked": calls[0], "answered": len(got), "usd": round(spent[0], 5), "calls_without_a_price": unpriced[0], "not_answered": errors}
    OUT.write_text(json.dumps(D, indent=1, ensure_ascii=False))
    print(D["rank"])
    return 0


def weight(r):
    s = r["scores"]
    return None if s is None else round((s["noticed"] + s["delight"]) * (.4 + .6 * s["explains"]), 3)


def show():
    top, D = arg("--top", 20), json.loads(OUT.read_text())
    print(f"read {D['read']}, {D['days']} days. Not read: {D['failed'] or 'none'}")
    for lane in dict.fromkeys(R["lane"] for R in REPOS):
        rows = [r for r in D["changes"] if r["lane"] == lane and not r["skip"]]
        rows.sort(key=lambda r: (weight(r) is not None, weight(r) or 0, r["day"]), reverse=True)
        print(f"\n## {lane}: {len(rows)} changes, {sum(r['scores'] is None for r in rows)} unscored")
        for r in rows[:top]: print(f"{'  - ' if weight(r) is None else format(weight(r), '4.2f')} {r['day']} {r['repo'].split('/')[1]} {('#' + str(r['pr'])) if r['pr'] else r['sha'][:9]} {r['who']} | {r['title'][:110]}")
    print("\n## taken out again, or said to be")
    for r in D["changes"]:
        if r["skip"] == "removal": print(f"     {r['day']} {r['repo'].split('/')[1]} {('#' + str(r['pr'])) if r['pr'] else r['sha'][:9]} | {r['title'][:110]}")
    return 0


def check():
    """Every change an edition names, read again now. Fails when one is missing or most of its lines have gone,
    or when a control (work we know was taken out) does not read as gone."""
    p = Path(sys.argv[2]); E, bad = json.loads(p.read_text()), 0
    for R in {i["repo"] for i in E["items"]}: fetch(R, 60)
    for i in E["items"]:
        try:
            on = subprocess.run(["git", "-C", str(CACHE / i["repo"].replace("/", "_")), "merge-base", "--is-ancestor", i["sha"], "peek"]).returncode == 0
            s = survival(i["repo"], i["sha"]) if on else None
        except RuntimeError as e: on, s = None, None; print(e)
        i["checked"] = {"on": dt.date.today().isoformat(), "head": git(i["repo"], "rev-parse", "peek").strip()[:12], "in_default_branch": on, "lines": s}
        ok = on is True and (s["share"] is None or s["share"] >= E.get("least_share", .6) or bool(i.get("read_by_hand")))
        if i.get("expect") == "gone": ok = on is True and s["share"] is not None and s["share"] < E.get("least_share", .6)     # a control: work known to be gone must read as gone
        bad += not ok
        print(("gone" if i.get("expect") == "gone" else "ok  ") if ok else "READ", i["repo"], i["pr"] or i["sha"][:9], "in" if on else "NOT IN" if on is False else "could not tell", "lines", s, "|", i["says"][:70])
    p.write_text(json.dumps(E, indent=1, ensure_ascii=False) + "\n")
    return 1 if bad else 0


if __name__ == "__main__":
    cmds = {"scan": scan, "rank": rank, "show": show, "check": check}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds: sys.exit(__doc__)
    sys.exit(cmds[sys.argv[1]]())
