# About this fork

`gAmUssA/watch-skill` is a maintained fork of [taoufik123-collab/claude-watch](https://github.com/taoufik123-collab/claude-watch) (itself built on [bradautomates/claude-video](https://github.com/bradautomates/claude-video)).

As of 2026-09-23, upstream `/watch` fails on any current ffmpeg (7+ removed `-vsync`). Nine separate PRs fix that, and 15+ more PRs are open, but the maintainer hasn't merged anything since the last upstream commit on 2026-07-24. This fork adopts the reviewed, working PRs so the skill runs today. The fork will track upstream if it becomes active again.

## Install

```
/plugin marketplace add gAmUssA/watch-skill
/plugin install watch@watch-skill
```

The plugin is still called `watch`, so the skill is still `/watch:watch`. If you have the upstream marketplace installed, remove it first (`/plugin marketplace remove claude-watch`) to avoid two `watch` plugins.

## Adopted upstream PRs

Cherry-picked with `-x`, so every commit keeps its original author and records the upstream commit it came from.

| PR | Author | What | Notes |
|---|---|---|---|
| #3 | @telaaron | Native-language captions, even-coverage frame sampling (two-pass: detect all cuts, then bucket by time), pacing fixes, visual-density classifier (`--mode auto`) | Fixes the fast-cut-intro starvation that left the last 29 min of a 2h video unsampled. |
| #11 | @NikosPAOK1999 | `-vsync` → `-fps_mode` | Applied as its own commit across #3's new code path. |
| #20 | @b-clg | `--no-whisper` privacy leak, UTF-8 stdio, `--out-dir` safety, bounded downloads, quoted frontmatter, SKILL.md injection/credential/`rm -rf` hazards, regression tests | Skipped its `-vsync` probe commit (superseded by #11), and replaced the probe tests with a guard test. |
| #4 (commit 1) | @DavidBeile | Whisper honours `--start`/`--end`; 25 MB pre-flight guard; real failure reasons | Resolved against #20's `sys.executable` hint. |
| #7 | @Jean-Claude92 | Unit tests for VTT parsing | |
| #18 | @scotch333 | TikTok `eng-US` captions | Adapted: added `eng-US` to #3's fallback chain instead of the blanket `en.*,eng.*` regex. |
| #21 | @jlewisd2006-crypto | Vault staging never reuses or deletes a pre-existing directory | Merged with #20's guarded `rm -rf` command. |

## Not adopted (yet)

| PR | Why |
|---|---|
| #4 (commit 2, motion scores) | Decodes the whole video with `signalstats`. Minutes of CPU on 2h videos, only to pick hero frames. Revisit with sampling. |
| #9 | Coverage-gap fallback, superseded by #3's even-coverage sampling. |
| #8, #1 | UTF-8 stdout, covered by #20. |
| #12, #15, #16, #19 | Duplicate `-vsync` fixes. #15's Windows hook tweak and #16's yt-dlp failure-mode docs are small candidates for later. |
| #10 | Single bundled commit (Windows `.env` encodings, YouTube 403 player-client fallback, transcript-only mode). The 403 fallback is worth splitting out and adopting separately. |
| #5 (closed upstream) | Local faster-whisper backend. Promising (no API key, audio stays local) but adds an optional heavy dependency; candidate for a later release. |

## Maintenance

```bash
git remote add upstream https://github.com/taoufik123-collab/claude-watch   # once
git fetch upstream '+refs/pull/*/head:refs/remotes/pr/*'                  # all PR heads
git log --oneline main..pr/<N>                                           # review a PR
git cherry-pick -x <sha>                                                 # adopt, keeping authorship
cd scripts && python3 -m unittest discover -s tests                      # must stay green
```

Public text in this repo (README, FORK.md, CHANGELOG, commit messages) goes through the `jbaruch/blog-writer` (Tessl) three-pass AI-slop check before it's pushed.

Rules for adopting a PR: read the full diff (this skill runs shell commands on your machine), keep changes minimal and attributed, run the test suite plus one real `/watch` end-to-end, and record the decision in the tables above.
