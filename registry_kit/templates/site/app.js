/* Public Registry site: search, filters and the quality dashboard over window.REGISTRY (data.js). */
(function () {
  'use strict';
  var R = window.REGISTRY;
  if (!R) { return; }
  var $ = function (id) { return document.getElementById(id); };
  var KIND = { a: 'api', d: 'dataset', m: 'mcp-server' };
  var KINDS = ['api', 'dataset', 'mcp-server'];
  var FAMILY_GROUP = {
    'public-domain': 'open', permissive: 'open', 'share-alike': 'open',
    'no-derivatives': 'restricted', 'non-commercial': 'restricted', 'research-only': 'restricted', terms: 'restricted',
    unknown: 'unknown'
  };
  var STATES = ['verified', 'suspicious', 'unconfirmed', 'failing', 'unchecked'];
  var STATE_ICON = { verified: '✓', suspicious: '!', unconfirmed: '?', failing: '✕', unchecked: '–' };
  var ORIGINS = ['public-apis', 'apd-link', 'contribution'];

  var STR = {
    en: {
      tagline: 'Public APIs, datasets and MCP servers in one catalogue, each with its access route, its licence where known, and a daily link check.',
      tabBrowse: 'Browse', tabQuality: 'Quality', tabAbout: 'About', filters: 'Filters', search: 'Search',
      kind: 'Kind', domain: 'Domain', licence: 'Licence', access: 'Dataset access', auth: 'API authentication',
      status: 'Link status', reset: 'Clear filters', sort: 'Sort', sortName: 'Name', sortNew: 'Newest',
      all: 'All', allDomains: 'All domains', resources: 'resources',
      k_api: 'API', k_dataset: 'Dataset', 'k_mcp-server': 'MCP',
      kp_api: 'APIs', kp_dataset: 'Datasets', 'kp_mcp-server': 'MCP servers',
      l_open: 'Open', l_restricted: 'Restricted', l_unknown: 'Unknown',
      a_public: 'Direct download', a_registration: 'Free account', a_application: 'Application', 'a_paid-tier': 'Free tier',
      u_none: 'None', 'u_api-key': 'API key', u_oauth: 'OAuth', 'u_x-mashape-key': 'RapidAPI key', 'u_user-agent': 'User-Agent',
      s_verified: 'OK', s_suspicious: 'Check', s_unconfirmed: 'Unconfirmed', s_failing: 'Failing', s_unchecked: 'Not checked',
      shown: function (n, t) { return n === t ? fmt(t) + ' resources' : fmt(n) + ' of ' + fmt(t) + ' resources'; },
      more: function (n) { return 'Show ' + n + ' more'; },
      empty: 'Nothing matches these filters. Clear a filter or search for a broader term.',
      licUnknown: 'licence unknown', formats: 'formats', by: 'by', sponsor: 'Sponsor', id: 'id',
      counts: [['resources', 'resources'], ['api', 'APIs'], ['dataset', 'datasets'], ['mcp-server', 'MCP servers'], ['domains', 'domains']],
      tResources: 'Resources', tAvail: 'Links working', tLicence: 'Licence known', tZh: 'Chinese text',
      tResourcesSub: function (s) { return fmt(s.api_and_dataset) + ' offer both an API and downloads'; },
      tAvailSub: function (s) { return 'of ' + fmt(s.health.checked) + ' checked on ' + s.generated; },
      tLicenceSub: function (c) { return 'datasets ' + c.license_known_dataset + '% · APIs ' + c.license_known_api + '%'; },
      tZhSub: 'share of resources with a Chinese description',
      cTitle: 'Metadata completeness', cNote: 'Share of resources with each field filled. Licences were never recorded in the public-apis list, so most APIs still say unknown.',
      c_description: 'Description', c_translation_zh: 'Chinese description', c_license_known: 'Licence known',
      c_license_url_when_known: 'Licence source link (of known)', c_publisher: 'Publisher', c_cors_known: 'CORS known (APIs)',
      c_update_frequency: 'Update frequency (datasets)', c_spatial: 'Coverage area (datasets)', c_temporal: 'Time span (datasets)',
      hTitle: 'Link health', hNote: 'A resource counts as failing only after 3 failed checks in a row spanning at least 7 days; until then a resource never seen working is unconfirmed. 401, 403 and 429 answers count as working.',
      fTitle: 'Licences', fNote: 'Licence families. Open means public domain, permissive or share-alike.',
      f_public: 'Public domain', f_permissive: 'Permissive', 'f_share-alike': 'Share-alike', 'f_no-derivatives': 'No derivatives',
      'f_non-commercial': 'Non-commercial', 'f_research-only': 'Research only', f_terms: "Provider's terms", f_unknown: 'Unknown',
      dTitle: 'Domains', dNote: 'Resources per domain, split by kind. A resource that is both an API and a dataset counts in both.',
      oTitle: 'Formats', oNote: 'File formats offered by datasets.',
      gTitle: 'Where resources come from', gNote: 'Every resource file records its origin.',
      g_public: 'Imported from the public-apis list', g_apd: 'Researched from a dataset link list', g_contribution: 'Contributed directly',
      foot: function (g, sha) { return 'Generated ' + g + (sha ? ' from ' + sha : '') + ' · data CC BY 4.0 · code MIT'; }
    },
    zh: {
      tagline: '把公开 API、数据集和 MCP 服务器放在一个目录里，标明获取方式和已知的许可，并每天检测链接。',
      tabBrowse: '浏览', tabQuality: '质量', tabAbout: '说明', filters: '筛选', search: '搜索',
      kind: '类型', domain: '领域', licence: '许可', access: '数据集获取方式', auth: 'API 鉴权',
      status: '链接状态', reset: '清除筛选', sort: '排序', sortName: '名称', sortNew: '最新收录',
      all: '全部', allDomains: '全部领域', resources: '个资源',
      k_api: 'API', k_dataset: '数据集', 'k_mcp-server': 'MCP',
      kp_api: 'API', kp_dataset: '数据集', 'kp_mcp-server': 'MCP 服务器',
      l_open: '开放', l_restricted: '有限制', l_unknown: '未知',
      a_public: '直接下载', a_registration: '免费注册', a_application: '需申请', 'a_paid-tier': '有免费档',
      u_none: '免鉴权', 'u_api-key': 'API key', u_oauth: 'OAuth', 'u_x-mashape-key': 'RapidAPI key', 'u_user-agent': 'User-Agent',
      s_verified: '正常', s_suspicious: '待核实', s_unconfirmed: '待确认', s_failing: '失效', s_unchecked: '未检测',
      shown: function (n, t) { return n === t ? '共 ' + fmt(t) + ' 个资源' : fmt(t) + ' 个资源中的 ' + fmt(n) + ' 个'; },
      more: function (n) { return '再显示 ' + n + ' 个'; },
      empty: '没有符合条件的资源。可以清除某个筛选，或换一个更宽泛的搜索词。',
      licUnknown: '许可未知', formats: '格式', by: '发布方', sponsor: '赞助商', id: 'id',
      counts: [['resources', '个资源'], ['api', '个 API'], ['dataset', '个数据集'], ['mcp-server', '个 MCP 服务器'], ['domains', '个领域']],
      tResources: '资源总数', tAvail: '链接可用', tLicence: '许可已知', tZh: '中文说明',
      tResourcesSub: function (s) { return '其中 ' + fmt(s.api_and_dataset) + ' 个同时提供 API 和数据下载'; },
      tAvailSub: function (s) { return '按 ' + s.generated + ' 检测的 ' + fmt(s.health.checked) + ' 个计'; },
      tLicenceSub: function (c) { return '数据集 ' + c.license_known_dataset + '% · API ' + c.license_known_api + '%'; },
      tZhSub: '有中文说明的资源占比',
      cTitle: '元数据完整度', cNote: '各字段已填写的资源占比。public-apis 原表从未记录许可，所以大部分 API 的许可仍是未知。',
      c_description: '英文说明', c_translation_zh: '中文说明', c_license_known: '许可已知',
      c_license_url_when_known: '许可出处链接（已知许可中）', c_publisher: '发布方', c_cors_known: 'CORS 已知（API）',
      c_update_frequency: '更新频率（数据集）', c_spatial: '覆盖地区（数据集）', c_temporal: '时间范围（数据集）',
      hTitle: '链接健康', hNote: '连续 3 次检测失败且跨度至少 7 天，才判为失效；在此之前，从未检测成功的资源标为待确认。401、403、429 视为可用。',
      fTitle: '许可', fNote: '按许可类别统计。开放指公有领域、宽松许可和相同方式共享。',
      f_public: '公有领域', f_permissive: '宽松许可', 'f_share-alike': '相同方式共享', 'f_no-derivatives': '禁止演绎',
      'f_non-commercial': '非商业', 'f_research-only': '仅限科研', f_terms: '服务条款', f_unknown: '未知',
      dTitle: '领域', dNote: '各领域的资源数量，按类型拆分。同时是 API 和数据集的资源在两边都计入。',
      oTitle: '格式', oNote: '数据集提供的文件格式。',
      gTitle: '资源来源', gNote: '每个资源文件都记录了来源。',
      g_public: '从 public-apis 清单导入', g_apd: '依据数据集链接清单独立调研', g_contribution: '直接投稿',
      foot: function (g, sha) { return '生成于 ' + g + (sha ? '，源提交 ' + sha : '') + ' · 数据 CC BY 4.0 · 代码 MIT'; }
    }
  };

  function fmt(n) { return Number(n).toLocaleString('en-US'); }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function sortKey(s) { return s.normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase(); }
  function store(key, value) {
    try { if (value === undefined) { return window.localStorage.getItem(key); } window.localStorage.setItem(key, value); }
    catch (e) { return null; }
    return null;
  }

  var lang = store('registry-lang') || ((navigator.language || '').toLowerCase().indexOf('zh') === 0 ? 'zh' : 'en');
  if (!STR[lang]) { lang = 'en'; }
  function t(key) { return STR[lang][key] !== undefined ? STR[lang][key] : (STR.en[key] !== undefined ? STR.en[key] : key); }

  var DOM = R.domains;
  R.r.forEach(function (x) {
    x.kinds = x.k.split('').map(function (c) { return KIND[c]; });
    x.fam = x.l === 'unknown' ? 'unknown' : (R.licenses[x.l] || 'unknown');
    x.lg = FAMILY_GROUP[x.fam] || 'unknown';
    x.hs = x.h ? x.h[0] : 'unchecked';
    x.sk = sortKey(x.n);
    x.hay = [x.n, x.e, x.z || '', x.zg || '', (x.g || []).join(' '), x.i, x.p ? x.p[0] : '', x.l,
      x.ds ? x.ds.f.join(' ') : '', DOM[x.d].name, DOM[x.d].name_zh].join(' ').toLowerCase();
  });

  var st = { q: '', kind: '', domain: '', lic: '', access: '', auth: '', health: '', sort: 'name', limit: 40 };
  var STEP = 40;

  function pass(x, except) {
    if (except !== 'q' && st.q) {
      var terms = st.q.toLowerCase().split(/\s+/);
      for (var i = 0; i < terms.length; i++) { if (terms[i] && x.hay.indexOf(terms[i]) < 0) { return false; } }
    }
    if (except !== 'kind' && st.kind && x.kinds.indexOf(st.kind) < 0) { return false; }
    if (except !== 'domain' && st.domain && DOM[x.d].id !== st.domain) { return false; }
    if (except !== 'lic' && st.lic && x.lg !== st.lic) { return false; }
    if (except !== 'access' && st.access && !(x.ds && x.ds.x === st.access)) { return false; }
    if (except !== 'auth' && st.auth && !((x.ap && x.ap[0] === st.auth) || (x.mc && x.mc[0] === st.auth))) { return false; }
    if (except !== 'health' && st.health && x.hs !== st.health) { return false; }
    return true;
  }

  function counts(facet, valueOf) {
    var out = {};
    R.r.forEach(function (x) {
      if (!pass(x, facet)) { return; }
      [].concat(valueOf(x)).forEach(function (v) { if (v) { out[v] = (out[v] || 0) + 1; } });
    });
    return out;
  }

  function chipGroup(el, facet, options, labelPrefix, valueOf) {
    var c = counts(facet, valueOf);
    var total = R.r.filter(function (x) { return pass(x, facet); }).length;
    var html = '<button type="button" class="chip" data-f="' + facet + '" data-v="" aria-pressed="' + (!st[facet]) + '">'
      + esc(t('all')) + ' <span class="n">' + fmt(total) + '</span></button>';
    options.forEach(function (v) {
      var n = c[v] || 0;
      if (!n && st[facet] !== v && facet !== 'kind' && facet !== 'lic' && facet !== 'health') { return; }
      html += '<button type="button" class="chip" data-f="' + facet + '" data-v="' + esc(v) + '" aria-pressed="' + (st[facet] === v)
        + '"' + (n ? '' : ' disabled') + '>' + esc(t(labelPrefix + v)) + ' <span class="n">' + fmt(n) + '</span></button>';
    });
    el.innerHTML = html;
  }

  function renderFilters() {
    chipGroup($('f-kind'), 'kind', KINDS, 'kp_', function (x) { return x.kinds; });
    chipGroup($('f-lic'), 'lic', ['open', 'restricted', 'unknown'], 'l_', function (x) { return x.lg; });
    chipGroup($('f-access'), 'access', ['public', 'registration', 'application', 'paid-tier'], 'a_',
      function (x) { return x.ds ? x.ds.x : null; });
    chipGroup($('f-auth'), 'auth', ['none', 'api-key', 'oauth', 'x-mashape-key', 'user-agent'], 'u_',
      function (x) { return x.ap ? x.ap[0] : (x.mc ? x.mc[0] : null); });
    chipGroup($('f-health'), 'health', STATES, 's_', function (x) { return x.hs; });
    var dc = counts('domain', function (x) { return DOM[x.d].id; });
    var all = R.r.filter(function (x) { return pass(x, 'domain'); }).length;
    var opts = '<option value="">' + esc(t('allDomains')) + ' (' + fmt(all) + ')</option>';
    DOM.map(function (d) { return d; }).sort(function (a, b) {
      return sortKey(lang === 'zh' ? a.name_zh : a.name) < sortKey(lang === 'zh' ? b.name_zh : b.name) ? -1 : 1;
    }).forEach(function (d) {
      opts += '<option value="' + d.id + '"' + (st.domain === d.id ? ' selected' : '') + '>'
        + esc(lang === 'zh' ? d.name_zh : d.name) + ' (' + fmt(dc[d.id] || 0) + ')</option>';
    });
    $('f-domain').innerHTML = opts;
  }

  function row(x) {
    var kinds = x.kinds.map(function (k) { return '<span class="kind ' + k + '">' + esc(t('k_' + k)) + '</span>'; }).join('');
    var desc = lang === 'zh' ? (x.z || x.e) : x.e;
    var meta = ['<span>' + esc(lang === 'zh' ? DOM[x.d].name_zh + (x.zg ? ' · ' + x.zg : '') : DOM[x.d].name) + '</span>'];
    meta.push(x.l === 'unknown' ? '<span>' + esc(t('licUnknown')) + '</span>'
      : '<span><code>' + esc(x.l.replace('LicenseRef-', '')) + '</code></span>');
    if (x.ds) {
      meta.push('<span>' + esc(t('a_' + x.ds.x)) + '</span>');
      meta.push('<span>' + esc(t('formats')) + ' <code>' + esc(x.ds.f.join(', ')) + '</code></span>');
    }
    if (x.ap) { meta.push('<span>' + esc(t('u_' + x.ap[0])) + (x.ap[1] ? '' : ' · HTTP') + '</span>'); }
    if (x.mc) { meta.push('<span>' + esc(t('u_' + x.mc[0])) + ' · <code>' + esc(x.mc[1].join(', ')) + '</code></span>'); }
    if (x.p) { meta.push('<span>' + esc(t('by')) + ' ' + esc(x.p[0]) + '</span>'); }
    meta.push('<span>' + esc(t('id')) + ' <code>' + esc(x.i) + '</code></span>');
    return '<article class="row"><div class="row-head"><a class="name" href="' + esc(x.u) + '" target="_blank" rel="noopener">'
      + esc(x.n) + '</a>' + kinds + (x.s ? '<span class="sponsor">' + esc(t('sponsor')) + '</span>' : '')
      + '<span class="state ' + x.hs + '"><i aria-hidden="true">' + STATE_ICON[x.hs] + '</i>' + esc(t('s_' + x.hs)) + '</span></div>'
      + '<p class="desc">' + esc(desc) + '</p><div class="meta">' + meta.join('') + '</div></article>';
  }

  function renderList() {
    var items = R.r.filter(function (x) { return pass(x); });
    if (st.sort === 'new') {
      items.sort(function (a, b) { return a.a === b.a ? (a.sk < b.sk ? -1 : 1) : (a.a < b.a ? 1 : -1); });
    } else {
      items.sort(function (a, b) { return a.sk < b.sk ? -1 : a.sk > b.sk ? 1 : 0; });
    }
    $('result-count').textContent = t('shown')(items.length, R.r.length);
    $('list').innerHTML = items.length ? items.slice(0, st.limit).map(row).join('')
      : '<p class="empty">' + esc(t('empty')) + '</p>';
    var rest = items.length - st.limit;
    $('more').hidden = rest <= 0;
    if (rest > 0) { $('more').textContent = t('more')(Math.min(STEP, rest)); }
  }

  function renderBrowse() { renderFilters(); renderList(); }

  function bar(label, value, max, text, cls) {
    var w = max ? Math.max(0, Math.min(100, 100 * value / max)) : 0;
    return '<div class="bar' + (cls ? ' ' + cls : '') + '" title="' + esc(label + ': ' + text) + '"><span class="lab">' + esc(label)
      + '</span><span class="track"><span class="fill" style="width:' + w.toFixed(2) + '%"></span></span><span class="val">'
      + esc(text) + '</span></div>';
  }

  function stack(label, parts, max, text) {
    var segs = parts.filter(function (p) { return p[1] > 0; }).map(function (p) {
      return '<span class="seg ' + p[0] + '" style="width:' + (100 * p[1] / max).toFixed(3) + '%" title="'
        + esc(p[2] + ': ' + fmt(p[1])) + '"></span>';
    }).join('');
    return '<div class="bar"><span class="lab">' + esc(label) + '</span><span class="track" style="background:transparent">'
      + segs + '</span><span class="val">' + esc(text) + '</span></div>';
  }

  function legend(items) {
    return '<p class="legend">' + items.map(function (i) {
      return '<span><i class="' + i[0] + '"></i>' + esc(i[1]) + '</span>';
    }).join('') + '</p>';
  }

  function renderQuality() {
    var s = R.stats, c = s.completeness;
    var html = '<div class="tiles">'
      + tile(fmt(s.resources), t('tResources'), t('tResourcesSub')(s))
      + tile(s.health.checked ? s.health.availability + '%' : '–', t('tAvail'), t('tAvailSub')(s))
      + tile(c.license_known + '%', t('tLicence'), t('tLicenceSub')(c))
      + tile(c.translation_zh + '%', t('tZh'), t('tZhSub'))
      + '</div><div class="board">';

    var fields = ['description', 'translation_zh', 'license_known', 'license_url_when_known', 'publisher', 'cors_known',
      'update_frequency', 'spatial', 'temporal'];
    html += card(t('cTitle'), t('cNote'), '<div class="bars">' + fields.map(function (f) {
      return bar(t('c_' + f), c[f], 100, c[f] + '%');
    }).join('') + '</div>');

    var hs = s.health.states, total = s.resources;
    html += card(t('hTitle'), t('hNote'), legend(STATES.map(function (k) { return [k, t('s_' + k) + ' ' + fmt(hs[k] || 0)]; }))
      + '<div class="bars stack-big">' + stack(lang === 'zh' ? '全部' : 'All', STATES.map(function (k) {
        return [k, hs[k] || 0, t('s_' + k)];
      }), total, fmt(total)) + '</div>');

    var fam = s.license_families, fkeys = ['public-domain', 'permissive', 'share-alike', 'no-derivatives', 'non-commercial',
      'research-only', 'terms', 'unknown'];
    var fmax = Math.max.apply(null, fkeys.map(function (k) { return fam[k] || 0; }));
    html += card(t('fTitle'), t('fNote'), '<div class="bars">' + fkeys.filter(function (k) { return fam[k]; }).map(function (k) {
      return bar(t('f_' + (k === 'public-domain' ? 'public' : k)), fam[k], fmax, fmt(fam[k]));
    }).join('') + '</div>');

    var doms = DOM.map(function (d) {
      var x = s.domains[d.id] || {};
      return { d: d, api: x.api || 0, dataset: x.dataset || 0, mcp: x['mcp-server'] || 0, total: x.total || 0 };
    }).sort(function (a, b) { return b.total - a.total; });
    var dmax = Math.max.apply(null, doms.map(function (d) { return d.api + d.dataset + d.mcp; }));
    html += card(t('dTitle'), t('dNote'), legend(KINDS.map(function (k) { return [k, t('kp_' + k)]; }))
      + '<div class="bars domains">' + doms.map(function (d) {
        return stack(lang === 'zh' ? d.d.name_zh : d.d.name, [['api', d.api, t('kp_api')], ['dataset', d.dataset, t('kp_dataset')],
          ['mcp-server', d.mcp, t('kp_mcp-server')]], dmax, fmt(d.total));
      }).join('') + '</div>', 'wide');

    var fmts = Object.keys(s.formats).slice(0, 14), omax = s.formats[fmts[0]] || 1;
    html += card(t('oTitle'), t('oNote'), '<div class="bars">' + fmts.map(function (f) {
      return bar(f, s.formats[f], omax, fmt(s.formats[f]));
    }).join('') + '</div>');

    var o = s.origins, omax2 = Math.max(o['public-apis'] || 0, o['apd-link'] || 0, o.contribution || 0);
    html += card(t('gTitle'), t('gNote'), '<div class="bars">'
      + bar(t('g_public'), o['public-apis'] || 0, omax2, fmt(o['public-apis'] || 0))
      + bar(t('g_apd'), o['apd-link'] || 0, omax2, fmt(o['apd-link'] || 0))
      + bar(t('g_contribution'), o.contribution || 0, omax2, fmt(o.contribution || 0)) + '</div>');
    html += '</div>';
    $('dashboard').innerHTML = html;
  }

  function tile(v, k, sub) {
    return '<div class="tile"><span class="v">' + esc(v) + '</span><span class="k">' + esc(k) + '</span><span class="s">'
      + esc(sub) + '</span></div>';
  }
  function card(title, note, body, cls) {
    return '<section class="card' + (cls ? ' ' + cls : '') + '"><h2>' + esc(title) + '</h2><p class="note">' + esc(note)
      + '</p>' + body + '</section>';
  }

  function renderAbout() {
    var files = R.mode === 'site';
    var en = [
      ['What this is', ['One catalogue for public APIs, downloadable datasets and MCP servers. Each resource is one file in the repository, checked against a JSON Schema, and a resource can be both an API and a dataset.']],
      ['How entries are checked', ['Every pull request is validated in full: schema, unique URL, controlled values for domain, licence and format, and a live check of new links. Links are checked again every day; a resource is marked failing only after 3 failed checks in a row over at least 7 days, and the result is kept outside the resource files.']],
      ['Where the data comes from', ['Resources with origin "public-apis" were imported from the public-apis list (MIT). Those with origin "apd-link" were researched independently: only their links came from the awesome-public-datasets list (its licence values served only as hints for a few licence checks), and names, descriptions, licences and all other fields were written from each resource\'s own website. Resources with origin "contribution" were added through pull requests.']],
      ['Licences', ['The catalogue data is published under CC BY 4.0 and the code under MIT. The licence shown for a resource is that resource\'s own licence, where it is known, with a link to where it is stated.']]
    ];
    var zh = [
      ['这是什么', ['一个同时收录公开 API、可下载数据集和 MCP 服务器的目录。每个资源在仓库里是一个文件，经 JSON Schema 校验；同一个资源可以既是 API 又是数据集。']],
      ['条目怎么把关', ['每个拉取请求都做完整校验：Schema、URL 唯一性、领域、许可、格式等受控取值，以及新链接的实时检测。链接每天复检；只有连续 3 次失败且跨度至少 7 天才标为失效，检测结果存放在资源文件之外。']],
      ['数据来源', ['origin 为 public-apis 的资源导入自 public-apis 清单（MIT）。origin 为 apd-link 的资源为独立调研：只从 awesome-public-datasets 清单取了链接（其许可字段只在少数许可核实中用作线索），名称、说明、许可等所有字段都依据资源自己的网站撰写。origin 为 contribution 的资源经拉取请求加入。']],
      ['许可', ['目录数据以 CC BY 4.0 发布，代码为 MIT。资源显示的许可是该资源自身的许可（已知时），并附出处链接。']]
    ];
    var html = (lang === 'zh' ? zh : en).map(function (s) {
      return '<h2>' + esc(s[0]) + '</h2>' + s[1].map(function (p) { return '<p>' + esc(p) + '</p>'; }).join('');
    }).join('');
    if (files) {
      html += '<h2>' + (lang === 'zh' ? '下载与接口' : 'Downloads and API') + '</h2><ul>'
        + '<li><a href="export/resources.csv">resources.csv</a> · <a href="export/resources.json">resources.json</a> · <a href="export/registry.sqlite">registry.sqlite</a></li>'
        + '<li><a href="api/v1/index.json">api/v1/index.json</a> ' + (lang === 'zh' ? '（静态只读接口）' : '(static read-only API)') + '</li></ul>';
    }
    $('about').innerHTML = html;
  }

  function renderChrome() {
    document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
    Array.prototype.forEach.call(document.querySelectorAll('[data-t]'), function (el) {
      var v = t(el.getAttribute('data-t'));
      if (typeof v === 'string') { el.textContent = v; }
    });
    $('lang-en').setAttribute('aria-pressed', String(lang === 'en'));
    $('lang-zh').setAttribute('aria-pressed', String(lang === 'zh'));
    var s = R.stats, kinds = s.kinds;
    var values = { resources: s.resources, api: kinds.api, dataset: kinds.dataset, 'mcp-server': kinds['mcp-server'], domains: DOM.length };
    $('counts').innerHTML = t('counts').map(function (p) {
      return '<div><dt>' + esc(p[1]) + '</dt><dd>' + fmt(values[p[0]]) + '</dd></div>';
    }).join('');
    $('foot').textContent = t('foot')(R.generated, R.sha);
  }

  function renderAll() { renderChrome(); renderBrowse(); renderQuality(); renderAbout(); }

  function showTab() {
    var tab = (location.hash || '#browse').slice(1);
    if (['browse', 'quality', 'about'].indexOf(tab) < 0) { tab = 'browse'; }
    ['browse', 'quality', 'about'].forEach(function (name) {
      $('panel-' + name).hidden = name !== tab;
      $('tab-' + name).setAttribute('aria-selected', String(name === tab));
    });
  }

  document.addEventListener('click', function (e) {
    var chip = e.target.closest('.chip');
    if (chip && !chip.disabled) {
      var f = chip.getAttribute('data-f'), v = chip.getAttribute('data-v');
      st[f] = st[f] === v ? '' : v;
      st.limit = STEP;
      renderBrowse();
      return;
    }
    var lb = e.target.closest('[data-lang]');
    if (lb) { lang = lb.getAttribute('data-lang'); store('registry-lang', lang); renderAll(); }
  });
  $('q').addEventListener('input', function (e) { st.q = e.target.value.trim(); st.limit = STEP; renderBrowse(); });
  $('f-domain').addEventListener('change', function (e) { st.domain = e.target.value; st.limit = STEP; renderBrowse(); });
  $('sort').addEventListener('change', function (e) { st.sort = e.target.value; renderList(); });
  $('more').addEventListener('click', function () { st.limit += STEP; renderList(); });
  $('reset').addEventListener('click', function () {
    st = { q: '', kind: '', domain: '', lic: '', access: '', auth: '', health: '', sort: st.sort, limit: STEP };
    $('q').value = '';
    renderBrowse();
  });
  window.addEventListener('hashchange', showTab);
  if (window.matchMedia && window.matchMedia('(max-width: 880px)').matches) { $('filters').open = false; }
  renderAll();
  showTab();
})();
