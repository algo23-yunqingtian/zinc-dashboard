"""
scorer_v2.py — 锌看板统一新闻打分模块 (唯一打分来源 / single source of truth)

设计目标 (2026-08-16 统一化):
  1. 所有取数路径共用本模块打分, 禁止各自维护关键词/打分逻辑:
     - fetch_data.py   (GitHub Actions 主路径, 写 gh_static/data.json)
     - fetch_zinc.py (本地定时刷新, commodity-dashboard + gh_static 两份)
     - analyze.py      (8774 AI 实时解盘, 构建 prompt 的新闻)
     - update_data.py  (news_cache.json 导出)
  2. 评分算法 = keyword_engine scorer v2 (维度去重 + 矛盾权重 + 多空方向 + 交叉验证),
     配置自包含于本仓库 zinc_scoring.yaml (GitHub Actions 无 /home/ubuntu 路径).
  3. 相关性闸门 (relevance gate): 与锌无关的新闻 (如"哥伦比亚强震"命中地震词)
     评分上限压到 5 分, 降出榜单; 标题含品种名的保留.

对外 API:
  score_news(content, title) -> (score, tier, matched_terms, direction, contradiction_summary, relevant)
  build_entry(title, content, source, time_str, url) -> dict  (统一新闻结构)
  is_noise(text) -> bool
  is_related(text, title) -> bool
  load_config() -> dict
"""
import os, re
from collections import defaultdict

_BASE = os.path.dirname(os.path.abspath(__file__))
_YAML = os.path.join(_BASE, "zinc_scoring.yaml")

# 与 keyword_engine.GENERIC_NEGATIVE 同步 (本模块自包含, GH Actions 无外部依赖)
GENERIC_NEGATIVE = [
    'LME现货结算价', 'SHFE最新', 'LME夜盘收盘', 'SHFE夜盘收盘',
    'LME库存', 'LME注销仓单', 'LME现货结算',
    '上期所基本金属仓单', 'LME金属技术策略', 'SHFE夜盘开盘',
    'SHFE开盘_基本', 'SHFE收盘_基本', '本周均价',
    '每股收益', '分红', '回购',
    'IPO', '上市审核', 'A股发行', '港股发行', '深交所', '上交所', '港交所',
    '股票发行', '首次公开募股', '发行股份', '定增', '配股',
    '授信额度', '银行授信',
    '股价', '涨停', '跌停', '市值', '市盈率', '解禁',
    '股东减持', '股东增持', '股权激励', '限售股',
    '证券时报', '中国财经报', '经济参考报',
    '市场热点回顾', '本周市场回顾', '本周要闻回顾', '热点回顾',
    '今日要闻回顾', '本周要闻', '本周市场综述', '本周金属市场回顾',
    '生态修复', '节能降耗', '绿色矿山', '清洁生产',
    '布林带', 'MACD', 'KDJ', '均线', '支撑位', '阻力位',
    '技术面', '多头排列', '空头排列', '金叉', '死叉',
    'SMM.*调研', 'Mysteel.*调研',
]

GENERIC_FINANCIAL_CONTEXT = [
    '上市', 'IPO', '股票', '股价', '市值', '市盈率', '涨停', '跌停',
    '发行', '认购', '配售', '解禁', '减持', '增持', '回购', '分红',
    '融资', '授信', '贷款', '债券', '可转债', '股权', '股东',
    '审计', '财报', '季报', '年报', '净利润', '每股收益',
    '交易所', '深交所', '上交所', '港交所', '纳斯达克',
    '保荐', '承销', '路演', '询价', '募投',
]

DEFAULT_CONTRADICTION_WEIGHTS = {
    'supply': 5, 'disruption': 5, 'demand': 4, 'cost': 4,
    'capacity': 4, 'policy': 3, 'project': 3,
    'macro': 1, 'technical': 0,
}

_cache = {}


