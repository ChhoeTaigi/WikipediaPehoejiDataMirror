"""Find the English, Chinese (Taiwan) and Japanese Wikipedia articles each
Pe̍h-ōe-jī title leads to.

The zh-min-nan dumps of the same run give the interlanguage links: `page` maps
titles to page ids and flags redirects, `redirect` gives each redirect's
target, `langlinks` maps a page id to the title of the same subject on another
wiki (Wikidata sitelinks included). A Pe̍h-ōe-jī redirect takes the links of
the article it leads to, unless it has links of its own.

The linked titles are then looked up on each wiki's API, 50 per request. A
link may point at a redirect there (`Tang-kiaⁿ` links to en `Tokyo Proper`,
which redirects to `Tokyo`), and zh Wikipedia stores each title in whichever
script its article was created in, so zh titles are given in their zh-tw
variant (`东京` → `東京`).
"""
import collections
import functools
import gzip
import http.client
import json
import os
import re
import threading
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

USER_AGENT = "ChhoeTaigi-WikipediaPehoejiDataMirror/1.0 (https://github.com/ChhoeTaigi)"

# Wiki language code → ChhoeTaigi database column. The database already has
# these columns for every dictionary; Wikipedia rows have left them empty.
LANG_COLUMNS = {"en": "EngBun", "zh": "HoaBun", "ja": "JitBun"}
# zh Wikipedia serves one page under several script variants; HoaBun is the
# Taiwan one.
ZH_VARIANT = "zh-tw"
ARTICLE_NS = 0

API_HOST = "{lang}.wikipedia.org"
API_PATH = "/w/api.php"
API_HEADERS = {"User-Agent": USER_AGENT,
               "Content-Type": "application/x-www-form-urlencoded"}
# Titles per query: the API's limit for clients without the apihighlimits right.
API_BATCH = 50
API_RETRIES = 5
API_BACKOFF_SECONDS = 5
API_TIMEOUT = 60
# Ask the API to refuse work while replication lag is high, as Wikimedia's
# etiquette asks of non-interactive clients. A refusal is retried after its
# Retry-After without using up one of API_RETRIES, for up to this long.
API_MAXLAG = "5"
API_MAXLAG_PATIENCE_SECONDS = 600
# An HTTP 429/503 with Retry-After is retried after that long (capped here),
# not after the usual backoff.
API_RETRY_AFTER_MAX_SECONDS = 300
PROGRESS_EVERY = 500  # batches

# Redirect chains on zh-min-nan longer than this many hops are treated as broken.
MAX_REDIRECT_HOPS = 5

# Version of the saved API answers (…-langlinks-resolved.json). Answers saved
# in another format are not reused.
ANSWERS_FORMAT = 2
ANSWERS_SUFFIX = "-resolved.json"

# --- Dumps ------------------------------------------------------------------

SQL_DUMPS = ("page", "redirect", "langlinks")
TITLES_DUMP_SUFFIX = re.compile(r"all-titles-in-ns0(\.gz)?$")


def sql_dump_path(titles_dump, name):
    """`…-20261001-all-titles-in-ns0.gz` → `…-20261001-{name}.sql.gz`, beside it."""
    titles_dump = Path(titles_dump)
    sql_name, found = TITLES_DUMP_SUFFIX.subn(f"{name}.sql.gz", titles_dump.name)
    if not found:
        raise ValueError(f"{titles_dump.name} is not an …-all-titles-in-ns0[.gz] dump, "
                         f"so the {name} dump of its run cannot be found")
    return titles_dump.with_name(sql_name)


def answers_name(titles_dump):
    """`…-20261001-all-titles-in-ns0.gz` → `…-20261001-langlinks-resolved.json`,
    the name the API answers for that run are saved under."""
    return sql_dump_path(titles_dump, "langlinks").name.replace(".sql.gz", ANSWERS_SUFFIX)


# One row of each table as mysqldump writes it. Only the leading columns are
# read, so a column added at the end does not break a pattern. finditer()
# works whether a line holds one row or a whole INSERT.
_STR = r"'((?:[^'\\]|\\.)*)'"
_OPT_STR = r"(?:NULL|" + _STR + r")"
PAGE_ROW = re.compile(r"\((\d+),(-?\d+)," + _STR + r",([01]),")
REDIRECT_ROW = re.compile(r"\((\d+),(-?\d+)," + _STR + "," + _OPT_STR + "," + _OPT_STR + r"[,)]")
LANGLINK_ROW = re.compile(r"\((\d+),'([^'\\]*)'," + _STR + r"[,)]")
_ESCAPE = re.compile(r"\\(.)")


