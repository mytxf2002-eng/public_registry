"""Link health: check every resource URL and keep a state per resource in health/status.json.

A single failed check never marks a resource as failing. The state machine (hysteresis):

    working, no content signal      -> verified    (failures = 0, last_ok = today)
    working, with a content signal  -> suspicious  (cross-site redirect, parked or gambling page)
    not working                     -> failures + 1; failing once at least 3 checks in a row have failed
                                       and the first of them was at least 7 days ago; until then the
                                       previous state is kept, or `unconfirmed` for a resource that has
                                       never been seen working

401, 403, 405, 406, 429 and bot-check pages count as working: the service is there, it only asks for
credentials or rate limits us. health/acknowledged.yml records what the maintainer has checked by hand:
`signals` that are harmless for a resource (they stop raising `suspicious`) and `results` that the
resource gives automated clients although it works in a browser (they count as `restricted`).
"""
import datetime as dt
import html
import os
import re
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

import requests

from . import urls, yamlio

USER_AGENT = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
              'Chrome/140.0.0.0 Safari/537.36')
TIMEOUT = (10, 25)
MAX_PER_HOST = 2
RETRIES = 2
BODY_LIMIT = 262_144
FAIL_AFTER_CHECKS = 3
FAIL_AFTER_DAYS = 7

OK, RESTRICTED = 'ok', 'restricted'
NOT_FOUND, CLIENT_ERROR, SERVER_ERROR = 'not_found', 'client_error', 'server_error'
DNS_ERROR, REFUSED, SSL_ERROR, TIMEOUT_ERROR = 'dns_error', 'refused', 'ssl_error', 'timeout'
TOO_MANY_REDIRECTS, CONNECTION_ERROR, UNKNOWN_ERROR = 'too_many_redirects', 'connection_error', 'unknown_error'
WORKING = {OK, RESTRICTED}
FAILED_RESULTS = (NOT_FOUND, CLIENT_ERROR, SERVER_ERROR, DNS_ERROR, REFUSED, SSL_ERROR, TIMEOUT_ERROR,
                  TOO_MANY_REDIRECTS, CONNECTION_ERROR, UNKNOWN_ERROR)
SIGNALS = ('cross-site-redirect', 'parked-or-gambling')
TRANSIENT = {SERVER_ERROR, TIMEOUT_ERROR, CONNECTION_ERROR, DNS_ERROR}
RESTRICTED_CODES = {401, 403, 405, 406, 429}

DNS_HINTS = ('NameResolutionError', 'Name or service not known', 'nodename nor servname', 'getaddrinfo failed',
             'No address associated with hostname', 'Temporary failure in name resolution', 'Failed to resolve')
REFUSED_HINTS = ('Connection refused', 'ConnectionRefusedError', 'actively refused', '[Errno 111]', '[WinError 10061]')
BOT_CHECK_RE = re.compile(r'Just a moment\.\.\.|cf-chl|_cf_chl|Checking your browser|DDoS protection by|'
                          r'Attention Required! \| Cloudflare|captcha-delivery|Incapsula incident', re.I)
PARKED_RE = re.compile(
    r'this domain (name )?(is|may be) for sale|buy this domain|domain is for sale|hugedomains\.com|sedoparking|'
    r'parkingcrew|bodis\.com|afternic\.com|dan\.com/buy-domain|domain has expired|'
    r'slot gacor|situs slot|situs toto|togel online|judi online|casino online|agen slot|nhà cái|'
    r'카지노|토토사이트|bandar togel', re.I)
TITLE_RE = re.compile(r'<title[^>]*>([^<]{0,300})</title>', re.I)


def classify_exception(error):
    if isinstance(error, requests.exceptions.SSLError):
        return SSL_ERROR
    if isinstance(error, requests.exceptions.Timeout):          # before ConnectionError: ConnectTimeout is both
        return TIMEOUT_ERROR
    if isinstance(error, requests.exceptions.TooManyRedirects):
        return TOO_MANY_REDIRECTS
    if isinstance(error, requests.exceptions.ConnectionError):
        text = repr(error)
        if any(h in text for h in DNS_HINTS):
            return DNS_ERROR
        if any(h in text for h in REFUSED_HINTS):
            return REFUSED
        return CONNECTION_ERROR
    return UNKNOWN_ERROR


