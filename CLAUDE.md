# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Data mirror for the Pe̍h-ōe-jī article titles of the Taigi Wikipedia (https://zh-min-nan.wikipedia.org/). Part of the ChhoeTaigi project. The repo downloads the monthly `all-titles-in-ns0` dump from https://dumps.wikimedia.org/zh_min_nanwiki/, keeps the titles containing a Pe̍h-ōe-jī syllable, converts them into one CSV+JSON table with the ChhoeTaigi database's own column names, and hosts everything via GitHub Pages. Its columns `EngBun`, `HoaBun` and `JitBun` give the English, Chinese (zh-tw) and Japanese Wikipedia title each Pe̍h-ōe-jī title leads to (`Tang-kiaⁿ` → `Tokyo` / `東京` / `東京`), from the `page`, `redirect` and `langlinks` dumps of the same run plus the en/zh/ja APIs.

Licensed **CC BY-SA 4.0**, as Wikipedia is: credit Wikipedia, share alike.

It replaces `ParseWikipediaPehoejiPanAllTitlesInNamespace0` (a one-off Kotlin script, run once on the 2024-10-20 dump), whose output became the `Wikipedia (Wiki百科)` rows of `SoanntengBunjiMuitheSekin` in `ChhoeTaigiPlusWebsite/database_src`.

## Commands

```bash
# Run the full update pipeline (downloads four dumps, ~125 MB; filters;
# looks the linked titles up on the en/zh/ja APIs; checks for changes via
# SHA256 of the published CSVs; builds the tables)
cd script && python update_data.py

# Iterate without downloading, against local dumps. The all-titles file must
# keep its dated name (the manifest records the dump URL built from it), and
# the page/redirect/langlinks .sql.gz of the same run must sit beside it —
# as they do in every tangloo/.
cd script && python update_data.py --dump ../public/{version}/tangloo/zh_min_nanwiki-YYYYMMDD-all-titles-in-ns0.gz

# …and skip the ~30 min of API queries by reusing an earlier run's answers
cd script && python update_data.py --dump ../public/{version}/tangloo/zh_min_nanwiki-YYYYMMDD-all-titles-in-ns0.gz \
    --resolved ../public/{version}/tangloo/zh_min_nanwiki-YYYYMMDD-langlinks-resolved.json

# A failed run keeps its downloads and API answers in public/temp_update_failed/
# (gitignored) and prints the command that starts from them:
cd script && python update_data.py --dump ../public/temp_update_failed/zh_min_nanwiki-YYYYMMDD-all-titles-in-ns0.gz \
    --resolved ../public/temp_update_failed/zh_min_nanwiki-YYYYMMDD-langlinks-resolved.json

# Force a new version directory even when the output is unchanged — and
# publish even when counts fell more than 5% since the last version, or the
# dump is older than the published one
cd script && python update_data.py --force

# Run only the conversion (add --related [--resolved PATH] to fill EngBun/HoaBun/JitBun;
# without it they are left empty)
cd script && python convert_titles.py ../public/{version}/tangloo/zh_min_nanwiki-YYYYMMDD-all-titles-in-ns0.gz /tmp/out/bunji
```

Dependencies: pure Python stdlib (no `pip install` needed). A full run takes
~30 min, nearly all of it API queries (~3,000 en, ~1,650 zh, ~780 ja, each
wiki in its own thread); with `--resolved`, under a minute.

### Verifying a change

There is no test suite. The pipeline *is* the check: run it and read
`public/{version}/WikipediaPehoejiDataQuality.md`.

- **Selection regression check.** The old Kotlin repo sits beside this one
  with its input and output committed. Running `contains_poj()` over
  `../ParseWikipediaPehoejiPanAllTitlesInNamespace0/zh_min_nanwiki-20241020-all-titles-in-ns0`
  must keep exactly the 290,596 titles in its `…-output.csv`, in order. Any
  change to `POJ_UNICODE_REGEX` or `SEGMENT_SPLIT` must still pass this.
- **Database check.** Against the 290,595 Wikipedia rows in
  `ChhoeTaigiPlusWebsite/database_src/*/JOINED/*.csv` (matched on
  `LaigoanBangchi`, `%3F` read as `?`): 172,650 identical; 112,604 differ
  only in the space now written before `(`; 200 have corrected text; 1,444
  keep their text but leave a multi-tone word as written (the database
  half-converts it, `kūlek8`); 33 smaller conversion fixes (double-acute
  tone 9, Hanji after a syllable, full-width brackets and en-dashes no longer
  glued into words); 3,644 merged into their article's row; 20 no longer in
  the dump. A change that moves rows between these lines must be meant.
