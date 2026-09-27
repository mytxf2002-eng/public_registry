"""Command line: python -m registry_kit <command> [options]

  validate [--strict FILE ...]   check every file; --strict holds the given (new) files to the rules for
                                 new resources: complete metadata and the "contribution" origin
  format [--check]               rewrite files into canonical form (--check: only report)
  schema [--check]               regenerate schema/*.json from vocab/ (--check: fail if stale)
  health [--ids ID ...]          check links and update health/status.json with hysteresis
  check-urls [URL ...] [--files FILE ...]   check URLs now (the pull request gate passes changed files)
  archive-failing --days N       archive failing resources whose first failed check is N or more days old
  archive ID --reason TEXT       move a resource to data/_archive/ (keeps its URL reserved)
  restore ID                     bring an archived resource back
  build [--out DIR]              render the site, exports, static API and Markdown lists into build/
  stats                          print counts and completeness
"""
import argparse
import os
import sys

from .repo import Repo, find_root


def _print_problems(problems, limit=None):
    errors = [p for p in problems if p.level == 'error']
    warnings = [p for p in problems if p.level == 'warning']
    for p in (errors + warnings)[:limit]:
        print(p)
    if limit is not None and len(errors) + len(warnings) > limit:
        print(f'... and {len(errors) + len(warnings) - limit} more')
    print(f'{len(errors)} error(s), {len(warnings)} warning(s)')
    return errors


def cmd_validate(repo, args):
    from .validate import validate
    problems = validate(repo, strict_paths=args.strict or ())
    return 1 if _print_problems(problems, args.limit) else 0


def cmd_format(repo, args):
    from .normalize import format_repo
    changed = format_repo(repo, check=args.check)
    for path in changed:
        print(('not canonical: ' if args.check else 'formatted: ') + path)
    print(f'{len(changed)} file(s) {"need formatting" if args.check else "rewritten"}')
    return 1 if (args.check and changed) else 0


def cmd_schema(repo, args):
    from .schema import write_schemas
    stale = write_schemas(repo.root, repo.vocab, check=args.check)
    for name in stale:
        print(('out of date: schema/' if args.check else 'wrote schema/') + name)
    if not stale:
        print('schemas are up to date')
    return 1 if (args.check and stale) else 0


def cmd_health(repo, args):
    from .health import run_health
    report = run_health(repo, ids=args.ids, workers=args.workers, today=args.today)
    print(report['summary'])
    if args.report:
        with open(args.report, 'w', encoding='utf-8') as f:
            f.write(report['markdown'])
    return 0


def cmd_check_urls(repo, args):
    from . import yamlio
    from .health import WORKING, check_url, load_acknowledged
    from .validate import _repo_path
    acknowledged = load_acknowledged(repo)
    none = {'signals': set(), 'results': set()}
    targets = {url: none for url in args.urls or []}        # url -> what the maintainer accepted for it
    failed = 0
    for given in args.files or []:
        path = _repo_path(repo, given)
        if not (path.startswith('data/') and path.endswith('.yml')) or path.startswith('data/_archive/'):
            continue                                        # only active resource files are checked
        if not os.path.exists(repo.abs(path)):
            print(f'FAIL no such file: {given}')
            failed += 1
            continue
        try:
            data = yamlio.load_file(repo.abs(path))
        except Exception as e:  # noqa: BLE001 - validate reports the file; here it only cannot be checked
            print(f'FAIL cannot read {path}: {e}')
            failed += 1
            continue
        if not isinstance(data, dict):
            continue
        ack = acknowledged.get(data.get('id'), none)
        for url in (data.get('url'), data.get('license_url')):
            if isinstance(url, str):
                targets.setdefault(url, ack)
    for url, ack in targets.items():
        result = check_url(url)
        signals = [s for s in result.get('signals', []) if s not in ack['signals']]
        ok = (result['result'] in WORKING or result['result'] in ack['results']) and not signals
        failed += not ok
        note = f' signals: {", ".join(signals)}' if signals else ''
        if result['result'] in ack['results']:
            note += ' (accepted in health/acknowledged.yml)'
        print(f'{"ok  " if ok else "FAIL"} {result["result"]:<18} {result.get("status") or "-":<4} {url}{note}')
    return 1 if failed else 0