def classify_status(code, body=''):
    if code < 400:
        return OK
    if code in RESTRICTED_CODES or (code == 503 and BOT_CHECK_RE.search(body or '')):
        return RESTRICTED
    if code in (404, 410):
        return NOT_FOUND
    return SERVER_ERROR if code >= 500 else CLIENT_ERROR


def content_signals(url, final_url, body):
    signals = []
    if final_url and urls.site(final_url) != urls.site(url):
        signals.append(SIGNALS[0])
    if body and PARKED_RE.search(body):
        signals.append(SIGNALS[1])
    return signals


def decode(raw, encoding):
    """Text of a response body; an unknown or bogus charset falls back to UTF-8."""
    try:
        return raw.decode(encoding or 'utf-8', errors='replace')
    except LookupError:
        return raw.decode('utf-8', errors='replace')


def request_once(url):
    try:
        with requests.get(url, headers={'User-Agent': USER_AGENT, 'Accept': 'text/html,application/json;q=0.9,*/*;q=0.8'},
                          timeout=TIMEOUT, stream=True, allow_redirects=True) as r:
            ctype = r.headers.get('Content-Type', '').lower()
            body = ''
            if 'html' in ctype or 'text' in ctype or not ctype:
                chunks, size, start = [], 0, time.time()
                for chunk in r.iter_content(16384):
                    chunks.append(chunk)
                    size += len(chunk)
                    if size >= BODY_LIMIT or time.time() - start > 15:
                        break
                body = decode(b''.join(chunks), r.encoding)
            result = {'result': classify_status(r.status_code, body), 'status': r.status_code, 'final_url': r.url}
            if result['result'] == OK:
                title = TITLE_RE.search(body)
                if title:
                    result['title'] = html.unescape(re.sub(r'\s+', ' ', title.group(1))).strip()[:200]
                signals = content_signals(url, r.url, body)
                if signals:
                    result['signals'] = signals
            return result
    except Exception as error:  # noqa: BLE001 - every failure is a result
        return {'result': classify_exception(error), 'status': None, 'detail': str(error)[:200]}


_host_locks = defaultdict(lambda: threading.Semaphore(MAX_PER_HOST))
_host_guard = threading.Lock()


def check_url(url, retries=RETRIES, backoff=2.0):
    """Check one URL: at most MAX_PER_HOST requests per host at a time, transient failures retried."""
    with _host_guard:
        lock = _host_locks[urls.host(url)]
    result = None
    for attempt in range(retries + 1):
        with lock:
            result = request_once(url)
        if result['result'] not in TRANSIENT:
            break
        if attempt < retries:
            time.sleep(backoff * (attempt + 1))
    return result