- **Title text check.** `kūle̍k` must become `kū-le̍k`, `Sūkhek` `Sū-khek`
  (one tone mark) and `Ēmn̂g` `Ē-mn̂g` (a syllabic nasal after an initial),
  while `Hélène`, `Pyrénées` and the one-syllable `hiông` stay as written;
  `10 goe̍h 10 ji̍t (kūle̍k)` must be merged into `10 goe̍h 10 ji̍t (kū-le̍k)`;
  `tâng(II)` keeps its parenthesis attached.
- **`EngBun`/`HoaBun`/`JitBun` check.** `Tang-kiaⁿ` must give `Tokyo` /
  `東京` / `東京`: its en link is `Tokyo Proper`, a redirect, and its zh link
  is `东京`. `Bart Simpson`, a redirect to `Nancy Cartwright` with links of
  its own, must give `Bart Simpson`. A redirect to a section (`48 nî
  chhut-sì`) must have all three empty, and no cell may name a category,
  portal or template (`Category:`, `分類:`, `Portal:`, `Template:`). The
  first three columns must not change when only these do. In the report,
  the reasons for rows with no title must add up: an "Unexplained" row
  means a counting bug.
- A second run with unchanged data must reuse the existing version directory.
  Use `--resolved`; without it, renames on the three wikis since the last run
  legitimately produce a new version.

## Architecture

### Data Pipeline (`script/`)

1. **`update_data.py`** — Main entry point. Verifies `README.md`/`index.md` are in sync, reads `latest/…-all-titles-in-ns0.gz-rss.xml` to resolve the dated dump run, downloads the dated all-titles file and the `page`/`redirect`/`langlinks` dumps of the same run, builds into a staging directory, compares the SHA256 of the published table (CSV and JSON) against `public/manifest.json`, and only then moves it into a timestamped version directory and writes the manifest.

2. **`convert_titles.py`** — Filters titles with `contains_poj()`, renders `PojUnicode` / `PojInput` / `LaigoanBangchi`, writes `bunji/WikipediaPehoeji.{csv,json}` and the data-quality report at the version root. Given a `relate` callable, also fills `EngBun` / `HoaBun` / `JitBun`.

3. **`related_titles.py`** — For the kept titles: reads `page` / `redirect` / `langlinks` (regex over mysqldump rows), takes the en/zh/ja links of the first page along each title's redirect chain that has interlanguage links of its own, then looks every distinct linked title up on its wiki's API (50 per POST, `redirects=1`; zh with `inprop=varianttitles`). The answers — `[namespace, title]` or `null` per linked title, format 2 — are saved as `tangloo/…-langlinks-resolved.json`, even when the lookups fail.

### Key design decisions

- **Change detection hashes the published table — CSV and JSON — not the dumps.** The dump is rebuilt every month whether or not a Pe̍h-ōe-jī title changed. Hashing the table also means a converter or JSON-writer change produces a new version — intended. The report is deliberately not hashed: its count of reused API answers differs on every run. A report-only change goes live with the next table change, or with `--force`. The CSV also changes whenever a linked article on en/zh/ja is renamed, so most monthly runs will publish.

- **Build in staging, publish on success.** Nothing under `public/` is touched until conversion succeeds, so a failed run leaves no partial version directory. What it fetched is kept in `public/temp_update_failed/` (dumps hard-linked, API answers so far) for `--dump`/`--resolved`; the next successful run deletes it. Even a failure after the build has moved into its version directory hands `tangloo/` back there first; answers already kept are merged with, never replaced by, a later run's (an unreadable one changes nothing); copies and saves go through `.part` files. The report a failed run built is kept in `temp_update_failed/report/` — a run refused for a count drop is judged by it. The all-titles dump's Last-Modified is kept beside it (`….gz.last-modified`), so a version published by resuming still records it. A successful run removes only its own dump run's files there; another run's stay for their own resume. `--resolved` is loaded before any download, so a wrong file (a `.sql.gz`) fails at once. The version directory is reserved by creating it, so two runs in one second get two names.

- **Refuse a sharp drop.** A partial failure upstream — a dump whose columns changed, an API that stopped answering — shows up as falling counts, not an error. A run whose `rows`, `related_rows` or `related_rows_{EngBun,HoaBun,JitBun}` fall more than 5% below the last manifest's refuses to publish unless `--force`. So does a dump older than the manifest's `source_dump_date` — it would drop every title added since — checked before anything is fetched.

