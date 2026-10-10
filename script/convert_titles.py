"""Filter zh-min-nan Wikipedia namespace-0 titles down to the ones containing
Pe̍h-ōe-jī, and build the ChhoeTaigi tables from them.

Input is the plain-text `all-titles-in-ns0` dump (one title per line, spaces
written as `_`, first line the header `page_title`). Output columns follow the
ChhoeTaigi database convention (`PojUnicode`, `PojInput`, `LaigoanBangchi`,
`EngBun`, `HoaBun`, `JitBun`), the same names `SoanntengBunjiMuitheSekin` rows
carry in ChhoeTaigiPlusWebsite.

Given a `relate` callable (see related_titles.py), it also fills `EngBun`,
`HoaBun` and `JitBun`: the English, Chinese (Taiwan) and Japanese Wikipedia
titles each Pe̍h-ōe-jī title leads to.
"""
import argparse
import collections
import csv
import functools
import gzip
import itertools
import json
import re
import sys
import unicodedata
from pathlib import Path

try:
    from related_titles import LANG_COLUMNS, answers_name, landing_pages, related_titles
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parent))
    from related_titles import LANG_COLUMNS, answers_name, landing_pages, related_titles

WIKI_BASE_URL = "https://zh-min-nan.wikipedia.org/wiki/"
DUMP_HEADER = "page_title"

TABLE_NAME = "WikipediaPehoeji"
REPORT_NAME = "WikipediaPehoejiDataQuality"
# Columns of the ChhoeTaigi database, so the table loads without renaming:
# PojUnicode, PojInput, LaigoanBangchi, then EngBun, HoaBun, JitBun — the
# English, Chinese (zh-tw) and Japanese Wikipedia titles, empty where there
# is none. With those three the JSON is 65 MB, past GitHub's 50 MB warning
# (under its 100 MB limit): accepted so the database gets one table. The raw
# page title is not a column: it is `LaigoanBangchi` minus WIKI_BASE_URL.
COLUMNS = ["PojUnicode", "PojInput", "LaigoanBangchi", *LANG_COLUMNS.values()]

# How many example titles each report section lists.
REPORT_SAMPLE_SIZE = 50

# --- Selection --------------------------------------------------------------

# Ported verbatim from ParseWikipediaPehoejiPanAllTitlesInNamespace0
# (src/main/kotlin/wikipedia/Main.kt) so this mirror selects exactly the titles
# ChhoeTaigi has always ingested. It matches ONE syllable, applied
# case-insensitively to each segment of the title split on `-`, `_`, `(`, `)`.
# A title is kept if ANY segment is a syllable. Kept as-is, oddities included
# (`̍ă` with a leading combining mark, `r` as a vowel): changing it changes
# which titles are published. See "Non-obvious invariants" in CLAUDE.md.
# `o\u0324\u0306` (ŏ̤) is escaped because Kotlin's is decomposed, and an editor
# that NFC-normalizes would silently turn it into the different `ŏ̤`.
POJ_UNICODE_REGEX = (
    "^(ph|p|m|b|th|t|l|kh|k|ng|n|g|h|chh|ch|s|j)?"
    "((?:á|à|â|ā|a̍|̍ă|a|í|ì|î|ī|i̍|ĭ|i|ṳ́|ṳ̀|ṳ̂|ṳ̄|ṳ̍|ṳ̆|ṳ|ú|ù|û|ū|u̍|ŭ|u"
    "|ó͘|ò͘|ô͘|ō͘|o̍͘|ǒ͘|o͘|ó̤|ò̤|ô̤|ō̤|o̤̍|o\u0324\u0306|o̤|é|è|ê|ē|e̍|ĕ|e|ó|ò|ô|ō|o̍|ŏ|o|r)*)"
    "(ⁿ|ḿ|m̀|m̂|m̄|m̍|m̆|m|ńg|ǹg|n̂g|n̄g|n̍g|n̆g|ng|ń|ǹ|n̂|n̄|n̍|n̆|n)?"
    "(p|t|k|h)?$"
)
POJ_SYLLABLE = re.compile(POJ_UNICODE_REGEX, re.IGNORECASE)
SEGMENT_SPLIT = re.compile(r"[\-_()]")


def contains_poj(title):
    """True when any `-`/`_`/`(`/`)` segment of title is a POJ syllable."""
    return any(seg and POJ_SYLLABLE.match(seg) for seg in SEGMENT_SPLIT.split(title))


def title_to_url(title):
    """Unencoded, exactly as the ChhoeTaigi database stores `LaigoanBangchi`,
    except `?`: a browser takes it as the start of the query string instead
    of encoding it, so `…/wiki/?_(tiān-iáⁿ)` would open the Main Page.
    Browsers percent-encode everything else on request; encoding it here
    would break equality with every URL already in the database."""
    return WIKI_BASE_URL + title.replace("?", "%3F")