def _days(a, b):
    return (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days


def next_state(previous, result, today, acknowledged=()):
    """New health record from the previous one (or None) and today's check result."""
    rec = dict(previous or {})
    rec.update({'checked': today, 'result': result['result'], 'status': result.get('status')})
    for key in ('final_url', 'title', 'detail'):
        if result.get(key):
            rec[key] = result[key]
        else:
            rec.pop(key, None)
    signals = [s for s in result.get('signals', []) if s not in acknowledged]
    if result['result'] in WORKING:
        rec.update({'failures': 0, 'failing_since': None, 'last_ok': today})
        rec['state'] = 'suspicious' if signals else 'verified'
        if signals:
            rec['signals'] = signals
        else:
            rec.pop('signals', None)
        return rec
    rec['failures'] = rec.get('failures', 0) + 1
    rec['failing_since'] = rec.get('failing_since') or today
    if rec['failures'] >= FAIL_AFTER_CHECKS and _days(rec['failing_since'], today) >= FAIL_AFTER_DAYS:
        rec['state'] = 'failing'
    else:
        rec['state'] = rec.get('state') if rec.get('state') in ('verified', 'suspicious', 'failing') else 'unconfirmed'
    if rec['state'] != 'suspicious':
        rec.pop('signals', None)            # signals describe a working page; they say nothing about a failure
    return rec


def load_acknowledged(repo):
    path = os.path.join(repo.root, 'health', 'acknowledged.yml')
    if not os.path.exists(path):
        return {}
    data = yamlio.load_file(path) or {}
    out = {}
    for rid, item in data.items():                  # validate checks the file; here, only never crash on it
        item = item if isinstance(item, dict) else {}
        out[rid] = {key: set(v for v in item.get(key) or [] if isinstance(v, str))
                    if isinstance(item.get(key), list) else set() for key in ('signals', 'results')}
    return out


def run_health(repo, ids=None, workers=16, today=None, checker=None):
    """Check resources and update health/status.json. `checker` replaces check_url in tests."""
    today = today or dt.datetime.now(dt.timezone.utc).date().isoformat()
    checker = checker or check_url
    resources = [r.data for r in repo.load_resources() if not r.archived]
    if ids:
        wanted = set(ids)
        resources = [d for d in resources if d['id'] in wanted]
    health = repo.load_health()
    records = health.setdefault('resources', {})
    acknowledged = load_acknowledged(repo)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        results = dict(zip([d['id'] for d in resources], pool.map(lambda d: checker(d['url']), resources)))
    for d in resources:
        previous = records.get(d['id'])
        if previous and previous.get('url') != d['url']:
            previous = None                                 # a new URL starts a new history
        ack = acknowledged.get(d['id'], {'signals': set(), 'results': set()})
        result = results[d['id']]
        if result['result'] in ack['results']:
            result = dict(result, result=RESTRICTED, detail=f'{result["result"]} (acknowledged in health/acknowledged.yml)')
        rec = next_state(previous, result, today, ack['signals'])
        rec['url'] = d['url']
        records[d['id']] = rec
    active = {r.data['id'] for r in repo.load_resources() if not r.archived}
    for rid in [rid for rid in records if rid not in active]:
        del records[rid]
    health['generated'] = today
    repo.save_health(health)
    return {'summary': summarize(records, len(resources), today), 'markdown': report(records, today)}


def summarize(records, checked, today):
    states = Counter(r.get('state') for r in records.values())
    return (f'{today}: checked {checked}; ' + ', '.join(f'{k} {v}' for k, v in sorted(states.items())))


def report(records, today, max_chars=60_000):
    """Markdown report of the resources that need attention. It becomes the body of the rolling issue,
    which GitHub limits to 65,536 characters, so rows beyond `max_chars` are counted instead of listed."""
    lines = ['# Link health report', '', f'Generated {today}. A resource is failing only after '
             f'{FAIL_AFTER_CHECKS} failed checks in a row spanning at least {FAIL_AFTER_DAYS} days.', '']
    size = sum(len(line) + 1 for line in lines)
    for state, title in (('failing', 'Failing'), ('suspicious', 'Suspicious (confirm by hand)'),
                         ('unconfirmed', 'Not yet seen working')):
        items = sorted((rid, r) for rid, r in records.items() if r.get('state') == state)
        if not items:
            continue
        head = [f'## {title} ({len(items)})', '', '| Resource | Result | Since | URL | Detail |', '|---|---|---|---|---|']
        lines += head
        size += sum(len(line) + 1 for line in head)
        for n, (rid, r) in enumerate(items):
            detail = ', '.join(r.get('signals', [])) or r.get('detail', '') or ''
            if r.get('final_url') and SIGNALS[0] in r.get('signals', []):
                detail += f' -> {r["final_url"]}'
            row = (f'| {rid} | {r.get("result")} {r.get("status") or ""} | {r.get("failing_since") or r.get("last_ok") or ""} '
                   f'| {r["url"]} | {detail.replace("|", "/")[:160]} |')
            if size + len(row) + 1 > max_chars:
                lines += ['', f'... and {len(items) - n} more; the full state is status.json on the health-data branch.']
                size += 120
                break
            lines.append(row)
            size += len(row) + 1
        lines.append('')
    return '\n'.join(lines)