- **The dated dump URL is recorded, never `latest`.** The RSS file beside `latest/` names the dated run. When it cannot be read (three tries) or names no dated file, the run aborts rather than publish a version that cannot be traced to a dump run; `--dump` likewise accepts only a dated file name.

- **Output columns are the ChhoeTaigi database's.** `PojUnicode`, `PojInput`, `LaigoanBangchi`, `EngBun`, `HoaBun`, `JitBun` — not the snake_case of the Wikidata mirror — because these rows are loaded straight into `SoanntengBunjiMuitheSekin`.

- **The link is faithful; the text is made searchable.** `LaigoanBangchi` is the exact page and is never corrected (beyond `%3F`). `PojUnicode`, which ChhoeTaigi searches, is the title made as good as possible for finding by Pe̍h-ōe-jī: spacing, typing slips, run-together syllables (see invariants). No correction is silent: every corrected row is in the report (`corrected_rows`), and so is every merge (`merged_rows`).

- **The title columns are in the one table, so its JSON is 65 MB.** That is
  past GitHub's 50 MB push warning, under its 100 MB limit — accepted so the
  database loads a single table. (A separate `WikipediaPehoejiGoabun` table
  joined on `LaigoanBangchi`, 43 MB as JSON, was tried and dropped.) The CSV
  is 43 MB. Check the 100 MB limit before adding any column.

- **Linked titles are where the link lands, not what `langlinks` says.**
  Wikidata may link a page to a redirect on purpose (`Tang-kiaⁿ` → en
  `Tokyo Proper`, badge "intentional sitelink to redirect"); a reader who
  follows it reads `Tokyo`. This was chosen knowing it widens the subject
  for ~6,000 en titles (`AD 48` → `40s`, `1402 Eri` → `List of minor
  planets: 1001–2000`, `Pișcov River` → `Bașeu`), ~150 ja and ~170 zh, and
  that `Tang-kiaⁿ` and `Tang-kiaⁿ-to͘` both get `Tokyo`. Keeping the linked
  title instead is a one-line change (drop `redirects=1`) but changes the
  data — ask first. A linked page that no longer exists is dropped and
  listed in the report.

- **API politeness.** One kept-alive connection per wiki, one request at a
  time, `maxlag=5`, a descriptive User-Agent — Wikimedia's API etiquette.
  Do not add parallelism within a wiki. A maxlag refusal waits its
  Retry-After without using up a retry, for up to 10 min in all; an HTTP
  429/503 waits its Retry-After (up to 5 min) before the retry — from the API
  and from dumps.wikimedia.org alike. An answer that is not the documented
  JSON shape is retried, never trusted. When one
  wiki gives up, or on Ctrl-C, the other threads stop at their next request;
  even a second Ctrl-C waits for the requests in flight, so no answer is lost.

### Non-obvious invariants

- **`POJ_UNICODE_REGEX` is ported verbatim from Kotlin, oddities included.**
  `̍ă` has a stray leading combining mark, `r` counts as a vowel, and plain
  ASCII syllables like `Pak` match, so foreign place names are kept whenever
  one word fits. Every one of these looks like a bug and "fixing" any of them
  changes which titles ChhoeTaigi publishes. Change selection deliberately or
  not at all, and rerun the regression check above. "Verbatim" is per code
  point: Kotlin's `ŏ̤` is decomposed (`o` U+0324 U+0306), so it is escaped in
  the source — an editor that NFC-normalizes would turn it into `ŏ̤`.

- **`WORD` must include combining marks.** Python's `\w` excludes them, so a
  letters-only regex splits `ji̍t` into `ji` + `̍` + `t` and appends the tone
  after the wrong letter (`ji8t`). That was the first bug found here — 59,000
  rows wrong. And only the Latin runs of a word are converted (`_is_latin`):
  `\w` also takes Hanji, so `ló話` was one word and got `lo話2`, not `lo2話`.

- **`PojUnicode` corrections** (`title_text`, in this order, each listed in
  the report): full-width punctuation → ASCII, with the space a following
  Latin letter needs; `·`/`•` right after an o → o͘ (`Chúi-lō·` →
  `Chúi-lō͘`; elsewhere `·` separates words, `Sam·It`); i̍ typed as dotless
  `ı̍` or Greek `ἰ` → `i̍` (a plain `ı`, in Turkish names, stays; `ἰ` only
  beside a Latin letter, so Greek `Αἰσχύλος` stays); a
  non-breaking hyphen → `-`; a space before a `(` stuck to a letter, except
  notation (`tâng(II)`, `501(c)`). And `_` is a space throughout, so `X_(Y)`
  is `X (Y)`, not the 2024 import's `X(Y)`.

