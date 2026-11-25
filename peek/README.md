# Peek Behind the Curtain: how we find what is being built

Every Wednesday we read what landed in Omarchy's code, and in the independent projects around it, and pick what a person would enjoy hearing about. This folder is the whole method. You can run it yourself.

It is not a forecast. A change counts only once it is in a project's default branch, and even then it can be taken out again: on 21 November a panel for local models merged, on 23 November it was removed, and on 24 November we posted a film that still showed it. So the last step, before any film, reads every change again at that day's code and measures how much of it is still there.

## Run it

Python 3.10 or newer and git. Nothing to install, no account, no key.

```bash
python3 peek/peek.py scan --days 7
```

```bash
python3 peek/peek.py show --top 20
```

```bash
python3 peek/peek.py check peek/editions/1.json
```

- `scan` clones each repository in `repos.json` (shallow, no file contents until needed) into `~/.cache/omarchy-news`, and lists every change on the default branch in the window, one row per pull request or direct commit. Bots, translations, tests, version bumps and backports are set aside, and removals are listed on their own. A repository it cannot read is named, never counted as quiet.
- `rank` is optional. It asks Jev, a small model from TypeSafe that answers typed questions with probabilities, three things about each change: how much a daily user would notice it, what ten seconds of it would look like, and whether its description says what a person can now do. It needs your own `OPENROUTER_API_KEY` in the environment and stops at a spending cap (`--cap`, default 3 cents). On 25 November, 1,822 changes cost $0.047. Without a key, `show` lists changes newest first.
- `show` prints the list by lane: desktop, install, apps, local AI, Mac, mobile, and what was taken out.
- `check` reads an edition: every change it names, at today's code. For each it reports whether the change is still in the default branch and what share of the lines it added (outside tests and translations) are still in the same files. Below 60 percent it fails, and a person reads the change before anyone says it aloud. Controls, marked `"expect": "gone"`, are changes we know were removed; they must read as gone, or the check itself is broken.

The scores only order the reading. A person reads each change it puts near the top, then its pull request, then its code, before writing a story file. Every claim in a story names its source and one of four marks (`read`, `counted`, `said`, `open`), as everywhere in this repository.

## What it found the first time

28 days, 14 repositories, 1,822 changes. The two controls: the local models panel had 19 percent of its lines left, Slack theme sync none. Every change the first film names had 71 percent or more. Edition one is `editions/1.json`, with each result.

## What is not here

No key and no private file. The film is made in a separate studio from the story files and this edition; the video is a release asset of this repository. `repos.json` lists who runs each project: Omamobile and Flux are independent projects, and we say so in the film.

Want a repository added, or think we read something wrong? Open an issue.