# --- Pe̍h-ōe-jī Unicode → input form -----------------------------------------

# Tone diacritics (NFD combining marks) → tone number, as in KonvertToPOJ's
# ToneMap: breve is tone 9 (not 6), and `n` takes the double acute for 9.
TONE_MARKS = {
    "́": "2",  # acute
    "̀": "3",  # grave
    "̂": "5",  # circumflex
    "̄": "7",  # macron
    "̍": "8",  # vertical line above
    "̆": "9",  # breve
    "̋": "9",  # double acute (n̋)
}
# A caron is not a POJ tone mark here, as in KonvertToPOJ: on a tone bearer it
# is left as written (Czech `Moravě`, but also Taigi `jiǔ`), and such rows are
# listed in the report so they stay visible.
CARON = "\u030c"
# Only these letters bear a POJ tone. A mark on anything else (ś, ž, ư, ý) is
# another language's diacritic and is left untouched.
TONE_BEARERS = set("aeioumnAEIOUMN")
# Non-tone POJ marks, rewritten to their input spelling.
DOT_ABOVE_RIGHT = "͘"   # o͘  → oo
DIAERESIS_BELOW = "̤"   # ṳ, o̤ → ur, or
SUPERSCRIPT_N = "ⁿ"          # ⁿ  → nn
POJ_EXTRA_MARKS = {DOT_ABOVE_RIGHT, DIAERESIS_BELOW}

# A word is a run of letters AND combining marks: Python's \w excludes
# combining marks, so without them `ji̍t` would split into `ji` + `̍` + `t`.
# Every combining mark (category M), in whatever Unicode block, not just
# U+0300–036F: a mark from any other block would split a word the same way.
def _mark_class():
    ranges, start = [], None
    for cp in range(sys.maxunicode + 2):
        is_mark = cp <= sys.maxunicode and unicodedata.category(chr(cp)).startswith("M")
        if is_mark and start is None:
            start = cp
        elif not is_mark and start is not None:
            ranges.append(f"{re.escape(chr(start))}-{re.escape(chr(cp - 1))}")
            start = None
    return "".join(ranges)


WORD = re.compile(r"(?:[^\W\d_]|[" + _mark_class() + r"])+")


@functools.lru_cache(maxsize=None)
def _is_latin(ch):
    """Latin letters, the modifier letters written among them (ⁿ, ʾ) and
    combining marks: the part of a word a tone number goes after. Han right
    after a syllable (`ló話`) is not part of it, or the number would land
    after the Han (`lo話2`)."""
    return (unicodedata.category(ch) in ("Lm", "Mn", "Mc", "Me")
            or "LATIN" in unicodedata.name(ch, ""))


def _clusters(word):
    """Split an NFD word into (base, [combining marks]) clusters."""
    clusters = []
    for ch in unicodedata.normalize("NFD", word):
        if unicodedata.combining(ch) and clusters:
            clusters[-1][1].append(ch)
        else:
            clusters.append((ch, []))
    return clusters


def _is_poj_letter(base, marks):
    """True when base+marks is a POJ letter: a tone bearer with at most one
    tone mark and no mark POJ does not use. Vietnamese ộ, ễ, ắ (a second mark
    stacked on the tone) and ư, ơ (horn) are someone else's letters."""
    if base not in TONE_BEARERS:
        return False
    if any(m not in TONE_MARKS and m not in POJ_EXTRA_MARKS for m in marks):
        return False
    if DOT_ABOVE_RIGHT in marks and base not in "oO":
        return False
    return sum(m in TONE_MARKS for m in marks) <= 1


def word_to_input(word):
    """One word → (input form, is_multi_tone).

    A POJ syllable carries at most one tone mark. A word with two or more
    (`kūle̍k`, `Lō͘sòaⁿ` — syllables written without their hyphen) has no
    single tone number to append, so it is returned unchanged and flagged
    rather than guessed at.
    """
    clusters = _clusters(word)
    tones = [
        m for base, marks in clusters if _is_poj_letter(base, marks)
        for m in marks if m in TONE_MARKS
    ]
    if len(tones) > 1:
        return word, True

    out = []
    for base, marks in clusters:
        poj_letter = _is_poj_letter(base, marks)
        piece = base
        for m in marks:
            if poj_letter and m in TONE_MARKS:
                continue
            if poj_letter and m == DOT_ABOVE_RIGHT:
                piece += "o"
            elif poj_letter and m == DIAERESIS_BELOW:
                piece += "r"
            else:
                piece += m
        out.append(piece)
    text = unicodedata.normalize("NFC", "".join(out)).replace(SUPERSCRIPT_N, "nn")
    return text + (TONE_MARKS[tones[0]] if tones else ""), False