- **Run-together syllables are hyphenated only when attested.** A Latin word
  that carries a tone mark and is not itself one syllable is split into POJ
  syllables (`POJ_SYLLABLES`: initials × finals, and the syllabic nasals
  after any initial — `mn̂g`, `tn̂g`, `sng`; at most one tone each), but only
  into a hyphenated form some title in the dump uses, whole or inside a
  longer hyphenated token (`attested_hyphenations`). Without that, French
  `Hélène` parses as `Hé-lè-ne`, and `sîtāi` as both `sî-tāi` and `sît-āi`.
  Exactly one attested split, or none. A one-syllable word is never split
  (`hiông`, not `hi-ông`); a one-tone word that is not one syllable is, or
  its number lands after the wrong syllable (`Sūkhek` → `Sukhek7`).

- **The syllable search only extends attested beginnings.**
  `attested_hyphenations` holds every run of pieces, single ones too, and
  `_attested_splits` follows a split only while its beginning is one of
  them. Unpruned, the search was exponential: a 120-letter run-together title
  with no complete parse took hours, stalling the run before any API work.
  Do not drop the pruning, or cap the number of parses instead — the
  attested split of a long word is often far down the list.

- **Merging needs the redirect dump.** Rows merge only when their corrected
  `PojUnicode` is identical and `landing_pages` puts them on the same page (a
  redirect to a section lands on its page; at most `MAX_REDIRECT_HOPS` hops,
  as for the links). Kept: the article's own row,
  else the row that needed no correction, else the first. The 8 texts whose
  rows lead to different pages (`Chit-sò·` → `Chek-sò͘`, `Chit-sò͘` →
  `Sò͘-sò͘`) keep every row. Without `landing` (convert_titles.py without
  `--related`) nothing is merged.

- **A caron is not a tone mark.** KonvertToPOJ has none, so `jiǔ` stays
  `jiǔ` in `PojInput` rather than become `jiu6`. Of the 105 rows with a caron
  on a tone bearer, nearly all are Czech/Slovak (`Moravě`, `Plzeň`); they are
  listed in the report (`rows_caron`). A caron on `š`/`č`/`ž` is foreign by
  `TONE_BEARERS` alone and is not counted.

- **`WORD` takes every combining mark (category M), built at import.** A
  hard-coded U+0300–036F range let a mark from another block split a word,
  the `ji8t` bug again.

- **Multi-tone words are left unconverted on purpose.** A syllable has one
  tone; `kūle̍k` has two marks, so there is no correct single number. The 2024
  import converted the higher-priority mark and kept the other (`kūlek8`).
  Leaving the word verbatim and listing it in the report is the honest
  output — do not reintroduce a priority rule.

- **Tone marks count only on POJ letters.** `_is_poj_letter()` requires a
  tone bearer (`a e i o u m n`), at most one tone mark, and no mark Pe̍h-ōe-jī
  does not use. Without it Polish `ś` becomes `s2`, Vietnamese `Lộc` becomes
  `Lọc5`, `Đức` becomes `Đưc2`. `͘` counts only on `o`.

- **Breve is tone 9, matching KonvertToPOJ's `ToneMap`** (and the 2024 import),
  not tone 6.

- **A redirect with interlanguage links of its own keeps them.** Wikidata
  attaches some redirects to items of their own: `Bart Simpson` redirects to
  `Nancy Cartwright` but is linked to en `Bart Simpson`. A title takes the
  links of the first page along its redirect chain that has any links (in
  any language), so such a redirect never inherits its target's — even when
  its own have no en/zh/ja. ~20 titles.

- **A redirect to a section gets no related titles** (unless it has links of
  its own). `Jı̍t-pún sî-tāi` → `Tâi-oân le̍k-sú#Jı̍t-pún sî-tāi` would inherit
  en `History of Taiwan`; `48 nî chhut-sì` → `48 nî#Chhut-sì`, `AD 48`.
  ~2,000 titles. Nor does a redirect out of the article namespace
  (`0 nî-tāi chhut-sì` → `Category:0 nî-tāi chhut-sì`, ~440).

- **Only articles count as linked pages.** A link that lands in another
  namespace is dropped and listed in the report: `1759 nî kho-ha̍k` links to
  zh `Category:1759年科學`, whose zh-tw variant even translates the prefix
  (`分類:1759年科學`). The answers file records each page's namespace for
  this; answers in the older format, without it, are not reused. zh
  `Special:`/`Media:` pages (ns -1, -2) are virtual and have no zh-tw
  variant; they are dropped like the rest. A *real* zh page without one
  aborts the run: that means the API changed. A linked title that is not
  valid UTF-8 cannot be sent at all; it is dropped and counted
  (`langlinks_not_utf8`).