def _unescape(s):
    return _ESCAPE.sub(r"\1", s) if "\\" in s else s


def _is_utf8(s):
    """False for text that held bytes which were not UTF-8: the dumps are read
    with surrogateescape, and such a title cannot even be sent to an API."""
    try:
        s.encode("utf-8")
        return True
    except UnicodeEncodeError:
        return False


def _sql_rows(path, pattern):
    with gzip.open(path, "rt", encoding="utf-8", errors="surrogateescape") as f:
        for line in f:
            if line.startswith(("(", "INSERT")):
                yield from pattern.finditer(line)


@functools.lru_cache(maxsize=1)
def _page_tables(titles_dump):
    """({ns-0 title: (page id, is_redirect)}, {redirect page id: (ns, target,
    interwiki, fragment)}), read once per dump run and shared."""
    pages = {}
    for m in _sql_rows(sql_dump_path(titles_dump, "page"), PAGE_ROW):
        if m.group(2) == "0":
            pages[_unescape(m.group(3))] = (int(m.group(1)), m.group(4) == "1")
    redirects = {}
    for m in _sql_rows(sql_dump_path(titles_dump, "redirect"), REDIRECT_ROW):
        pid, ns, target, interwiki, fragment = m.groups()
        redirects[int(pid)] = (ns, _unescape(target), interwiki, fragment)
    return pages, redirects


def landing_pages(titles, titles_dump):
    """{title: (id of the page a reader of title lands on, or None, title is a
    redirect)}. Unlike the links, a redirect to a section lands on its page."""
    pages, redirects = _page_tables(str(titles_dump))
    out = {}
    for title in titles:
        page = pages.get(title)
        if page is None:
            out[title] = (None, False)
            continue
        pid, is_redirect = page
        # At most MAX_REDIRECT_HOPS hops, as in read_langlinks' chain().
        for _ in range(MAX_REDIRECT_HOPS):
            if not is_redirect:
                break
            ns, target, interwiki, _ = redirects.get(pid, (None, None, None, None))
            if ns != "0" or interwiki or target not in pages:
                break
            pid, is_redirect = pages[target]
        out[title] = (None if is_redirect else pid, page[1])
    return out


def read_langlinks(titles_dump, titles):
    """({title: {lang: linked title}} for the titles with any en/zh/ja link,
    the set of titles that are redirects, the set of titles that take a
    redirect's own links, counts — of every title given no links, by why).

    A title takes the links of the first page along its redirect chain that
    has interlanguage links of its own, in any language: the article it leads
    to, or a redirect that Wikidata attaches to an item of its own —
    `Bart Simpson` redirects to `Nancy Cartwright` but is linked to en
    `Bart Simpson`, and keeps that. Without such a page, a chain that stops at
    a redirect to a section gives no links (`Jı̍t-pún sî-tāi` →
    `Tâi-oân le̍k-sú#Jı̍t-pún sî-tāi` would be given en `History of Taiwan`),
    as does one that leaves the article namespace or reaches a missing page.
    """
    pages, redirects = _page_tables(str(titles_dump))

    def chain(title):
        """(page ids from title's page along its redirect chain, why the chain
        stopped short of an article, or None when it reached one)."""
        page = pages.get(title)
        if page is None:
            return [], "titles_not_in_page_dump"
        pid, is_redirect = page
        ids = [pid]
        while is_redirect:
            if len(ids) > MAX_REDIRECT_HOPS:
                return ids, "redirects_broken"
            ns, target, interwiki, fragment = redirects.get(pid, (None, None, None, None))
            if fragment:
                return ids, "redirects_to_section"
            if interwiki or (ns is not None and ns != "0"):
                return ids, "redirects_out_of_articles"
            if ns is None or target not in pages:
                return ids, "redirects_broken"
            pid, is_redirect = pages[target]
            ids.append(pid)
        return ids, None

    chains = {title: chain(title) for title in titles}
    wanted_ids = {pid for ids, _ in chains.values() for pid in ids}

    counts = collections.Counter()
    has_links = set()
    links = collections.defaultdict(dict)
    for m in _sql_rows(sql_dump_path(titles_dump, "langlinks"), LANGLINK_ROW):
        pid = int(m.group(1))
        if pid in wanted_ids:
            has_links.add(pid)
            lang, linked = m.group(2), _unescape(m.group(3))
            if lang in LANG_COLUMNS and linked:
                if not _is_utf8(linked):
                    counts["langlinks_not_utf8"] += 1
                    continue
                links[pid][lang] = linked

    redirect_titles = {t for t in titles if t in pages and pages[t][1]}
    redirect_ids = {pid for pid, is_redirect in pages.values() if is_redirect}
    result, own_link_titles = {}, set()
    for title, (ids, stopped) in chains.items():
        source = next((pid for pid in ids if pid in has_links), None)
        if source is None:
            counts[stopped or "titles_without_links"] += 1
        elif not links.get(source):
            counts["titles_linked_elsewhere_only"] += 1
        else:
            result[title] = links[source]
            if source in redirect_ids:
                own_link_titles.add(title)
    return result, redirect_titles, own_link_titles, counts