def load_config():
    if 'cfg' not in _cache:
        import yaml
        with open(_YAML, encoding='utf-8') as f:
            raw = yaml.safe_load(f)
        kw = {}
        for tier_name in ('A', 'B', 'C'):
            for item in raw.get('tiers', {}).get(tier_name, {}).get('keywords', []):
                name = item.get('name')
                if name:
                    kw[name] = {
                        'weight': item.get('weight', 0),
                        'tier': tier_name,
                        'terms': item.get('terms', []),
                        'tags': item.get('tags', []),
                        'contradiction': item.get('contradiction'),
                        'bias': item.get('bias', 'neutral'),
                    }
        _cache['cfg'] = {
            'raw': raw,
            'keywords': kw,
            'relevance': raw.get('relevance', {}),
            'negative': list(raw.get('negative_filters', [])) + GENERIC_NEGATIVE,
            'financial': GENERIC_FINANCIAL_CONTEXT,
        }
    return _cache['cfg']


def _is_neg(content, patterns):
    return any(re.search(p, content) for p in patterns)


def is_noise(text):
    return _is_neg(text, load_config()['negative'])


def is_related(text, title=''):
    """相关性闸门: 命中品种核心词或 印尼+锌产业词 组合"""
    full = (title or '') + ' ' + (text or '')
    r = load_config()['relevance']
    if not r:
        return True
    core = r.get('core_terms') or []
    if any(t in full for t in core):
        return True
    combo = r.get('combo') or {}
    anys, withs = combo.get('any') or [], combo.get('with_any') or []
    if anys and withs and any(a in full for a in anys) and any(w in full for w in withs):
        return True
    return False


def _cw(tags):
    ws = [DEFAULT_CONTRADICTION_WEIGHTS.get(t, 2) for t in tags]
    return max(ws) if ws else 2


def _bias(tags, hit_terms, yaml_bias='neutral', content=''):
    if yaml_bias not in (None, 'neutral'):
        return yaml_bias
    bull = {'罢工', '事故', '火灾', '爆炸', '洪水', '地震', '禁令',
            '出口限制', '限产', '停产整顿', '安全检查', '电力短缺',
            '限电', '制裁', '出口禁令', '港口堵塞', '检修',
            '排产增长', '需求增加', '订单增加', '消费增长',
            '上涨', '增长', '上升', '回升', '增加', '走高', '攀升', '走强'}
    bear = {'扩产', '复产', '新增产能', '达产', '投产', '产量增长',
            '产能释放', '一期投产', '二期扩产', '审批通过',
            '亏损', '成本倒挂', '利润下滑', '亏损扩大',
            '排产下降', '减产', '需求疲软',
            '收窄', '回落', '下跌', '下滑', '走弱', '偏弱', '承压',
            '下行', '降低', '减少', '倒挂', '亏损扩大'}
    # 命中词本身带方向 (如"罢工")
    hs = set(hit_terms)
    b_kw, s_kw = bool(hs & bull), bool(hs & bear)
    # 正文趋势词 (如"利润收窄""价格回落")
    b_tx = any(w in (content or '') for w in bull)
    s_tx = any(w in (content or '') for w in bear)
    b, s = b_kw or b_tx, s_kw or s_tx
    if b and not s:
        return 'bullish'
    if s and not b:
        return 'bearish'
    if b and s:
        return 'neutral'
    if 'disruption' in tags:
        return 'bullish'
    return 'neutral'