- **`--resolved` reuses only answers for titles still linked**, and asks
  again about pages it had found missing. The report and manifest count the
  reused answers (`api_answers_reused`).

- **`HoaBun` is the site-wide zh-tw conversion, not the page's own.**
  `inprop=varianttitles` applies zh Wikipedia's conversion tables but not an
  article's `-{T|…}-` / NoteTA title rule: `悉尼` stays `悉尼`, though the
  article displays as `雪梨 (城市)` in zh-tw. Only `action=parse`, one page per
  request, applies those — ~80,000 requests, too many to make monthly.

- **URLs are deliberately not percent-encoded — except `?`.** The ChhoeTaigi
  database stores them raw; encoding would break equality with every existing
  row. But a browser takes `?` as the start of the query string instead of
  encoding it, so it is written `%3F`: 26 rows, whose database links open the
  wrong page (`…/wiki/?_(tiān-iáⁿ)` opens the Main Page).

- **A link that names a section is dropped.** `Liông-hó͘-thah` (the pagodas)
  links to zh `蓮池潭#龍虎塔`; the article it is in, `蓮池潭`, is the lake.
  Such links are not looked up and are listed in the report (44 cells).

- **The CSV always has a header row.** The Kotlin parser wrote none, and the
  first title, `!Xóõ-gú`, was consumed as a header downstream — the one row of
  its output missing from the database.

- **JSON is one compact record per line, not `indent=2`.** Indented, the table
  is 74 MB instead of 65 MB. Likewise there is no `PageTitle`
  column: it is `LaigoanBangchi` minus `WIKI_BASE_URL`, and carrying it adds
  ~11 MB to the JSON.

### Downstream

`ChhoeTaigiDatasetGenerator` has its own `WikipediaSekinMapper`
(`manifest/sources.yaml`, code `WikipediaSekin`) that reads the raw dump
directly. Unlike this mirror it applies **no** Pe̍h-ōe-jī filter (all ~680k
titles), and maps `_` → space but makes none of this mirror's corrections or
merges, so its output differs from this table. Pointing that source at this mirror's CSV is the
intended follow-up; it recomputes `PojInput` with KonvertToPOJ anyway.

### Data Layout (`public/`)

```
public/
  manifest.json                       # Latest version, source dump, per-file SHA256, counts
  {YYYYMMDD-HHMMSS}/                  # Timestamped version directory
    WikipediaPehoejiDataQuality.md    # Data-quality report
    WikipediaPehoejiDataQuality.json  # Same, machine-readable, full multi-tone word list
    bunji/
      WikipediaPehoeji.csv/.json        # one row per Pe̍h-ōe-jī title (same-article duplicates merged), with its English / Chinese (zh-tw) / Japanese title
    tangloo/                          # The four dumps + the API answers — gitignored
```

### Hosting

- `index.md` is the GitHub Pages landing page
- `.nojekyll` disables Jekyll processing

## Important Rules

- **`README.md` and `index.md` must stay in sync.** They have identical content. `update_data.py` aborts before any network work if they differ. Fix with `cp README.md index.md`. Update the version ID, dates and counts in both after each new version.
- **`manifest.json` keys files by path relative to the version directory** (`bunji/WikipediaPehoeji.csv`), skipping `tangloo/`. `source_dump` stays the all-titles URL; `source_dumps` lists all four.
- **Never commit the dump.** `public/*/tangloo/` is gitignored.
- **Never correct `LaigoanBangchi`; never correct `PojUnicode` silently.** Every corrected or merged row is listed in the report.
- **Pure stdlib only.**

## Terminology (Taigi)

- **Taigi** — the language. Never "Taiwanese Southern Min", "Holo" or "Hokkien" in prose. `zh-min-nan` / `zh_min_nanwiki` appear only as upstream identifiers.
- **Roman Orthography** — never "Romanization".
- **Pe̍h-ōe-jī (POJ)** — the Taigi Roman-script Orthography.
- **KPL (Kàu-io̍k Pō͘ Lô-má-jī)** — the Taigi Latin-script Orthography. Not produced here; never "Tâi-lô" or "TL".
- **bûn-jī** (文字) — text data. Directory `bunji/`.
- **táng-ló͘** (檔路) — download. Directory `tangloo/`.
- **Eng-bûn, Hôa-bûn, Ji̍t-bûn** (英文, 華文, 日文) — English, Chinese (zh-tw), Japanese. Columns `EngBun`, `HoaBun`, `JitBun`, which the ChhoeTaigi database already has.