# --- API --------------------------------------------------------------------

class _Stopped(Exception):
    """Another wiki's lookup failed, or Ctrl-C: stop this one too."""


class _HttpError(http.client.HTTPException):
    """A non-200 answer, with the server's Retry-After in seconds, if any."""

    def __init__(self, status, retry_after):
        super().__init__(f"HTTP {status}")
        self.retry_after = retry_after


class _Api:
    """One kept-alive HTTPS connection to one wiki's API. Not thread-safe:
    each wiki gets its own, and queries on it are made one after another.
    Every wait ends early, raising _Stopped, once `stop` is set."""

    def __init__(self, lang, stop):
        self.host = API_HOST.format(lang=lang)
        self.stop = stop
        self.conn = None

    def _sleep(self, seconds):
        if self.stop.wait(seconds):
            raise _Stopped

    def _post(self, body):
        """One request → (parsed JSON, Retry-After seconds or None). Any
        failure drops the connection, so the next request reconnects."""
        try:
            if self.conn is None:
                self.conn = http.client.HTTPSConnection(self.host, timeout=API_TIMEOUT)
            self.conn.request("POST", API_PATH, body, API_HEADERS)
            resp = self.conn.getresponse()
            data = resp.read()
            retry_after = resp.getheader("Retry-After") or ""
            retry_after = int(retry_after) if retry_after.isdigit() else None
            if resp.status != 200:
                raise _HttpError(resp.status, retry_after)
            return json.loads(data), retry_after
        except BaseException:
            if self.conn is not None:
                self.conn.close()
                self.conn = None
            raise

    def query(self, params):
        body = urllib.parse.urlencode({
            "action": "query", "format": "json", "formatversion": "2",
            "maxlag": API_MAXLAG, **params,
        })
        attempt, lag_waited = 0, 0
        while True:
            if self.stop.is_set():
                raise _Stopped
            try:
                payload, retry_after = self._post(body)
                # Anything but the shape the API documents is retried, not
                # trusted: a middlebox page, or an API change.
                if not isinstance(payload, dict):
                    raise ValueError(f"unexpected answer: {str(payload)[:80]}")
                error = payload.get("error")
                if error is not None and not (isinstance(error, dict)
                                              and error.get("code") == "maxlag"):
                    code = error.get("code") if isinstance(error, dict) else None
                    info = error.get("info") if isinstance(error, dict) else error
                    raise RuntimeError(f"API error {code}: {info}")
                result = payload.get("query", {})
                if not isinstance(result, dict):
                    raise ValueError(f"unexpected query: {str(result)[:80]}")
            except (OSError, http.client.HTTPException, ValueError, RuntimeError) as e:
                attempt += 1
                if attempt >= API_RETRIES:
                    raise RuntimeError(
                        f"Giving up on {self.host} after {API_RETRIES} attempts: {e}") from e
                wait = API_BACKOFF_SECONDS * attempt
                if isinstance(e, _HttpError) and e.retry_after:
                    # 429/503: wait as long as the server asked, within reason.
                    wait = max(wait, min(e.retry_after, API_RETRY_AFTER_MAX_SECONDS))
                self._sleep(wait)
                continue
            if error is None:
                return result
            wait = retry_after or API_BACKOFF_SECONDS
            lag_waited += wait
            if lag_waited > API_MAXLAG_PATIENCE_SECONDS:
                raise RuntimeError(f"Giving up on {self.host}: replication lag above "
                                   f"{API_MAXLAG} s for over {API_MAXLAG_PATIENCE_SECONDS} s")
            self._sleep(wait)