def _has_caron_on_bearer(text):
    return any(base in TONE_BEARERS and CARON in marks for base, marks in _clusters(text))


def poj_unicode_to_input(text):
    """`Tâi-oân-hú-siâⁿ` → `Tai5-oan5-hu2-siann5`. Returns (input, multi_tone_words)."""
    multi = []

    def convert(run):
        converted, is_multi = word_to_input(run)
        if is_multi:
            multi.append(run)
        return converted

    def repl(m):
        # Only the Latin runs of a word are converted; Han, kana, Hangul… pass.
        return "".join(convert("".join(run)) if latin else "".join(run)
                       for latin, run in itertools.groupby(m.group(0), key=_is_latin))

    return WORD.sub(repl, text), multi


def _tone_count(run):
    return sum(m in TONE_MARKS for base, marks in _clusters(run)
               if _is_poj_letter(base, marks) for m in marks)


# --- Title text ---------------------------------------------------------------

# PojUnicode is the title made as good as possible for finding by Pe̍h-ōe-jī:
# ChhoeTaigi searches it. LaigoanBangchi keeps the exact page, so the text is
# free to differ from the title; every correction is listed in the report.

# `·` (or `•`) right after an o is the dot of o͘ typed as a character of its
# own: `Chúi-lō·` is `Chúi-lō͘`. Elsewhere `·` separates words (`Sam·It`).
O_WITH_DOT = re.compile("([oOòóôōŏǒÒÓÔŌŎǑ]\u030d?)[\u00b7\u2022]")
# i̍ typed with a dotless ı, so the vertical line need not sit on a dot
# (`Jı̍t-pún`), or with Greek ἰ (`jἰt`). In NFD. Plain ı (Turkish) stays.
TONED_DOTLESS_I = re.compile("\u0131(?=[\u0300-\u030f])")
# ἰ only beside a Latin letter, and with no further mark: genuine Greek
# (`Αἰσχύλος`, `Αἴγινα`) is left alone.
GREEK_I_WITH_PSILI = re.compile("(?<=[A-Za-z])\u03b9\u0313(?![\u0300-\u036f])"
                                "|\u03b9\u0313(?=[A-Za-z])")
HYPHEN_LOOKALIKES = re.compile("[\u2010\u2011]")
FULLWIDTH_ASCII = re.compile("[\uff01-\uff5e]")
# `(` stuck to a word gets the space every other title has before it, unless
# it is notation: `tâng(II)`, `501(c)`.
ATTACHED_PAREN = re.compile(
    r"(?:(?<=[^\W\d_])|(?<=[\u0300-\u036f]))\((?!(?:[IVXLCDM]+|[A-Za-z])\))")

# Syllables run together in one word (`kūle̍k`, `Lō͘sòaⁿ`) are split again —
# into a hyphenated form Wikipedia's own titles use somewhere (`kū-le̍k`), and
# only then: foreign names that happen to parse as syllables (`Hélène` →
# `Hé-lè-ne`) never appear so, and the form in use also decides between two
# parses (`sîtāi`: `sî-tāi`, not `sît-āi`). Only words with a tone mark that
# are not themselves one syllable are split: `hiông` stays, `Sūkhek` does not.
POJ_INITIALS = ("", "p", "ph", "m", "b", "t", "th", "n", "l", "k", "kh", "ng", "g",
                "h", "ch", "chh", "s", "j")
# Finals in a key alphabet where O is o͘ and N is ⁿ.
_VOWEL_FINALS = ("a", "ai", "au", "e", "i", "ia", "iau", "io", "iu", "o", "O", "oa",
                 "oai", "oe", "u", "ui")
POJ_FINALS = {v + c for v in _VOWEL_FINALS for c in ("", "h", "N", "Nh")} | {
    "am", "ap", "an", "at", "ang", "ak", "iam", "iap", "ian", "iat", "iang", "iak",
    "im", "ip", "in", "it", "eng", "ek", "iong", "iok", "om", "op", "ong", "ok",
    "oan", "oat", "oang", "un", "ut", "Om", "Ong", "Ok"}
# The syllabic nasals take any initial too: mn̂g, tn̂g, sng, kng, pn̄g, nńg.
POJ_SYLLABLES = ({i + f for i in POJ_INITIALS for f in POJ_FINALS}
                 | {i + n for i in POJ_INITIALS for n in ("m", "mh", "ng", "ngh")})
_LONGEST_SYLLABLE = max(map(len, POJ_SYLLABLES))
ATTESTATION_TOKEN = re.compile(r"[^\s_(),./:;!?\"“”'‘’]+")


