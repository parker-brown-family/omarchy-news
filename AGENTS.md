# Omarchy News, for agents

**To read the news,** fetch `feed.json` (JSON Feed 1.1). Each item's `_omarchy_news` holds the claims, sources, open questions, issue and videos. Nothing else needs fetching.

**To add or change a story,** edit `stories/<id>.json`, run `python3 tools/build.py`, then `python3 tools/issues.py` if it is new, then build again. `python3 tools/build.py --check` must pass.

- A story belongs to every topic it fits. Repeating it is wanted. Give each topic its own angle.
- Repeat a claim with its mark. `said` never becomes `read` or `counted` because it has been told often; only a source changes a mark.
- Open the source before citing it. A source nobody has read has `"read": null`, and no claim may cite it.
- `null` means not known. Never put a guess or a zero in its place.
- Paraphrase. Never copy an article or a post in here. Link it.
- Name the critic's source beside the project's. If nobody has answered an accusation, say so under `to_find`.
- Like and view counts are true on the day they were read. Say when.
- No `@name` in an issue, and link GitHub there through `redirect.github.com`, so citing someone does not notify them.

**Videos** are sealed films only, as release assets tagged `film-<id>`, never in git. `videos.json` holds the checksum and the stories each one tells. The poster goes in `posters/`.

**Peek Behind the Curtain** is weekly, on Wednesdays: `peek/README.md`. Name a change only after `python3 peek/peek.py check peek/editions/<n>.json` passes on the day the film is made. Omamobile and Flux are independent projects: say so, and never call Omamobile "Omarchy Mobile" (its maintainers renamed it at Omarchy's request).

**Licence:** the code here (`tools/`, `peek/`) is MIT (`LICENSE`). Story files paraphrase and link; they never copy.