def _resolve_batch(api, lang, titles):
    """{title: [namespace, title of the page it lands on], or None when there
    is no such page}. For zh the title is the zh-tw variant."""
    params = {"titles": "|".join(titles), "redirects": "1"}
    if lang == "zh":
        params.update(prop="info", inprop="varianttitles")
    q = api.query(params)
    alias = {}
    for step in q.get("normalized", []) + q.get("redirects", []):
        alias[step["from"]] = step["to"]
    landed = {}
    for p in q.get("pages", []):
        if p.get("missing") or p.get("invalid"):
            continue
        title = p["title"]
        if lang == "zh" and not p.get("special"):
            # Every real zh page has one, in every namespace: its absence
            # means the API changed, and HoaBun would silently keep stored
            # titles. Special: and Media: pages (ns -1, -2) are virtual and
            # have none; they are not articles, so they are dropped anyway.
            title = p.get("varianttitles", {}).get(ZH_VARIANT)
            if title is None:
                raise RuntimeError(f"zh API gave no {ZH_VARIANT} title for {p['title']!r}")
        landed[p["title"]] = [p["ns"], title]
    out = {}
    for t in titles:
        cur, seen = t, set()
        while cur in alias and cur not in seen:
            seen.add(cur)
            cur = alias[cur]
        out[t] = landed.get(cur)
    return out


def resolve_titles(wanted, answers):
    """Looks up every title of wanted ({lang: titles}) not yet in answers
    ({lang: {title: answer}}), adding to answers in place. Each wiki is
    queried by its own thread, one request at a time. When one wiki fails, or
    on Ctrl-C, the others stop at their next request, so answers holds all
    that was fetched when the exception propagates."""
    stop = threading.Event()
    print_lock = threading.Lock()

    def run(lang):
        api = _Api(lang, stop)
        todo = sorted(t for t in wanted[lang] if t not in answers[lang])
        batches = (len(todo) + API_BATCH - 1) // API_BATCH
        with print_lock:
            print(f"  {lang}: {len(wanted[lang]):,} linked titles, "
                  f"{len(todo):,} to look up ({batches:,} queries)")
        try:
            for n, i in enumerate(range(0, len(todo), API_BATCH), 1):
                if stop.is_set():
                    return
                answers[lang].update(_resolve_batch(api, lang, todo[i:i + API_BATCH]))
                if n % PROGRESS_EVERY == 0:
                    with print_lock:
                        print(f"  {lang}: {n:,}/{batches:,} queries")
        except _Stopped:
            pass

    pool = ThreadPoolExecutor(max_workers=len(wanted))
    try:
        for future in as_completed([pool.submit(run, lang) for lang in wanted]):
            future.result()
    except BaseException:
        stop.set()
        raise
    finally:
        # Every request in flight finishes before answers is read, even
        # through a second Ctrl-C: a reply is at most API_TIMEOUT away.
        while True:
            try:
                pool.shutdown(wait=True)
                break
            except KeyboardInterrupt:
                stop.set()
                print(f"  Waiting for the requests in flight (at most {API_TIMEOUT} s)...")


def load_answers(path):
    """{lang: {title: answer}} saved by an earlier run, or {} when it was
    saved in another format."""
    with open(path, encoding="utf-8") as f:
        saved = json.load(f)
    if not isinstance(saved, dict) or saved.get("format") != ANSWERS_FORMAT:
        print(f"  {Path(path).name} is not in answer format {ANSWERS_FORMAT}; not reused.")
        return {}
    return saved["answers"]