def attested_hyphenations(titles):
    """Every run of hyphen-joined pieces in the hyphenated words of titles,
    lowercased: `Tiong-kok-Kiōng-sán-tóng` gives `kiōng`, `kiōng-sán`,
    `kiōng-sán-tóng`, … A split is used only when it is one of these, and so
    is every split's beginning, which keeps the search for one short."""
    out = set()
    for title in titles:
        for token in ATTESTATION_TOKEN.findall(title):
            pieces = [p for p in unicodedata.normalize("NFC", token.lower()).split("-") if p]
            if len(pieces) < 2:
                continue
            for i in range(len(pieces)):
                for j in range(i + 1, len(pieces) + 1):
                    out.add("-".join(pieces[i:j]))
    return out


def _syllable_keys(word):
    """[(key, has tone, letters)] per letter of word, or None when a letter is
    not one POJ writes."""
    keys = []
    for base, marks in _clusters(word):
        if base == SUPERSCRIPT_N and not marks:
            keys.append(("N", False, base))
            continue
        low = base.lower()
        if low not in "abceghijklmnopstu" or (marks and not _is_poj_letter(low, marks)):
            return None
        keys.append(("O" if DOT_ABOVE_RIGHT in marks else low,
                     any(m in TONE_MARKS for m in marks), base + "".join(marks)))
    return keys


def _is_one_syllable(keys):
    return ("".join(k for k, _, _ in keys) in POJ_SYLLABLES
            and sum(t for _, t, _ in keys) <= 1)


def _attested_splits(keys, attested):
    """Every split of keys into POJ syllables of at most one tone each whose
    hyphenated form is in attested, built only through attested beginnings:
    a word with no attested split costs a few steps, not every parse."""
    out = []

    def walk(i, parts):
        if i == len(keys):
            out.append("-".join(parts))
            return
        for j in range(i + 1, min(len(keys), i + _LONGEST_SYLLABLE) + 1):
            piece = keys[i:j]
            if not _is_one_syllable(piece):
                continue
            so_far = parts + [unicodedata.normalize("NFC", "".join(t for _, _, t in piece))]
            if "-".join(so_far).lower() in attested:
                walk(j, so_far)

    walk(0, [])
    return [s for s in out if "-" in s]


def hyphenate(word, attested):
    """word with hyphens between its syllables, when it is not itself one
    syllable and exactly one split of it is a hyphenated form in attested;
    otherwise None."""
    keys = _syllable_keys(word)
    if not keys or _is_one_syllable(keys):
        return None
    found = set(_attested_splits(keys, attested))
    return found.pop() if len(found) == 1 else None


def _ascii_punctuation(text):
    """`（…）！？，` → `(…)!?,`, with the space a following Latin letter needs
    after `!?,.;:` (`Ha--looh！Tâi-uân` → `Ha--looh! Tâi-uân`)."""
    def repl(m):
        ch = chr(ord(m.group(0)) - 0xFEE0)
        nxt = m.string[m.end():m.end() + 1]
        return ch + (" " if ch in "!?,.;:" and nxt and _is_latin(nxt) else "")
    return FULLWIDTH_ASCII.sub(repl, text)


def _dotted_i(text):
    nfd = unicodedata.normalize("NFD", text)
    fixed = GREEK_I_WITH_PSILI.sub("i\u030d", TONED_DOTLESS_I.sub("i", nfd))
    return text if fixed == nfd else unicodedata.normalize("NFC", fixed)


# (name, function) in the order applied; the names are what the report lists.
TEXT_CORRECTIONS = [
    ("full-width punctuation → ASCII", _ascii_punctuation),
    ("o· → o͘", lambda t: O_WITH_DOT.sub(r"\1" + DOT_ABOVE_RIGHT, t)),
    ("ı̍ / ἰ → i̍", _dotted_i),
    ("non-breaking hyphen → -", lambda t: HYPHEN_LOOKALIKES.sub("-", t)),
    ("space before (", lambda t: ATTACHED_PAREN.sub(" (", t)),
]
HYPHENATION = "hyphens between run-together syllables"


def title_text(title, attested):
    """(PojUnicode for title, [names of the corrections made], [(word, split)]).
    `_` is a space, so `Tâi-oân-koān_(1684~1887)` → `Tâi-oân-koān (1684~1887)`."""
    text = title.replace("_", " ")
    made = []
    for name, correct in TEXT_CORRECTIONS:
        fixed = correct(text)
        if fixed != text:
            made.append(name)
            text = fixed

    splits = []

    def repl(m):
        out = []
        for latin, run in itertools.groupby(m.group(0), key=_is_latin):
            run = "".join(run)
            # A word with a tone mark is split when it is not one syllable:
            # `Sūkhek` would otherwise get its number after `khek` (`Sukhek7`).
            if latin and _tone_count(run):
                split = hyphenate(run, attested)
                if split:
                    splits.append((run, split))
                    run = split
            out.append(run)
        return "".join(out)

    text = WORD.sub(repl, text)
    if splits:
        made.append(HYPHENATION)
    return text, made, splits


# --- I/O --------------------------------------------------------------------