def score_news(content, title='', keywords=None,
               financial_context=None, contradiction_weights=None):
    """
    v2 评分: 维度去重 + 矛盾权重 + 多空方向 + 交叉验证 + 相关性闸门

    返回: (score, tier, matched_terms, direction, contradiction_summary, relevant)
    - score: 0-100, 不相关新闻被 relevance 闸门压到 cap_score(默认5)
    - tier: A/B/C
    - matched_terms: 去重命中词
    - direction: bullish/bearish/neutral/None
    - contradiction_summary: {矛盾名: {score, terms, bias, weight}}
    - relevant: bool, 是否通过相关性闸门
    """
    cfg = load_config()
    if keywords is None:
        keywords = cfg['keywords']
    if financial_context is None:
        financial_context = cfg['financial']
    if contradiction_weights is None:
        contradiction_weights = {k: v.get('weight', 3)
                                 for k, v in (cfg['raw'].get('contradictions') or {}).items()}

    full_text = (title or '') + ' ' + (content or '')
    is_fin = sum(1 for t in financial_context if t in full_text) >= 3
    relevant = is_related(content, title)

    by_contradiction = defaultdict(lambda: {'score': 0, 'terms': [], 'tags': [], 'bias': 'neutral'})
    all_matched = []
    tier_kw = set()

    for kw_name, c in keywords.items():
        terms = c.get('terms', [])
        weight = c.get('weight', 0)
        tags = c.get('tags', [])
        hit = [t for t in terms if t in full_text]
        if not hit:
            continue
        all_matched.extend(hit)
        tier_kw.add(c.get('tier', 'C'))

        contradiction = c.get('contradiction')
        if not contradiction:
            for t, nm in (('disruption', 'disruption'), ('supply', 'supply'),
                          ('demand', 'demand'), ('cost', 'cost'),
                          ('capacity', 'capacity'), ('policy', 'policy'),
                          ('project', 'project')):
                if t in tags:
                    contradiction = nm
                    break
            else:
                contradiction = 'other'

        eff = weight // 2 if (is_fin and 'supply' in tags) else weight
        bias = _bias(tags, hit, c.get('bias', 'neutral'), content or title)
        entry = by_contradiction[contradiction]
        entry['score'] = max(entry['score'], eff)
        entry['terms'].extend(hit)
        for t in tags:
            if t not in entry['tags']:
                entry['tags'].append(t)
        if bias != 'neutral' and entry['bias'] == 'neutral':
            entry['bias'] = bias

    star_mult = {1: 0.5, 2: 0.7, 3: 1.0, 4: 1.3, 5: 1.5}
    total = 0
    summary = {}
    for contradiction, entry in by_contradiction.items():
        cw = contradiction_weights.get(contradiction, _cw(entry['tags']))
        dim = int(entry['score'] * star_mult.get(cw, 1.0))
        total += dim
        summary[contradiction] = {
            'score': dim,
            'terms': list(dict.fromkeys(entry['terms'])),
            'bias': entry['bias'],
            'weight': cw,
        }

    active = [c for c, v in summary.items() if v['bias'] != 'neutral']
    b_cnt = sum(1 for c in active if summary[c]['bias'] == 'bullish')
    s_cnt = sum(1 for c in active if summary[c]['bias'] == 'bearish')
    if b_cnt >= 2 or s_cnt >= 2:
        total += 5
    total = min(total, 100)

    if b_cnt > s_cnt:
        direction = 'bullish'
    elif s_cnt > b_cnt:
        direction = 'bearish'
    elif b_cnt == s_cnt > 0:
        direction = 'neutral'
    else:
        direction = None

    if is_fin and 'A' in tier_kw and 'B' not in tier_kw:
        tier = 'B'
    elif 'A' in tier_kw:
        tier = 'A'
    elif 'B' in tier_kw:
        tier = 'B'
    else:
        tier = 'C'

    # 相关性闸门: 与锌无关 → 压分降级
    if not relevant:
        cap = load_config()['relevance'].get('cap_score', 5)
        total = min(total, cap)
        tier = 'C'

    all_matched = list(dict.fromkeys(all_matched))
    return total, tier, all_matched, direction, summary, relevant


def build_entry(title, content, source='', time_str='', url=''):
    """统一新闻结构 (所有路径共用): 含 score/direction/contradictions 新字段"""
    score, tier, matched, direction, summary, relevant = score_news(content, title)
    return {
        'title': (title or '')[:80],
        'body': (content or '')[:200],
        'source': source,
        'time': (time_str or '')[:19],
        'level': tier,
        'score': score,
        'url': url,
        'direction': direction,
        'relevant': relevant,
        'contradictions': summary,
        'matched_terms': matched[:5],
    }