def save_answers(answers, path):
    """Written to a .part file and renamed, so an interruption mid-write —
    this runs while a failure or Ctrl-C unwinds — never leaves a cut-off
    answers file in place of a good one."""
    path = Path(path)
    part = path.with_name(path.name + ".part")
    with open(part, "w", encoding="utf-8") as f:
        json.dump({"format": ANSWERS_FORMAT,
                   "answers": {lang: dict(sorted(a.items())) for lang, a in answers.items()}},
                  f, ensure_ascii=False, indent=0)
    os.replace(part, path)


# --- Entry point ------------------------------------------------------------

def related_titles(titles, titles_dump, resolved_cache=None, save_resolved=None):
    """{title: {EngBun, HoaBun, JitBun}} for each of titles linked to at least
    one of the three wikis, and a report dict.

    resolved_cache: answers saved by an earlier run (save_resolved). Those for
    titles still linked are reused; a page that was missing is looked up
    again. A development shortcut — a reused answer can be stale, and the
    report counts how many were reused. save_resolved is written even when
    the lookups fail, so a rerun can pick up where this one stopped.
    """
    links, redirect_titles, own_link_titles, counts = read_langlinks(titles_dump, titles)
    # A link that names a section (`蓮池潭#龍虎塔`, the pagodas in the lake)
    # is never looked up: the article it is in names something else.
    wanted = {lang: {ls[lang] for ls in links.values() if lang in ls and "#" not in ls[lang]}
              for lang in LANG_COLUMNS}

    answers = {lang: {} for lang in LANG_COLUMNS}
    if resolved_cache:
        saved = load_answers(resolved_cache)
        for lang in LANG_COLUMNS:
            for title in wanted[lang]:
                answer = saved.get(lang, {}).get(title)
                if answer is not None:
                    answers[lang][title] = answer
    counts["api_answers_reused"] = sum(len(a) for a in answers.values())
    try:
        resolve_titles(wanted, answers)
    finally:
        if save_resolved:
            save_answers(answers, save_resolved)

    related = {}
    per_lang = {lang: collections.Counter() for lang in LANG_COLUMNS}
    changed = {lang: {} for lang in LANG_COLUMNS}
    missing = {lang: set() for lang in LANG_COLUMNS}
    not_article = {lang: {} for lang in LANG_COLUMNS}
    section = {lang: set() for lang in LANG_COLUMNS}
    for title, ls in links.items():
        row = dict.fromkeys(LANG_COLUMNS.values(), "")
        for lang, column in LANG_COLUMNS.items():
            linked = ls.get(lang)
            if not linked:
                continue
            per_lang[lang]["linked"] += 1
            if "#" in linked:
                per_lang[lang]["section"] += 1
                section[lang].add(linked)
                continue
            answer = answers[lang][linked]
            if answer is None:
                per_lang[lang]["missing"] += 1
                missing[lang].add(linked)
                continue
            ns, landed = answer
            if ns != ARTICLE_NS:
                # A category, portal or template page is not an article, and
                # zh's variant even translates its prefix (`分類:…`).
                per_lang[lang]["not_article"] += 1
                not_article[lang][linked] = landed
                continue
            row[column] = landed
            if landed != linked:
                per_lang[lang]["changed"] += 1
                changed[lang][linked] = landed
        if any(row.values()):
            related[title] = row
        else:
            counts["titles_all_links_dropped"] += 1

    counts["related_rows"] = len(related)
    counts["related_rows_via_redirect"] = len(related.keys() & redirect_titles)
    counts["related_rows_own_redirect_links"] = len(related.keys() & own_link_titles)
    for column in LANG_COLUMNS.values():
        counts[f"related_rows_{column}"] = sum(1 for r in related.values() if r[column])
    report = {
        "counts": dict(counts),
        "languages": {
            lang: {
                "column": LANG_COLUMNS[lang],
                "rows_linked": per_lang[lang]["linked"],
                "rows_changed": per_lang[lang]["changed"],
                "rows_missing": per_lang[lang]["missing"],
                "rows_not_article": per_lang[lang]["not_article"],
                "rows_section": per_lang[lang]["section"],
                "distinct_linked": len(wanted[lang]),
                "distinct_changed": len(changed[lang]),
                "changed": sorted(changed[lang].items()),
                "missing": sorted(missing[lang]),
                "not_article": sorted(not_article[lang].items()),
                "section": sorted(section[lang]),
            }
            for lang in LANG_COLUMNS
        },
    }
    return related, report
