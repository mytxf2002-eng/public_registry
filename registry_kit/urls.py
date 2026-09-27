"""URL helpers: tracking-parameter removal, the uniqueness key, and site identity."""
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PREFIXES = ('utm_',)
TRACKING_PARAMS = {'gclid', 'fbclid', 'mc_cid', 'mc_eid', 'ref_src', 'igshid'}

# second-level public suffixes common in the registry; enough to tell sites apart
TWO_LEVEL_SUFFIXES = {
    'ac.uk', 'co.uk', 'gov.uk', 'org.uk', 'nhs.uk', 'ac.jp', 'co.jp', 'go.jp', 'or.jp', 'ne.jp', 'com.au', 'gov.au',
    'edu.au', 'org.au', 'co.nz', 'govt.nz', 'ac.nz', 'com.br', 'gov.br', 'org.br', 'com.cn', 'gov.cn', 'edu.cn',
    'ac.cn', 'org.cn', 'co.in', 'gov.in', 'nic.in', 'ac.in', 'co.za', 'gov.za', 'ac.za', 'com.sg', 'gov.sg',
    'edu.sg', 'com.mx', 'gob.mx', 'com.ar', 'gob.ar', 'gov.il', 'co.il', 'ac.il', 'gv.at', 'ac.at', 'gc.ca',
    'gov.pl', 'gouv.fr', 'gob.es', 'gov.it', 'go.kr', 'or.kr', 'ac.kr', 'co.kr', 'gov.hk', 'com.hk', 'edu.hk',
    'gov.pt', 'gov.ro', 'gov.ua', 'com.tr', 'gov.tr', 'edu.tr', 'com.tw', 'gov.tw', 'edu.tw', 'co.id', 'go.id',
    'ac.id', 'com.my', 'gov.my', 'com.ph', 'gov.ph', 'gov.ng', 'com.ng', 'go.ke', 'co.ke', 'gov.eg', 'gov.sa',
    'gov.ae', 'gob.cl', 'gov.co', 'gob.pe', 'gov.bd', 'gov.pk', 'gov.lk', 'gov.np', 'gov.vn', 'gov.qa',
}
# hosting platforms where the first label names the site, and the registrable part says nothing
PLATFORM_SUFFIXES = (
    'github.io', 'gitlab.io', 'herokuapp.com', 'netlify.app', 'vercel.app', 'pages.dev', 'workers.dev',
    'readthedocs.io', 'gitbook.io', 'glitch.me', 'onrender.com', 'fly.dev', 'web.app', 'firebaseapp.com',
    'appspot.com', 'azurewebsites.net', 'blogspot.com', 'wordpress.com', 'repl.co', 'replit.app', 'deno.dev',
    'surge.sh', 'railway.app', 'up.railway.app', 'amazonaws.com', 'cloudfront.net',
)


def problem(url):
    """Why a URL cannot be used (it has no host, or a malformed port or IPv6 address), or None."""
    try:
        p = urlsplit(url.strip())
        p.port                              # raises ValueError for a malformed port
    except ValueError as e:
        return str(e)
    if p.scheme not in ('http', 'https'):
        return 'not an http(s) URL'
    if not p.hostname:
        return 'no host'
    return None


def host(url):
    try:
        h = (urlsplit(url.strip()).hostname or '').lower().rstrip('.')
    except ValueError:
        return ''
    return h[4:] if h.startswith('www.') else h


def site(url_or_host):
    """The registrable site: example.co.uk, or user.github.io for hosting platforms."""
    h = host(url_or_host) if '/' in url_or_host else url_or_host.lower()
    for suffix in PLATFORM_SUFFIXES:
        if h == suffix:
            return h
        if h.endswith('.' + suffix):
            label = h[: -len(suffix) - 1].split('.')[-1]
            return f'{label}.{suffix}'
    parts = h.split('.')
    if len(parts) >= 3 and '.'.join(parts[-2:]) in TWO_LEVEL_SUFFIXES:
        return '.'.join(parts[-3:])
    return '.'.join(parts[-2:])


def is_tracking(name):
    n = name.lower()
    return n.startswith(TRACKING_PREFIXES) or n in TRACKING_PARAMS


def tracking_params(url):
    try:
        query = urlsplit(url).query
    except ValueError:
        return []
    return [k for k, _ in parse_qsl(query, keep_blank_values=True) if is_tracking(k)]


def strip_tracking(url):
    try:
        p = urlsplit(url)
    except ValueError:                      # a malformed URL is left as it is; validate reports it
        return url
    if not p.query:
        return url
    kept = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if not is_tracking(k)]
    if len(kept) == len(parse_qsl(p.query, keep_blank_values=True)):
        return url
    return urlunsplit((p.scheme, p.netloc, p.path, urlencode(kept, safe=':/@,'), p.fragment))


def unique_key(url):
    """Key under which two URLs count as the same resource.

    Ignores the scheme, a leading www., letter case of the host, a trailing slash, the fragment and
    tracking parameters. Letter case of the path is ignored too: registries list the same page with
    different capitalisation more often than two different pages differ only by case.
    """
    try:
        p = urlsplit(url.strip())
        port = p.port
    except ValueError:                      # validate reports the URL; keep the text as its own key
        return url.strip().lower()
    h = (p.hostname or '').lower()
    h = h[4:] if h.startswith('www.') else h
    if port and port not in (80, 443):
        h = f'{h}:{port}'
    query = '&'.join(f'{k}={v}' if v else k for k, v in parse_qsl(p.query, keep_blank_values=True)
                     if not is_tracking(k))
    return (h + p.path.rstrip('/') + ('?' + query if query else '')).lower()
