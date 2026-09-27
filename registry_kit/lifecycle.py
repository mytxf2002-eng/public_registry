"""Moving resources in and out of data/_archive/.

An archived resource keeps its id and URL, so the uniqueness check still finds it and a later
submission of the same URL is told why it was archived. Its translations stay in i18n/ (the site and
the exports show only active resources), so restoring it brings everything back unchanged.
"""
import datetime as dt
import os


def _find(repo, rid, archived):
    for r in repo.load_resources():
        if r.data.get('id') == rid and r.archived == archived:
            return r
    raise SystemExit(f'no {"archived" if archived else "active"} resource with id {rid!r}')


def archive(repo, rid, reason, date=None):
    r = _find(repo, rid, archived=False)
    data = dict(r.data)
    data['archived'] = {'date': date or dt.datetime.now(dt.timezone.utc).date().isoformat(), 'reason': reason}
    new = repo.write_resource(data, archived=True)
    os.remove(repo.abs(r.path))
    health = repo.load_health()
    if health.get('resources', {}).pop(rid, None) is not None:
        repo.save_health(health)
    return new


def restore(repo, rid):
    r = _find(repo, rid, archived=True)
    data = {k: v for k, v in r.data.items() if k != 'archived'}
    if data.get('domain') not in repo.vocab.domain_ids:
        raise SystemExit(f'{rid}: domain {data.get("domain")!r} no longer exists; set a current domain in '
                         f'{r.path} first')
    new = repo.write_resource(data)
    os.remove(repo.abs(r.path))
    return new