def read_titles(dump_path):
    """Yields titles from the dump (gzipped or plain), header dropped."""
    opener = gzip.open if str(dump_path).endswith(".gz") else open
    with opener(dump_path, "rt", encoding="utf-8", newline="\n") as f:
        for n, line in enumerate(f):
            title = line.rstrip("\n")
            if n == 0 and title == DUMP_HEADER:
                continue
            if title:
                yield title


def write_csv(rows, columns, path):
    # utf-8-sig (BOM) so Excel auto-detects UTF-8 — same convention as the
    # sibling mirrors. A header row is always written: the 2024 Kotlin parser
    # wrote none, and the first data row (`!Xóõ-gú`) was eaten as a header
    # downstream, which is why it is missing from the ChhoeTaigi database.
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)


def write_json(payload, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def write_json_rows(rows, path):
    """A JSON array with one compact record per line: 65 MB, where `indent=2`
    — the sibling mirrors' convention — makes 74 MB. Both are past GitHub's
    50 MB warning (under its 100 MB limit); one record per line still diffs
    line by line."""
    with open(path, "w", encoding="utf-8") as f:
        f.write("[\n")
        for i, row in enumerate(rows):
            f.write(json.dumps(row, ensure_ascii=False))
            f.write(",\n" if i < len(rows) - 1 else "\n")
        f.write("]\n")


# --- Report -----------------------------------------------------------------

def _shown(total, shown, noun):
    """`1 distinct title.` / `120 distinct titles; the first 50 are shown.`"""
    text = f"{total:,} {noun}{'' if total == 1 else 's'}"
    return text + (f"; the first {shown} are shown." if shown < total else ".")


def _md_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |",
             "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        cells = [str(c).replace("|", "\\|") for c in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def render_related_md(related, rows):
    c = related["counts"]
    langs = related["languages"]
    names = {"en": "English", "zh": "Chinese (zh-tw)", "ja": "Japanese"}
    empty = rows - c["related_rows"]
    counted = [
        ["Rows with at least one title", c["related_rows"]],
        ["… of which the Pe̍h-ōe-jī title is a redirect", c.get("related_rows_via_redirect", 0)],
        ["… of which it is a redirect with interlanguage links of its own, used",
         c.get("related_rows_own_redirect_links", 0)],
        ["Rows with no title", empty],
    ]
    if c.get("langlinks_not_utf8"):
        counted.append(["Links whose title is not valid UTF-8 — dropped",
                        c["langlinks_not_utf8"]])
    if c.get("api_answers_reused"):
        counted.append(["Linked titles answered from an earlier run (`--resolved`)",
                        c["api_answers_reused"]])
    reasons = [
        ["No interlanguage links at all", c.get("titles_without_links", 0)],
        ["Interlanguage links, but none to en, zh or ja", c.get("titles_linked_elsewhere_only", 0)],
        ["Every en/zh/ja link dropped (per-language table below)",
         c.get("titles_all_links_dropped", 0)],
        ["A redirect to a section", c.get("redirects_to_section", 0)],
        ["A redirect out of the article namespace", c.get("redirects_out_of_articles", 0)],
        ["A broken redirect", c.get("redirects_broken", 0)],
        ["Missing from the page dump", c.get("titles_not_in_page_dump", 0)],
    ]
    unexplained = empty - sum(n for _, n in reasons)
    if unexplained:
        reasons.append(["Unexplained — a bug in this report", unexplained])
    parts = [
        "## 3. English, Chinese and Japanese titles — `EngBun`, `HoaBun`, `JitBun`",
        "",
        "From the interlanguage links of the same dump run (`langlinks`, which",
        "includes Wikidata sitelinks). A title takes the links of the first page",
        "along its redirect chain that has links of its own: usually the article",
        "it leads to, but a redirect that Wikidata attaches to an item of its own",
        "keeps its own (`Bart Simpson`, a redirect to `Nancy Cartwright`, keeps en",
        "`Bart Simpson`). Each linked title is then looked up on its wiki:",
        "redirects there are followed, zh titles are given in the zh-tw variant,",
        "and a link to a section, a missing page or a page that is not an",
        "article is dropped.",
        "",
        _md_table(["", "count"], [[label, f"{n:,}"] for label, n in counted]),
        "",
        "### Rows with no title, and why",
        "",
        _md_table(["", "rows"], [[label, f"{n:,}"] for label, n in reasons if n]),
        "",
        "A redirect to a section (`Jı̍t-pún sî-tāi` → `Tâi-oân le̍k-sú#Jı̍t-pún sî-tāi`,",
        "`48 nî chhut-sì` → `48 nî#Chhut-sì`) is given no titles: the article's",
        "links name the whole article (`History of Taiwan`, `AD 48`), not the",
        "section the title names. Nor is a redirect out of the article namespace",
        "(`0 nî-tāi chhut-sì` → `Category:0 nî-tāi chhut-sì`).",
        "",
        _md_table(["", "column", "rows", "linked page redirected or converted",
                   "link to a section — dropped", "linked page missing — dropped",
                   "linked page not an article — dropped"],
                  [[names[lang], f"`{v['column']}`",
                    f"{v['rows_linked'] - v['rows_section'] - v['rows_missing'] - v['rows_not_article']:,}",
                    f"{v['rows_changed']:,}", f"{v['rows_section']:,}", f"{v['rows_missing']:,}",
                    f"{v['rows_not_article']:,}"]
                   for lang, v in langs.items()]),
        "",
    ]
    for lang, v in langs.items():
        if v["changed"]:
            parts += [
                f"### {names[lang]}: linked title → title of the page it lands on",
                "",
                _md_table(["linked", f"`{v['column']}`"],
                          [[f"`{a}`", f"`{b}`"] for a, b in v["changed"][:REPORT_SAMPLE_SIZE]]),
                "",
                _shown(v["distinct_changed"], min(REPORT_SAMPLE_SIZE, v["distinct_changed"]),
                       "distinct title"),
                "",
            ]
    for lang, v in langs.items():
        if v["section"]:
            parts += [
                f"### {names[lang]}: link names a section",
                "",
                ", ".join(f"`{t}`" for t in v["section"][:REPORT_SAMPLE_SIZE]),
                "",
                _shown(len(v["section"]), min(REPORT_SAMPLE_SIZE, len(v["section"])),
                       "distinct title"),
                "",
            ]
    for lang, v in langs.items():
        if v["not_article"]:
            parts += [
                f"### {names[lang]}: linked page is not an article",
                "",
                _md_table(["linked", "lands on"],
                          [[f"`{a}`", f"`{b}`"] for a, b in v["not_article"][:REPORT_SAMPLE_SIZE]]),
                "",
                _shown(len(v["not_article"]), min(REPORT_SAMPLE_SIZE, len(v["not_article"])),
                       "distinct title"),
                "",
            ]
    for lang, v in langs.items():
        if v["missing"]:
            parts += [
                f"### {names[lang]}: linked page does not exist",
                "",
                ", ".join(f"`{t}`" for t in v["missing"][:REPORT_SAMPLE_SIZE]),
                "",
                _shown(len(v["missing"]), min(REPORT_SAMPLE_SIZE, len(v["missing"])),
                       "distinct title"),
                "",
            ]
    parts += [
        f"Full lists are in `{REPORT_NAME}.json`.",
        "",
    ]
    return parts


def render_report_md(report, source_name):
    c = report["counts"]
    parts = [
        f"# {REPORT_NAME}",
        "",
        f"Source dump: `{source_name}`",
        "",
        "## Counts",
        "",
        _md_table(["", "count"], [
            ["Namespace-0 titles in dump", f"{c['titles_total']:,}"],
            ["Titles kept (contain Pe̍h-ōe-jī)", f"{c['titles_kept']:,}"],
            ["Titles dropped", f"{c['titles_dropped']:,}"],
            ["Rows merged into another (same text, same article)", f"{c['rows_merged']:,}"],
            ["Rows published", f"{c['rows']:,}"],
            ["… whose text was corrected", f"{c['rows_text_corrected']:,}"],
            ["… with a multi-tone word", f"{c['rows_multi_tone']:,}"],
            ["… with a caron on a tone-bearing letter", f"{c['rows_caron']:,}"],
        ]),
        "",
        "Namespace-0 titles include redirects. The dump does not mark them, so",
        "both a redirect and its target are kept — e.g. `'Amran-séng`,",
        "`'Amran Séng` and `'Amran séng` are all present. Only rows whose",
        "corrected text is identical and that lead to the same article are",
        "merged, keeping the article's own row: `10 goe̍h 10 ji̍t (kūle̍k)` and",
        "`10 goe̍h 10 ji̍t (kū-le̍k)` are one row. Every merge is listed in",
        f"`{REPORT_NAME}.json`.",
        "",
        "## 1. Title text — corrections",
        "",
        "`PojUnicode` is the title made as good as possible for finding by",
        "Pe̍h-ōe-jī; `LaigoanBangchi` keeps the exact page. `_` is a space",
        "(`Tâi-oân-koān (1684~1887)`), and these corrections were made:",
        "",
        _md_table(["correction", "rows"],
                  [[name, f"{n:,}"] for name, n in report["corrections"] if n]),
        "",
        "Run-together syllables are split only into a hyphenated form that",
        "Wikipedia's own titles use somewhere, so a foreign name that happens to",
        "parse as syllables (`Hélène`) is never split, and that form decides",
        "between two parses (`sîtāi` → `sî-tāi`, not `sît-āi`).",
        "",
    ]
    splits = report.get("hyphenated_words") or []
    if splits:
        parts += [
            _md_table(["written", "`PojUnicode`", "rows"],
                      [[f"`{w}`", f"`{sp}`", n] for w, sp, n in splits[:REPORT_SAMPLE_SIZE]]),
            "",
            _shown(len(splits), min(REPORT_SAMPLE_SIZE, len(splits)), "distinct word")
            + f" Every corrected row is in `{REPORT_NAME}.json`.",
            "",
        ]
    parts += [
        "## 2. Multi-tone words — `PojInput` left unconverted",
        "",
        "A Pe̍h-ōe-jī syllable carries at most one tone mark. These words carry",
        "two or more and could not be split into syllables: mostly foreign names",
        "(`Pyrénées`, `Józefów`), kept because another part of their title is a",
        "syllable, and a few run-together syllables no title writes hyphenated.",
        "There is no single tone number to append, so the word is copied into",
        "`PojInput` as-is rather than guessed at.",
        "",
    ]
    total = len(report["multi_tone_words_all"])
    if total:
        parts += [
            _md_table(["word", "titles"],
                      [[f"`{w}`", n] for w, n in report["multi_tone_words"]]),
            "",
            (f"{total:,} distinct multi-tone words; the {len(report['multi_tone_words'])} "
             f"most frequent are shown. The full list is in `{REPORT_NAME}.json`."
             if len(report["multi_tone_words"]) < total
             else _shown(total, total, "distinct multi-tone word")),
            "",
        ]
    caron = report.get("caron_titles") or []
    if caron:
        parts += [
            "### Caron on a tone-bearing letter — left as written",
            "",
            "A caron (`ǔ`, `ě`) is not read as a tone mark, as in KonvertToPOJ: no",
            "number is appended for it. Most are Czech and Slovak names (`Moravě`);",
            "a few are Taigi written with a tone-6 caron (`Diô-jiǔ-oē`).",
            "",
            ", ".join(f"`{t}`" for t in caron[:REPORT_SAMPLE_SIZE]),
            "",
            _shown(len(caron), min(REPORT_SAMPLE_SIZE, len(caron)), "title"),
            "",
        ]
    if report.get("related"):
        parts += render_related_md(report["related"], c["rows"])
    return "\n".join(parts)


# --- Entry point ------------------------------------------------------------

def merge_same_article(entries, landing):
    """entries minus the rows that repeat another row's PojUnicode and lead
    to the same article: one search result each. Kept: the article's own row,
    else the one whose title needed no correction, else the first. Returns
    (kept entries, [(merged entry, entry it went into)])."""
    groups = collections.defaultdict(list)
    for i, e in enumerate(entries):
        page, _ = landing.get(e["title"], (None, False))
        groups[(e["row"]["PojUnicode"], page if page is not None else e["title"])].append(i)
    merged, drop = [], set()
    for members in groups.values():
        if len(members) < 2:
            continue
        keep = min(members, key=lambda i: (landing[entries[i]["title"]][1],
                                            bool(entries[i]["made"]), i))
        for i in members:
            if i != keep:
                drop.add(i)
                merged.append((entries[i], entries[keep]))
    return [e for i, e in enumerate(entries) if i not in drop], merged


def convert_titles(dump_path, bunji_dir, report_dir=None, relate=None, landing=None):
    """Builds bunji/WikipediaPehoeji.{csv,json} and the report. Returns counts.

    relate: optional callable(titles) → ({title: {EngBun, HoaBun, JitBun}},
    report dict), as related_titles.related_titles. Without it those three
    columns are left empty.
    landing: optional callable(titles) → {title: (landing page id, is a
    redirect)}, as related_titles.landing_pages. With it, rows with the same
    PojUnicode that lead to the same article are merged into one."""
    dump_path = Path(dump_path)
    bunji_dir = Path(bunji_dir)
    report_dir = Path(report_dir) if report_dir else bunji_dir.parent
    bunji_dir.mkdir(parents=True, exist_ok=True)

    titles = list(read_titles(dump_path))
    attested = attested_hyphenations(titles)
    entries = []
    for title in titles:
        if not contains_poj(title):
            continue
        poj, made, splits = title_text(title, attested)
        poj_input, multi = poj_unicode_to_input(poj)
        entries.append({"title": title, "made": made, "splits": splits, "multi": multi,
                        "row": {"PojUnicode": poj, "PojInput": poj_input,
                                "LaigoanBangchi": title_to_url(title)}})
    titles_kept = len(entries)
    merged = []
    if landing:
        entries, merged = merge_same_article(entries, landing([e["title"] for e in entries]))

    kept = [e["title"] for e in entries]
    rows = [e["row"] for e in entries]
    related, related_report = {}, None
    if relate:
        related, related_report = relate(kept)
    no_titles = dict.fromkeys(LANG_COLUMNS.values(), "")
    for title, row in zip(kept, rows):
        row.update(related.get(title, no_titles))

    write_csv(rows, COLUMNS, bunji_dir / f"{TABLE_NAME}.csv")
    write_json_rows(rows, bunji_dir / f"{TABLE_NAME}.json")

    multi_counter = collections.Counter()
    correction_counts = collections.Counter()
    split_counter = collections.Counter()
    for e in entries:
        multi_counter.update(set(e["multi"]))
        correction_counts.update(e["made"])
        split_counter.update(set(e["splits"]))
    caron_rows = [row["PojUnicode"] for row in rows if _has_caron_on_bearer(row["PojUnicode"])]
    corrected = [{"LaigoanBangchi": e["row"]["LaigoanBangchi"], "title": e["title"].replace("_", " "),
                  "PojUnicode": e["row"]["PojUnicode"], "corrections": e["made"]}
                 for e in entries if e["made"]]
    counts = {
        "titles_total": len(titles),
        "titles_kept": titles_kept,
        "titles_dropped": len(titles) - titles_kept,
        "rows_merged": len(merged),
        "rows": len(rows),
        "rows_text_corrected": len(corrected),
        **{f"rows_corrected: {name}": n for name, n in correction_counts.items()},
        "rows_multi_tone": sum(1 for e in entries if e["multi"]),
        "multi_tone_distinct_words": len(multi_counter),
        "rows_caron": len(caron_rows),
    }
    if related_report:
        counts.update(related_report["counts"])
    ranked = sorted(multi_counter.items(), key=lambda kv: (-kv[1], kv[0]))
    report = {
        "counts": counts,
        "corrections": [[name, correction_counts[name]] for name, _ in TEXT_CORRECTIONS]
                       + [[HYPHENATION, correction_counts[HYPHENATION]]],
        "hyphenated_words": [[w, sp, n] for (w, sp), n in
                             sorted(split_counter.items(), key=lambda kv: (-kv[1], kv[0]))],
        "corrected_rows": corrected,
        "merged_rows": [{"PojUnicode": a["row"]["PojUnicode"],
                         "LaigoanBangchi": a["row"]["LaigoanBangchi"],
                         "into": b["row"]["LaigoanBangchi"]} for a, b in merged],
        "multi_tone_words": ranked[:REPORT_SAMPLE_SIZE],
        "multi_tone_words_all": ranked,
        "caron_titles": caron_rows,
        "related": related_report,
    }
    write_json(report, report_dir / f"{REPORT_NAME}.json")
    with open(report_dir / f"{REPORT_NAME}.md", "w", encoding="utf-8") as f:
        f.write(render_report_md(report, dump_path.name))

    print(f"  {len(titles):,} titles → {titles_kept:,} with Pe̍h-ōe-jī → {len(rows):,} rows "
          f"({len(merged):,} merged, {len(corrected):,} with corrected text, "
          f"{counts['rows_multi_tone']:,} with a multi-tone word)")
    if related_report:
        print(f"  {counts['related_rows']:,} rows with an English, Chinese or Japanese title")
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dump", help="all-titles-in-ns0 dump (.gz or plain)")
    parser.add_argument("bunji_dir", help="output directory for the tables")
    parser.add_argument(
        "--related", action="store_true",
        help="fill EngBun/HoaBun/JitBun from the page/redirect/langlinks dumps "
             "beside DUMP, and merge rows with the same text that lead to the "
             "same article; queries the en, zh and ja Wikipedia APIs. Without "
             "it the columns are left empty and nothing is merged")
    parser.add_argument(
        "--resolved", metavar="PATH",
        help="with --related: reuse the …-langlinks-resolved.json of an earlier "
             "run instead of querying the APIs again. Each run with --related "
             "saves its own beside BUNJI_DIR")
    args = parser.parse_args()
    if args.resolved and not args.related:
        parser.error("--resolved needs --related")
    # Titles and arrows must not crash a run on a terminal that is not UTF-8.
    sys.stdout.reconfigure(errors="backslashreplace")
    relate = landing = None
    if args.related:
        landing = functools.partial(landing_pages, titles_dump=args.dump)
        # Beside the report, as update_data keeps them beside the tables. Saved
        # even when the lookups fail, for the next run's --resolved.
        save_to = Path(args.bunji_dir).parent / answers_name(args.dump)
        print(f"API answers will be saved to {save_to}")
        relate = functools.partial(related_titles, titles_dump=args.dump,
                                   resolved_cache=args.resolved, save_resolved=save_to)
    counts = convert_titles(args.dump, args.bunji_dir, relate=relate, landing=landing)
    if args.related and counts["related_rows"] == 0:
        print("No row has an English, Chinese or Japanese title — the dumps beside "
              f"{args.dump} or the APIs failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
