# WikipediaPehoejiDataMirror

Data mirror for ChhoeTaigi WikipediaPehoeji. This site provides direct access to every article title in the Taigi Wikipedia ([zh-min-nan.wikipedia.org](https://zh-min-nan.wikipedia.org/)) that is written in Pe̍h-ōe-jī, each with its tone-number input form, a link to the article, and the titles of the English, Chinese (Taiwan) and Japanese Wikipedia articles it leads to. The files are hosted on GitHub Pages for easy access.

## Chu-liāu Pán-koân

版權聲明

- 資料授權：[CC BY-SA 4.0「姓名標示－相同方式分享」授權](https://creativecommons.org/licenses/by-sa/4.0/deed.zh-hant)
- 資料來源：Wikipedia (Wiki百科) contributors, <https://zh-min-nan.wikipedia.org/>

Wikipedia content is licensed CC BY-SA 4.0. If you redistribute these tables or anything built from them, **credit Wikipedia** and **release your derivative under the same licence**.

## Latest Version

- **Version ID:** `20261009-194411`
- **Last Updated:** 2026-10-09
- **Source dumps:** `zh_min_nanwiki-20261001-all-titles-in-ns0.gz`, with `page.sql.gz`, `redirect.sql.gz` and `langlinks.sql.gz` of the same run (dump run 2026-10-01)
- **Coverage:** 293,009 Pe̍h-ōe-jī titles, out of 679,227 namespace-0 titles, in 289,365 rows; 268,096 of them with an English, Chinese or Japanese title

You can check [**manifest.json**](./public/manifest.json) for the latest version information programmatically. It records `last_updated`, `latest_version_dir`, the source dump URL and date, per-file SHA256 hashes, and row counts.

## Accessing Files

The files are organized by version. Once updated, the latest files will be in `public/{version}/`.

```
bunji/                              # 文字
  WikipediaPehoeji.csv/.json          # one row per Pe̍h-ōe-jī title (same-article duplicates merged)
WikipediaPehoejiDataQuality.md/.json  # counts and findings for this version
```

### `WikipediaPehoeji` — one row per Pe̍h-ōe-jī title

289,365 rows: one per Pe̍h-ōe-jī title, except that titles which read the same once corrected and lead to the same article share a row (3,644 merged; see caveat 1).

* **CSV:** `https://chhoetaigi.github.io/WikipediaPehoejiDataMirror/public/{version}/bunji/WikipediaPehoeji.csv`
* **JSON:** `https://chhoetaigi.github.io/WikipediaPehoejiDataMirror/public/{version}/bunji/WikipediaPehoeji.json`
* **Columns:** `PojUnicode, PojInput, LaigoanBangchi, EngBun, HoaBun, JitBun`

| Column | Description | Rows filled |
|--------|-------------|-------------|
| `PojUnicode` | The title in Pe̍h-ōe-jī, corrected for searching, e.g. `Tâi-oân-hú-siâⁿ (khu-pia̍t-ia̍h)` | 289,365 |
| `PojInput` | The same text in tone-number input form, e.g. `Tai5-oan5-hu2-siann5 (khu-piat8-iah8)` | 289,365 |
| `LaigoanBangchi` | Link to the exact article, e.g. `https://zh-min-nan.wikipedia.org/wiki/Tâi-oân-hú-siâⁿ_(khu-pia̍t-ia̍h)` | 289,365 |
| `EngBun` | Title of the English Wikipedia article it leads to, e.g. `Tokyo` for `Tang-kiaⁿ` | 249,608 |
| `HoaBun` | Title of the Chinese Wikipedia article, in its Taiwan (zh-tw) form, e.g. `東京` | 156,880 |
| `JitBun` | Title of the Japanese Wikipedia article, e.g. `東京` | 80,005 |

268,096 rows have at least one of `EngBun`, `HoaBun`, `JitBun`; an empty cell means the article has no counterpart in that language.

The column names are the ones the ChhoeTaigi database uses for these rows (dataset `SoanntengBunjiMuitheSekin`, 線頂文字媒體索引, `LaigoanMia` = `Wikipedia (Wiki百科)`), so the table can be loaded without renaming. `EngBun`, `HoaBun` and `JitBun` (英文, 華文, 日文) are columns the database has for every dataset, which its Wikipedia rows have so far left empty.

CSV is UTF-8 **with BOM** (so Excel auto-detects the encoding), every field quoted, with a header row (~43 MB). JSON is a UTF-8 array with one record per line (~65 MB).

## How titles are chosen and rendered

- **Selection.** A title is kept when any of its parts — split on `-`, `_`, `(` and `)` — is a single Pe̍h-ōe-jī syllable (matched case-insensitively). This is the rule ChhoeTaigi has used since its first Wikipedia import; on the 2024-10-20 dump it reproduces that import exactly, title for title.
- **`PojUnicode`.** The title made as good as possible for finding by Pe̍h-ōe-jī, since ChhoeTaigi searches this column. `LaigoanBangchi` keeps the exact page, so the text is free to differ from the title. `_` becomes a space — `Tâi-oân-koān_(1684~1887)` → `Tâi-oân-koān (1684~1887)` — and typing slips are corrected:
  - the dot of o͘ typed as `·` or `•` is restored: `Chúi-lō·` → `Chúi-lō͘`;
  - i̍ typed with a dotless `ı̍` or a Greek `ἰ` becomes `i̍`: `Jı̍t-pún` → `Ji̍t-pún`;
  - full-width punctuation becomes ASCII, a non-breaking hyphen `-`, and a `(` stuck to a word gets its space — but not notation like `tâng(II)` or `501(c)`;
  - syllables run together in a word that carries a tone mark and is not itself one syllable are hyphenated again — `kūle̍k` → `kū-le̍k`, `Sūkhek` → `Sū-khek`, `Ēmn̂g` → `Ē-mn̂g` — but only into a hyphenated form some other Wikipedia title uses, so a foreign name that happens to parse as syllables (`Hélène`) is never split, and that form decides between two readings (`sîtāi` → `sî-tāi`, not `sît-āi`).

  Every corrected row is listed in `WikipediaPehoejiDataQuality.md`/`.json`.
- **`PojInput`.** Each tone mark is removed and its number appended to the word: acute 2, grave 3, circumflex 5, macron 7, vertical line 8, breve or double acute 9. `o͘` → `oo`, `ⁿ` → `nn`, `ṳ`/`o̤` → `ur`/`or`. Built from the corrected `PojUnicode`, so `Chúi-lō·` gives `Chui2-loo7` and `kūle̍k` gives `ku7-lek8`. The number follows the syllable even when Hanji come right after it: `Ho̍h-ló話` → `Hoh8-lo2話`. Diacritics that are not Pe̍h-ōe-jī — `ś`, `ž`, Vietnamese `ộ`, `ư` — are left untouched. A caron is not read as a tone mark either: `jiǔ` stays `jiǔ`, and the titles with one on a tone-bearing letter are listed in `WikipediaPehoejiDataQuality.md`.
- **`LaigoanBangchi`.** `https://zh-min-nan.wikipedia.org/wiki/` + the title as it appears in the dump, *not* percent-encoded, which is how the ChhoeTaigi database stores it. Browsers encode it on request — except `?`, which a browser would take as the start of a query, so it is written `%3F`: `…/wiki/%3F_(tiān-iáⁿ)`.
- **`EngBun` / `HoaBun` / `JitBun`.** The article's interlanguage links, from the `langlinks` dump of the same run (Wikidata's sitelinks included). A Pe̍h-ōe-jī title that is a redirect takes the links of the article it leads to — `'Amran Séng` → `'Amran-séng` → `'Amran Governorate` — unless Wikidata attaches the redirect to an item of its own: `Bart Simpson` redirects to `Nancy Cartwright` but keeps its own `Bart Simpson`. Each linked title is then looked up on its own Wikipedia, and the title of the page the link actually lands on is given:
  - a link to a redirect is followed — `Tang-kiaⁿ` links to en `Tokyo Proper`, which redirects to `Tokyo`;
  - zh Wikipedia stores each title in the script its article was created in and converts it for display, so `HoaBun` is the zh-tw form — `东京` → `東京`, `软件` → `軟體`;
  - a link to a page that is not an article — a category, portal or template — or that no longer exists is dropped and listed in the report.

## Caveats

### 1. Redirects are included

The `all-titles-in-ns0` dump lists redirects alongside articles and does not mark which is which. Both are kept, so spelling variants of one article appear as separate rows — `'Amran-séng`, `'Amran Séng` and `'Amran séng` all lead to the same page. Only rows whose corrected text is identical and that lead to the same article become one, the article's own row: `10 goe̍h 10 ji̍t (kūle̍k)`, a redirect, is merged into `10 goe̍h 10 ji̍t (kū-le̍k)` (3,644 in this version, all listed in the report). Identical texts that lead to different pages keep their rows. Every link works.

### 2. Not every kept title is Taigi

Selection only asks that *one* part of the title look like a Pe̍h-ōe-jī syllable, so place names in other languages are kept whenever one of their words happens to fit: `Saint-Jean-de-Maurienne`, `San Giorgio di Lomellina`. The rule is deliberately unchanged from ChhoeTaigi's original import.

### 3. Some multi-tone words keep their tone marks in `PojInput`

1,448 rows still contain a word carrying two or more tone marks that could not be split into syllables: mostly foreign names that are not Pe̍h-ōe-jī at all, kept because another part of the title is a syllable (`Pyrénées`, `Józefów`), and a few run-together syllables that no title writes hyphenated. A syllable has one tone, so there is no single number to append: the word is copied into `PojInput` unchanged rather than guessed at. They are listed in `WikipediaPehoejiDataQuality.md`. The earlier ChhoeTaigi import converted one mark of such words and kept the other, giving mixed forms like `kūlek8`.

### 4. `!Xóõ-gú` is new to ChhoeTaigi

The first title in the dump was missing from ChhoeTaigi's earlier import: that file had no header row, so the first data row was read as one. This mirror always writes a header.

### 5. `HoaBun` uses zh Wikipedia's general zh-tw conversion

zh Wikipedia converts a title to zh-tw with its site-wide tables, and some articles add a rule of their own on top: `悉尼` is shown in zh-tw as `雪梨 (城市)`. Only rendering each article applies those rules — one request per article, ~80,000 a month — so `HoaBun` has the general conversion (`悉尼`), not the article's own.

### 6. Redirects to a section get no titles

2,029 Pe̍h-ōe-jī titles redirect to a section of an article: `Jı̍t-pún sî-tāi` → `Tâi-oân le̍k-sú#Jı̍t-pún sî-tāi`, `48 nî chhut-sì` → `48 nî#Chhut-sì`. The article's links name the whole article (`History of Taiwan`, `AD 48`), not what the title names, so these rows leave `EngBun`, `HoaBun` and `JitBun` empty, unless the redirect has interlanguage links of its own. So do the 436 redirects into another namespace, such as `0 nî-tāi chhut-sì` → `Category:0 nî-tāi chhut-sì`.

### 7. Following a redirect can widen the subject

Wikidata sometimes links an article to a redirect, usually because the other Wikipedia has no article of its own on the subject. The title given is the page that redirect lands on — what a reader following the link sees — and that page is often broader: `Tang-kiaⁿ`, the special wards that used to form the city of Tokyo, links to en `Tokyo Proper` and is given `Tokyo`, the same as `Tang-kiaⁿ-to͘`, the whole metropolis; `48 nî` links to `AD 48` and is given `40s`. In this version 12,692 `EngBun` and 280 `JitBun` rows differ from the linked title, nearly all of them this way; `HoaBun` follows redirects too. A link that names a section of an article is dropped instead: `Liông-hó͘-thah`, the pagodas, links to zh `蓮池潭#龍虎塔`, and `蓮池潭` would be the lake. The report lists each linked title beside the one given. Treat the three titles as equivalents to look up, not translations.

### 8. Some values differ from ChhoeTaigi's earlier import

Matched on `LaigoanBangchi`, the earlier import's 290,595 rows compare as follows:

| | rows |
|---|---|
| identical | 172,650 |
| differ only in the space now written before `(` | 112,604 |
| corrected text (restored hyphens, o͘, i̍ …) | 200 |
| same text, `PojInput` differs: multi-tone words left as written instead of half-converted | 1,444 |
| same text, `PojInput` differs: smaller conversion fixes (double-acute tone 9, Hanji after a syllable …) | 33 |
| merged into the row of the article they lead to | 3,644 |
| no longer in the dump | 20 |

26 `LaigoanBangchi` contain `%3F` where the import has `?`, whose links open the wrong page. 2,434 rows are titles added since the import.

## Chu-liāu bāng-chí

資料下載

1. [Wikimedia dumps for zh_min_nanwiki](https://dumps.wikimedia.org/zh_min_nanwiki/) — from each monthly run, `all-titles-in-ns0.gz` (~3.5 MB gzipped) for the titles, and `page.sql.gz`, `redirect.sql.gz` and `langlinks.sql.gz` (~120 MB together) for redirects and interlanguage links.
2. The APIs of [English](https://en.wikipedia.org/w/api.php), [Chinese](https://zh.wikipedia.org/w/api.php) and [Japanese](https://ja.wikipedia.org/w/api.php) Wikipedia — each linked title is looked up, 50 per query, to follow redirects and get its zh-tw form.

The pipeline reads `latest/zh_min_nanwiki-latest-all-titles-in-ns0.gz-rss.xml` to find the dated run that `latest` points at and downloads the dated files, so `manifest.json` records URLs that keep resolving after `latest/` has moved on. If the RSS cannot be read, the run stops without publishing.

## Source

Original data source: Wikipedia (Wiki百科) <https://zh-min-nan.wikipedia.org/>

## Terminology

- **Taigi** — the language. Written in Hanji and in Roman Orthography.
- **Pe̍h-ōe-jī (POJ)** — the Taigi Roman-script Orthography in the Presbyterian tradition. Columns `PojUnicode` and `PojInput`.
- **bûn-jī** (文字) — text data. Directory `bunji/`.
- **táng-ló͘** (檔路) — download; a loan of English "download". Directory `tangloo/`, holding the dumps and API answers as downloaded rather than anything this repo publishes. Never committed.
- **Eng-bûn, Hôa-bûn, Ji̍t-bûn** (英文, 華文, 日文) — English, Chinese (Taiwan), Japanese. Columns `EngBun`, `HoaBun`, `JitBun`.
- **lâi-goân bāng-chí** (來源網址) — source URL. Column `LaigoanBangchi`.