def cmd_archive(repo, args):
    from .lifecycle import archive
    print('archived:', archive(repo, args.id, args.reason, args.date))
    return 0


def cmd_archive_failing(repo, args):
    import datetime as dt
    from .lifecycle import archive
    today = args.today or dt.datetime.now(dt.timezone.utc).date().isoformat()
    moved = 0
    for rid, rec in sorted(repo.load_health().get('resources', {}).items()):
        since = rec.get('failing_since')
        if rec.get('state') != 'failing' or not since:
            continue
        if (dt.date.fromisoformat(today) - dt.date.fromisoformat(since)).days < args.days:
            continue
        reason = (f'Unreachable since {since} ({rec.get("result")}{" " + str(rec["status"]) if rec.get("status") else ""}, '
                  f'{rec.get("failures")} failed checks); archived automatically after {args.days} days')
        print('archived:', archive(repo, rid, reason, today))
        moved += 1
    print(f'{moved} resource(s) archived')
    return 0


def cmd_restore(repo, args):
    from .lifecycle import restore
    print('restored:', restore(repo, args.id))
    return 0


def cmd_build(repo, args):
    from .build import build
    summary = build(repo, out=args.out, source_sha=args.source_sha)
    print(summary)
    return 0


def cmd_stats(repo, args):
    from .stats import compute, format_text
    print(format_text(compute(repo)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog='python -m registry_kit', description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', help='repository root (default: found from the current directory)')
    sub = ap.add_subparsers(dest='command', required=True)

    p = sub.add_parser('validate')
    p.add_argument('--strict', nargs='*', metavar='FILE')
    p.add_argument('--limit', type=int, default=200, help='print at most this many problems')
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser('format')
    p.add_argument('--check', action='store_true')
    p.set_defaults(func=cmd_format)

    p = sub.add_parser('schema')
    p.add_argument('--check', action='store_true')
    p.set_defaults(func=cmd_schema)

    p = sub.add_parser('health')
    p.add_argument('--ids', nargs='*')
    p.add_argument('--workers', type=int, default=16)
    p.add_argument('--today', help='date to record (YYYY-MM-DD, default: today UTC)')
    p.add_argument('--report', help='write a Markdown report of failing resources here')
    p.set_defaults(func=cmd_health)

    p = sub.add_parser('check-urls')
    p.add_argument('urls', nargs='*')
    p.add_argument('--files', nargs='*', help='resource files whose url and license_url to check')
    p.set_defaults(func=cmd_check_urls)

    p = sub.add_parser('archive-failing')
    p.add_argument('--days', type=int, default=30)
    p.add_argument('--today', help='YYYY-MM-DD (default: today UTC)')
    p.set_defaults(func=cmd_archive_failing)

    p = sub.add_parser('archive')
    p.add_argument('id')
    p.add_argument('--reason', required=True)
    p.add_argument('--date', help='YYYY-MM-DD (default: today UTC)')
    p.set_defaults(func=cmd_archive)

    p = sub.add_parser('restore')
    p.add_argument('id')
    p.set_defaults(func=cmd_restore)

    p = sub.add_parser('build')
    p.add_argument('--out', default='build')
    p.add_argument('--source-sha', default=None, help='commit the build is made from (default: git HEAD)')
    p.set_defaults(func=cmd_build)

    p = sub.add_parser('stats')
    p.set_defaults(func=cmd_stats)

    # resource texts use every script; a console or a pipe on Windows may default to a legacy code page
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='backslashreplace')
    args = ap.parse_args(argv)
    repo = Repo(args.root or find_root())
    return args.func(repo, args)


if __name__ == '__main__':
    sys.exit(main())
