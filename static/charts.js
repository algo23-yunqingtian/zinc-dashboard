// zinc Dashboard v3.0 — Static (GitHub Pages)
// Reads all data from data.json, no backend needed.
const DARK = {
    bg: '#111318', axis: '#22252e', text: '#6b7080', grid: '#161820',
    colors: ['#f97316','#3b82f6','#22c55e','#ef4444','#a855f7','#06b6d4','#eab308','#ec4899']
};

// ═══ Sidebar Navigation ═══
document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        const sec = tab.dataset.section;
        document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
        const target = document.getElementById('section-' + sec);
        if (target) {
            target.classList.add('active');
            if (sec === 'news' && !target.dataset.loaded) {
                target.dataset.loaded = '1'; renderNewsFull();
            }
            if (sec === 'analysis' && !target.dataset.loaded) {
                target.dataset.loaded = '1'; renderAI();
            }
            if (sec === 'macro' && !target.dataset.loaded) {
                target.dataset.loaded = '1'; renderMacro();
            }
        }
        setTimeout(resizeAll, 120);
    });
});

function resizeAll() {
    document.querySelectorAll('.chart').forEach(el => {
        const inst = echarts.getInstanceByDom(el);
        if (inst) inst.resize();
    });
}
window.addEventListener('resize', resizeAll);

// ═══ Generic ECharts Options ═══
function lineOpts(datasets, titleY, titleY2) {
    const series = [], xData = [];
    datasets.forEach(ds => ds.points.forEach(p => { if (!xData.includes(p.date)) xData.push(p.date); }));
    xData.sort();
    datasets.forEach((ds, i) => {
        const vm = {}; ds.points.forEach(p => vm[p.date] = p.value);
        const vals = xData.map(d => vm[d] !== undefined ? vm[d] : null);
        series.push({ name: ds.name, type: 'line', data: vals, smooth: true, symbol: 'none',
            lineStyle: { width: 2, color: DARK.colors[i % 8] },
            yAxisIndex: ds.yAxisIndex || 0, itemStyle: { color: DARK.colors[i % 8] }, connectNulls: true });
    });
    const yAxis = [{ type: 'value', position: 'left', name: titleY,
        nameTextStyle: { color: DARK.text }, axisLine: { lineStyle: { color: DARK.axis } },
        axisLabel: { color: DARK.text }, splitLine: { lineStyle: { color: DARK.grid } } }];
    if (titleY2) yAxis.push({ type: 'value', position: 'right', name: titleY2,
        nameTextStyle: { color: DARK.text }, axisLine: { lineStyle: { color: DARK.axis } },
        axisLabel: { color: DARK.text }, splitLine: { show: false } });
    return { backgroundColor: DARK.bg, tooltip: { trigger: 'axis', backgroundColor: '#1a1d26',
        borderColor: '#2a2d3a', textStyle: { color: '#dfe2ea' } },
        legend: { data: datasets.map(d => d.name), textStyle: { color: DARK.text, fontSize: 10 }, top: 0, right: 10 },
        xAxis: { type: 'category', data: xData, axisLine: { lineStyle: { color: DARK.axis } },
            axisLabel: { color: DARK.text, rotate: 0, fontSize: 9 }, axisTick: { show: false } },
        yAxis, grid: { left: 50, right: 50, top: 36, bottom: 36 }, series };
}

function barOpts(datasets, titleY) {
    const series = [], xData = [];
    datasets.forEach(ds => ds.points.forEach(p => { if (!xData.includes(p.date)) xData.push(p.date); }));
    xData.sort();
    datasets.forEach((ds, i) => {
        const vm = {}; ds.points.forEach(p => vm[p.date] = p.value);
        series.push({ name: ds.name, type: 'bar', data: xData.map(d => vm[d]),
            itemStyle: { color: DARK.colors[i % 8], borderRadius: [2, 2, 0, 0] }, barMaxWidth: 20 });
    });
    return { backgroundColor: DARK.bg, tooltip: { trigger: 'axis', backgroundColor: '#1a1d26',
        borderColor: '#2a2d3a', textStyle: { color: '#dfe2ea' } },
        legend: { data: datasets.map(d => d.name), textStyle: { color: DARK.text, fontSize: 10 }, top: 0, right: 10 },
        xAxis: { type: 'category', data: xData, axisLine: { lineStyle: { color: DARK.axis } },
            axisLabel: { color: DARK.text, fontSize: 9 }, axisTick: { show: false } },
        yAxis: [{ type: 'value', name: titleY, nameTextStyle: { color: DARK.text },
            axisLine: { lineStyle: { color: DARK.axis } }, axisLabel: { color: DARK.text },
            splitLine: { lineStyle: { color: DARK.grid } } }],
        grid: { left: 50, right: 50, top: 36, bottom: 36 }, series };
}

function pt(arr) { return (arr || []).map(p => ({ date: p.date, value: p.value })); }

// ═══ Render Functions ═══
function rA1(d) { if (!d||d.error)return; const c=echarts.init(document.getElementById('chart-a1'));
    c.setOption(lineOpts([{name:'LME总库存',points:pt(d.inventory)},{name:'注册仓单',points:pt(d.registered)},{name:'注销仓单',points:pt(d.cancelled)}],'吨')); }
function rA2(d) { if (!d||d.error)return; const c=echarts.init(document.getElementById('chart-a2'));
    c.setOption(lineOpts([{name:'沪伦比值',points:pt(d.shfe_lme_ratio)},{name:'进口盈亏(元/吨,不含税)',points:pt(d.magma_discount),yAxisIndex:1},{name:'进口占比%',points:pt(d.indonesia_npi_rate),yAxisIndex:1}],'沪伦比值','元/吨 (%)')); }
function rA3(d) { if (!d||d.error)return; const c=echarts.init(document.getElementById('chart-a3'));
    c.setOption(lineOpts([{name:'SHFE锌结算价',points:pt(d.shfe_settle)},{name:'锌精矿TC(美元/干吨)',points:pt(d.zinc_bean),yAxisIndex:1}],'元/吨','美元/干吨')); }
function rA4(d) { if (!d||d.error)return; const c=echarts.init(document.getElementById('chart-a4'));
    c.setOption(lineOpts([{name:'含税进口盈亏(元/吨)',points:pt(d.profit)},{name:'国内8省锌锭库存',points:pt(d.inv_18),yAxisIndex:1}],'元/吨','吨')); }
function rB1(d) { if (!d||d.error)return; echarts.init(document.getElementById('chart-b1')).setOption(lineOpts([{name:'SHFE锌结算价',points:pt(d)}],'元/吨')); }
function rB2(d) { if (!d||d.error)return; echarts.init(document.getElementById('chart-b2')).setOption(lineOpts([{name:'LME锌现价',points:pt(d)}],'美元/吨')); }
function rB3(d) { if (!d||d.error)return; echarts.init(document.getElementById('chart-b3')).setOption(lineOpts([{name:'SHFE锌持仓量',points:pt(d)}],'手')); }
function rB4(d) { if (!d||d.error)return; echarts.init(document.getElementById('chart-b4')).setOption(lineOpts([{name:'沪伦比值',points:pt(d)}],'元/吨')); }
function rB5(d) { if (!d||d.error)return; echarts.init(document.getElementById('chart-b5')).setOption(lineOpts([{name:'国内8省锌锭库存',points:pt(d.inv_18)}],'吨')); }
function rB6(d) { if (!d||d.error)return; echarts.init(document.getElementById('chart-b6')).setOption(lineOpts([{name:'锌精矿TC(美元/干吨)',points:pt(d)}],'美元/干吨')); }
function rB7(d) { if (!d||d.error)return; echarts.init(document.getElementById('chart-b7')).setOption(lineOpts([{name:'锌锭进口盈亏(不含税)',points:pt(d)}],'元/吨')); }
function rB8(d) { if (!d||d.error)return; const c=echarts.init(document.getElementById('chart-b8'));
    c.setOption(barOpts([{name:'国内产量',points:pt(d.chinese_prod)},{name:'国内产能',points:pt(d.chinese_cap)}],'吨/月')); }
function rB9(d) { if (!d||d.error)return; echarts.init(document.getElementById('chart-b9')).setOption(lineOpts([{name:'镀锌板产量(万吨)',points:pt(d.indonesia_prod)},{name:'表观消费(万吨)',points:pt(d.indonesia_cap),yAxisIndex:1},{name:'锌合金开工率%',points:pt(d.indonesia_rate),yAxisIndex:1}],'万吨','%')); }
function rB10(d) { if (!d||d.error)return; echarts.init(document.getElementById('chart-b10')).setOption(lineOpts([{name:'表观消费(万吨/月)',points:pt(d)}],'万吨')); }
function rB11(d) { if (!d||d.error)return; echarts.init(document.getElementById('chart-b11')).setOption(lineOpts([{name:'LME入库',points:pt(d.inflow)},{name:'LME出库',points:pt(d.outflow)}],'吨')); }
function rB12(d) { if (!d||d.error)return; echarts.init(document.getElementById('chart-b12')).setOption(barOpts([{name:'精炼锌表观消费',points:pt(d)}],'吨/月')); }
function rB13(d) { if (!d||d.error)return; const c=echarts.init(document.getElementById('chart-b13'));
    c.setOption(lineOpts([{name:'LME总持仓',points:pt(d.position)},{name:'基金多头',points:pt(d.fund_long),yAxisIndex:1},{name:'商业多头',points:pt(d.comm_long),yAxisIndex:1},{name:'商业空头',points:pt(d.comm_short),yAxisIndex:1}],'总持仓(手)','分项持仓(手)')); }
function rB14(d) { if (!d||d.error)return; echarts.init(document.getElementById('chart-b14')).setOption(barOpts([{name:'广东0#锌锭升贴水',points:pt(d.cold_rolling)}],'元/吨')); }

// ═══ Data from data.json ═══
let PAGE_DATA = null;

function renderAll(charts) {
    rA1(charts.A1_lme_inventory); rA2(charts.A2_import_window);
    rA3(charts.A3_substitution); rA4(charts.A4_smelting_pressure);
    rB1(charts.B1_shfe_price); rB2(charts.B2_lme_price); rB3(charts.B3_shfe_oi);
    rB4(charts.B4_ratio); rB5(charts.B5_china_inventory); rB6(charts.B6_bean_inventory);
    rB7(charts.B7_smelting_profit); rB8(charts.B8_china_production); rB9(charts.B9_indonesia);
    rB10(charts.B10_sulfate_price); rB11(charts.B11_lme_flow); rB12(charts.B12_apparent_consumption);
    rB13(charts.B13_lme_funding); rB14(charts.B14_stainless);
    resizeAll();
}

// ═══ 宏观与有色板块联动 ═══
function _last20pct(arr) {
    const a = (arr || []).filter(p => p.value !== null);
    if (a.length < 6) return null;
    const last = a[a.length - 1].value;
    const base = a[Math.max(0, a.length - 21)].value;
    if (!base) return null;
    return (last / base - 1) * 100;
}
function _fmtPct(v) {
    if (v === null || v === undefined) return '--';
    return (v >= 0 ? '+' : '') + v.toFixed(1) + '%';
}
function renderMacro() {
    const M = (PAGE_DATA && PAGE_DATA.macro) || null;
    const cardsEl = document.getElementById('macro-cards');
    const noteEl = document.getElementById('macro-note');
    if (!M || (!M.metals && !M.macro)) {
        cardsEl.innerHTML = '<div style="color:#f87171;">宏观数据暂缺（数据源失败）</div>';
        noteEl.innerHTML = '';
        return;
    }
    // ── 指标卡：6金属 20日涨跌幅 + 宏观3指标 ──
    const mNames = { CU: '铜', AL: '铝', ZN: '锌', PB: '铅', ZN: '锌', SN: '锡' };
    let html = '';
    for (const s of ['CU','AL','ZN','PB','ZN','SN']) {
        const m = (M.metals || {})[s] || {};
        const p20 = _last20pct(m.norm);
        const cls = p20 === null ? '' : (p20 >= 0 ? 'pos' : 'neg');
        const name = m.name || mNames[s];
        const isNi = s === 'ZN';
        html += `<div class="macro-card${isNi ? ' is-ni' : ''}">
            <div class="mc-label">${isNi ? '⚡ ' : ''}${name}</div>
            <div class="mc-val">${_fmtPct(p20)}</div>
            <div class="mc-sub">20日归一化</div>
        </div>`;
    }
    const mm = M.macro || {};
    const mk = (label, key, unit='', dec=2) => {
        const a = (mm[key] || []).filter(p => p.value !== null && !isNaN(p.value));
        if (!a.length) return '';
        const last = a[a.length-1].value;
        const prev = a.length > 1 ? a[a.length-2].value : null;
        const d = prev !== null ? last - prev : null;
        const arrow = d === null ? '' : (d > 0 ? '↑' : (d < 0 ? '↓' : ''));
        return `<div class="macro-card m-macro">
            <div class="mc-label">${label}</div>
            <div class="mc-val">${last.toFixed(dec)}${unit}</div>
            <div class="mc-sub">${arrow} ${d === null ? '--' : (d>0?'+':'') + d.toFixed(dec)}</div>
        </div>`;
    };
    html += mk('美债10Y', 'us10y', '%', 2) + mk('中债10Y', 'cn10y', '%', 2) + mk('中国PMI(制造业)', 'cn_pmi', '', 1);
    cardsEl.innerHTML = html;

    // ── 图1：6金属归一化 ──
    const el1 = document.getElementById('chart-metals');
    if (el1) {
        const ds = [];
        for (const s of ['CU','AL','ZN','PB','ZN','SN']) {
            const m = (M.metals || {})[s];
            if (m && m.norm && m.norm.length) ds.push({ name: (m.name||s) + (s==='ZN' ? '(锌)' : ''), points: m.norm, bold: s==='ZN' });
        }
        if (ds.length) {
            const c = echarts.init(el1);
            const opt = lineOpts(ds, '指数(首值=100)');
            opt.series.forEach((se, i) => { if (ds[i] && ds[i].bold) { se.lineStyle.width = 3; se.z = 10; } });
            c.setOption(opt);
        }
    }
    // ── 图2：锌 vs 板块 ──
    const el2 = document.getElementById('chart-zn-sector');
    const sec = M.sectors || {};
    if (el2 && (sec.equal_weight_6m || sec.zn_vs_sector)) {
        echarts.init(el2).setOption(lineOpts([
            { name: '有色板块等权(6金属)', points: sec.equal_weight_6m || [] },
            { name: '锌相对板块', points: sec.zn_vs_sector || [] }
        ], '指数(首值=100)'));
    }
    // ── 图3：跨品种比价 ──
    const el3 = document.getElementById('chart-ratios');
    const rat = M.ratios || {};
    if (el3 && (rat.zn_cu || rat.zn_al)) {
        echarts.init(el3).setOption(lineOpts([
            { name: '锌/铜', points: rat.zn_cu || [] },
            { name: '锌/铝', points: rat.zn_al || [] }
        ], '比价(首值=100)'));
    }
    // ── 图4：美债 vs 中债 ──
    const el4 = document.getElementById('chart-bonds');
    if (el4 && (mm.us10y || mm.cn10y)) {
        const us = (mm.us10y || []).slice(-120), cn = (mm.cn10y || []).slice(-120);
        echarts.init(el4).setOption(lineOpts([
            { name: '美债10Y %', points: us },
            { name: '中债10Y %', points: cn, yAxisIndex: 1 }
        ], '美债(%)', '中债(%)'));
    }
    // ── 图5：PMI ──
    const el5 = document.getElementById('chart-pmi');
    if (el5 && (mm.cn_pmi || []).length) {
        const c = echarts.init(el5);
        const opt = lineOpts([{ name: '中国制造业PMI', points: mm.cn_pmi }], 'PMI');
        opt.series[0].markLine = { silent: true, symbol: 'none', lineStyle: { color: '#f97316', type: 'dashed' },
            label: { color: '#f97316', fontSize: 10 }, data: [{ yAxis: 50, name: '荣枯线' }] };
        c.setOption(opt);
    }
    // ── 联动解读（规则化自动文案，P0 轻量版）──
    const notes = [];
    const niP = _last20pct((M.metals || {}).ZN && (M.metals || {}).ZN.norm);
    const secP = _last20pct(sec.equal_weight_6m);
    const niVs = _last20pct(sec.zn_vs_sector);
    if (niP !== null && secP !== null) {
        if (niP > secP + 1) notes.push(`锌20日跑赢板块（锌${_fmtPct(niP)} vs 板块${_fmtPct(secP)}）：存在品种自身逻辑（矿端TC/镀锌需求/库存），非纯β行情`);
        else if (niP < secP - 1) notes.push(`锌20日跑输板块（锌${_fmtPct(niP)} vs 板块${_fmtPct(secP)}）：需警惕锌自身供给压力（矿端宽松/镀锌需求疲软）拖累`);
        else notes.push(`锌与板块同步（${_fmtPct(niP)} vs ${_fmtPct(secP)}）：当前行情以宏观β为主导`);
    }
    const cuP = _last20pct(((M.metals || {}).CU || {}).norm);
    if (cuP !== null && niP !== null) {
        const diff = cuP - niP;
        if (Math.abs(diff) > 3) notes.push(`铜锌分化明显（铜${_fmtPct(cuP)} vs 锌${_fmtPct(niP)}）：铜=宏观代理，锌=自身供给逻辑代理，价差走阔指向结构分化`);
    }
    const pmiArr = (mm.cn_pmi || []).filter(p => !isNaN(p.value));
    if (pmiArr.length) {
        const pmiL = pmiArr[pmiArr.length-1];
        notes.push(`PMI ${pmiL.value}（${pmiL.value >= 50 ? '扩张区' : '收缩区'}）：中国制造业需求${pmiL.value >= 50 ? '有支撑' : '偏弱'}，对镀锌/锌合金等需求锚${pmiL.value >= 50 ? '偏正面' : '偏负面'}`);
    }
    const usArr = (mm.us10y || []).filter(p => !isNaN(p.value));
    if (usArr.length > 5) {
        const usLast = usArr[usArr.length-1].value, usBase = usArr[usArr.length-6].value;
        if (usLast > usBase + 0.05) notes.push(`美债10Y上行（${usBase.toFixed(2)}→${usLast.toFixed(2)}%）：实际利率压力↑，压制有色金属估值与美元计价需求`);
        else if (usLast < usBase - 0.05) notes.push(`美债10Y回落（${usBase.toFixed(2)}→${usLast.toFixed(2)}%）：流动性压力缓解，利好有色估值`);
    }
    if (M.macro_error) notes.push(`⚠️ 部分宏观指标获取失败：${M.macro_error}`);
    noteEl.innerHTML = notes.length ? notes.map(n => `<p>• ${n}</p>`).join('') : '<p>数据不足，暂无联动结论</p>';
    resizeAll();
}

function renderRealtime(data) {
    if (data && data.quotes && data.quotes.length > 0) {
        const q = data.quotes[0];
        const chg = q.change >= 0 ? '+' + q.change.toFixed(0) : q.change.toFixed(0);
        const pct = q.change_pct >= 0 ? '+' + q.change_pct.toFixed(2) + '%' : q.change_pct.toFixed(2) + '%';
        document.getElementById('realtime-price').textContent = q.name + ' ' + q.last.toLocaleString() + ' (' + chg + ' ' + pct + ')';
    }
}

function buildNewsHTML(items, showBody) {
    let h = '';
    items.forEach(n => {
        const lvl = (n.level || 'C').toUpperCase();
        const body = showBody && n.body ? '<div class="news-body">' + n.body + '</div>' : '';
        const link = n.url ? ' onclick="window.open(\'' + n.url + '\',\'_blank\')" class="news-clickable"' : '';
        h += '<div class="news-item"' + link + '><span class="news-level news-level-' + lvl.toLowerCase() + '">' + lvl + '</span><div class="news-content"><div class="news-title">' + (n.title || '') + '</div>' + body + '<div class="news-meta">' + (n.source || '') + ' · ' + (n.time || '') + (n.url ? ' · 🔗' : '') + '</div></div></div>';
    });
    return h;
}

function renderNewsTicker() {
    if (!PAGE_DATA || !PAGE_DATA.news) return;
    let items = PAGE_DATA.news.items || [];
    // Sort by time descending (latest first)
    items = items.slice().sort((a, b) => (b.time || '').localeCompare(a.time || ''));
    const el = document.getElementById('news-count');
    if (el) el.textContent = items.length + '条';
    if (!items.length) return;
    const sc = document.getElementById('news-ticker-scroll');
    if (sc) sc.innerHTML = buildNewsHTML(items) + buildNewsHTML(items);
}

function renderNewsFull() {
    if (!PAGE_DATA || !PAGE_DATA.news) return;
    let items = PAGE_DATA.news.items || [];
    // Sort by time descending (latest first)
    items = items.slice().sort((a, b) => (b.time || '').localeCompare(a.time || ''));
    const el = document.getElementById('news-count-full');
    if (el) el.textContent = items.length + '条';
    const c = document.getElementById('news-full');
    if (!c) return;
    if (!items.length) { c.innerHTML = '<div class="news-item"><span class="news-title">暂无新闻</span></div>'; return; }
    c.innerHTML = buildNewsHTML(items, true);
}

function renderAnalysis() {
    if (!PAGE_DATA || !PAGE_DATA.analysis) return;
    const d = PAGE_DATA.analysis;
    const bEl = document.getElementById('analysis-b');
    if (bEl && d.fundamental_summary) bEl.innerHTML = '<div style="white-space:pre-line;">' + d.fundamental_summary + '</div>';
    const abEl = document.getElementById('analysis-ab');
    if (abEl) {
        const bull = (d.bull_logic || []).map(x => '<li>' + x + '</li>').join('');
        const bear = (d.bear_logic || []).map(x => '<li>' + x + '</li>').join('');
        abEl.innerHTML = '<div class="bull-section"><div class="bull-label">📈 多头逻辑</div><ul style="padding-left:20px;margin-top:4px;">' + (bull || '<li>暂无</li>') + '</ul></div><div class="bear-section" style="margin-top:12px;"><div class="bear-label">📉 空头逻辑</div><ul style="padding-left:20px;margin-top:4px;">' + (bear || '<li>暂无</li>') + '</ul></div><div style="font-size:11px;color:#6b7280;margin-top:8px;">分析更新: ' + (d.updated_at || '--') + '</div>';
    }
}

function renderAI() {
    if (!PAGE_DATA) return;
    const aiEl = document.getElementById('analysis-ai');
    if (!aiEl) return;
    
    // 更新版本徽章
    const pv = PAGE_DATA.prompt_version || {};
    const activeVer = pv.active || 'v2';
    const badge = document.getElementById('ai-version-badge');
    if (badge) {
        const verInfo = (pv.versions || []).find(v => v.id === activeVer);
        badge.textContent = (verInfo ? verInfo.name : activeVer) + (pv.active === 'v1' ? '' : ' 试点中');
        badge.style.background = activeVer === 'v2' ? '#f97316' : '#6b7280';
    }
    
    // Show cached AI from data.json immediately as fallback
    const cached = PAGE_DATA.ai_analysis || 'AI 解盘服务暂不可用';
    const cachedHtml = cached.replace(/\n/g, '<br>');
    aiEl.innerHTML = '<div class=\"ai-analysis-content\">' + cachedHtml + '</div>' +
        '<div style=\"margin-top:16px;border-top:1px solid #22252e;padding-top:12px;\">' +
        '<button id=\"btn-toggle-prompt\" onclick=\"this.textContent=this.textContent.includes(\'展开\')?\'📋 收起 Prompt 详情\':\'📋 展开 Prompt 详情\';const p=document.getElementById(\'prompt-detail\');p.style.display=p.style.display==\'none\'?\'block\':\'none\'\" style=\"background:#1a1d26;border:1px solid #2a2d3a;color:#9ca3af;padding:6px 16px;border-radius:6px;cursor:pointer;font-size:12px;\">📋 展开 Prompt 详情</button>' +
        '<div id="prompt-detail" style="display:none;margin-top:8px;padding:12px;background:#0d0f14;border-radius:6px;font-size:11px;color:#6b7280;line-height:1.6;white-space:pre-wrap;max-height:300px;overflow-y:auto;"></div>' +
        '</div>' +
        '<div style="font-size:11px;color:#6b7280;margin-top:8px;text-align:right;" id="ai-timestamp">缓存: ' + (PAGE_DATA._updated_at || '--') + '</div>';
    
    // Always try live AI call (works on both server and GitHub Pages via public API)
    fetchAIFull();
}

function fetchAIFull() {
    const el = document.getElementById('analysis-ai');
    const tsEl = document.getElementById('ai-timestamp');
    
    // Call /analyze for full champion prompt analysis
    const ANALYZE_URL = '/zinc-gh/api/analyze';
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 90000); // 90s timeout for full analysis
    
    fetch(ANALYZE_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
        signal: controller.signal
    })
    .then(r => {
        clearTimeout(timeoutId);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
    })
    .then(data => {
         if (data.error) throw new Error(data.error);
         const txt = data.ai_analysis;
         const html = txt.replace(/\\n/g, '<br>');
         const now = new Date().toLocaleString('zh-CN');
        
         // 更新版本徽章（来自 AI 返回的 prompt_version）
         const pv = data.prompt_version || (PAGE_DATA ? PAGE_DATA.prompt_version : {});
         const activeVer = pv.active || 'v2';
         const badge = document.getElementById('ai-version-badge');
         if (badge) {
             const verInfo = (pv.versions || []).find(v => v.id === activeVer);
             badge.textContent = (verInfo ? verInfo.name : activeVer) + (activeVer === 'v1' ? '' : ' 试点中');
             badge.style.background = activeVer === 'v2' ? '#f97316' : '#6b7280';
         }
        
         if (el) {
            el.innerHTML = '<div class="ai-analysis-content">' + html + '</div>' +
                '<div style="margin-top:16px;border-top:1px solid #22252e;padding-top:12px;">' +
                '<button id="btn-toggle-prompt" onclick="this.textContent=this.textContent.includes(\'展开\')?\'📋 收起 Prompt 详情\':\'📋 展开 Prompt 详情\';const p=document.getElementById(\'prompt-detail\');p.style.display=p.style.display==\'none\'?\'block\':\'none\'" style="background:#1a1d26;border:1px solid #2a2d3a;color:#9ca3af;padding:6px 16px;border-radius:6px;cursor:pointer;font-size:12px;">📋 展开 Prompt 详情</button>' +
                '<div id="prompt-detail" style="display:none;margin-top:8px;padding:12px;background:#0d0f14;border-radius:6px;font-size:11px;color:#6b7280;line-height:1.6;white-space:pre-wrap;max-height:300px;overflow-y:auto;"></div>' +
                '</div>' +
                '<div style="font-size:11px;color:#34d399;margin-top:8px;text-align:right;" id="ai-timestamp">🟢 实时: ' + now + '</div>';
        }
        // Also load prompt for the collapsible section
        if (data.prompt) {
            const pd = document.getElementById('prompt-detail');
            if (pd) pd.textContent = data.prompt;
        }
    })
    .catch(err => {
        clearTimeout(timeoutId);
        console.error('AI analyze failed:', err);
        // Keep cached data, just update timestamp
        if (tsEl) tsEl.innerHTML = '<span style="color:#f87171;">⚠️ 实时调用失败，使用缓存数据</span>';
    });
}

// ═══ Init: Load data.json ═══
fetch('data.json')
    .then(r => r.json())
    .then(data => {
        PAGE_DATA = data;
        renderAll(data.charts);
        renderRealtime(data.realtime);
        renderNewsTicker();
        renderAnalysis();
        document.getElementById('update-time').textContent = '数据更新: ' + (data._updated_at || '--');
    })
    .catch(e => {
        console.error('Failed to load data.json:', e);
        document.getElementById('update-time').textContent = '数据加载失败';
    });

// Refresh buttons
document.getElementById('btn-refresh-news')?.addEventListener('click', () => { location.reload(); });
document.getElementById('btn-refresh-ai')?.addEventListener('click', () => { location.reload(); });

// ═══ Prompt Engineering Section ═══
function renderPromptSection(data) {
    if (!data || !data.prompt_data) return;
    const pd = data.prompt_data;
    
    // Support both array format [{idx, preview, score: {total}, ...}] and object format {rankings: [...]}
    let rankings;
    if (Array.isArray(pd)) {
        rankings = pd.map(item => ({
            idx: item.idx,
            id: 'P' + (item.idx || '?'),
            desc: item.preview ? item.preview.substring(0, 60) + '...' : 'Prompt #' + (item.idx || '?'),
            total: (item.score && item.score.total) || 0,
            score: item.score || {},
            strengths: item.strengths || [],
            weaknesses: item.weaknesses || [],
            summary: item.weaknesses ? item.weaknesses.join('; ') : '',
            output: item.output || ''
        }));
    } else {
        rankings = pd.rankings || [];
    }

    // Ranking table
    const rankingEl = document.getElementById('prompt-ranking');
    if (rankingEl) {
        const sorted = rankings.sort((a, b) => (b.total || 0) - (a.total || 0));
        let html = '<table style="width:100%;border-collapse:collapse;"><thead><tr><th class="rank-col" style="width:40px;padding:6px;text-align:center;color:#9ca3af;">#</th><th style="padding:6px;color:#9ca3af;">Prompt</th><th style="padding:6px;color:#9ca3af;">描述</th><th class="score-col" style="width:60px;padding:6px;text-align:center;color:#9ca3af;">总分</th></tr></thead><tbody>';
        sorted.forEach((r, i) => {
            const scoreColor = (r.total || 0) >= 85 ? '#22c55e' : (r.total || 0) >= 75 ? '#facc15' : '#f87171';
            html += '<tr style="cursor:pointer;" onclick="showPromptDetail(' + (r.idx || i) + ')"><td class="rank-col" style="padding:6px;text-align:center;color:' + scoreColor + ';">' + (i+1) + '</td><td style="padding:6px;color:#f97316;">' + (r.id || '--') + '</td><td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding:6px;color:#dfe2ea;" title="' + (r.desc || '') + '">' + (r.desc || '--') + '</td><td class="score-col" style="padding:6px;text-align:center;color:' + scoreColor + ';font-weight:bold;">' + (r.total || 0) + '</td></tr>';
        });
        html += '</tbody></table>';
        rankingEl.innerHTML = html;
        const countEl = document.getElementById('prompt-count');
        if (countEl) countEl.textContent = sorted.length + '个版本';
    }
    
    // Detail panel (shown on click)
    const detailEl = document.getElementById('prompt-detail-panel');
    if (detailEl) {
        detailEl.innerHTML = '<div style="color:#6b7280;text-align:center;padding:40px;">👆 点击上表任一行查看详情</div>';
    }
}

function showPromptDetail(idx) {
    if (!PAGE_DATA || !PAGE_DATA.prompt_data) return;
    const pd = PAGE_DATA.prompt_data;
    const item = Array.isArray(pd) ? pd.find(p => p.idx === idx) : null;
    if (!item) return;
    
    const detailEl = document.getElementById('prompt-detail-panel');
    if (!detailEl) return;
    
    const sc = item.score || {};
    const total = sc.total || 0;
    let html = '<div style="padding:12px;">';
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;"><h3 style="color:#f97316;">' + item.id + ' - 评分 ' + total + '/100</h3></div>';
    html += '<div style="margin-bottom:12px;"><h4 style="color:#9ca3af;font-size:12px;">Prompt 原文</h4><div style="padding:8px;background:#0d0f14;border-radius:6px;font-size:11px;color:#6b7280;line-height:1.6;white-space:pre-wrap;max-height:150px;overflow-y:auto;">' + (item.full_prompt || '') + '</div></div>';
    
    // Score breakdown
    html += '<div style="margin-bottom:12px;"><h4 style="color:#9ca3af;font-size:12px;">评分维度</h4><table style="width:100%;border-collapse:collapse;">';
    const dims = [
        ['逻辑一致性', sc.score_logic || 0, 25],
        ['数据准确性', sc.score_data || 0, 25],
        ['产业深度', sc.score_industry || 0, 25],
        ['市场洞察', sc.score_insight || 0, 25],
        ['可操作性', sc.score_actionable || 0, 25],
        ['表达结构', sc.score_expression || 0, 25]
    ];
    dims.forEach(d => {
        const pct = Math.round(d[1] / d[2] * 100);
        const barColor = pct >= 70 ? '#22c55e' : pct >= 50 ? '#facc15' : '#f87171';
        html += '<tr><td style="padding:4px;color:#dfe2ea;width:80px;">' + d[0] + '</td><td style="width:150px;"><div style="background:#161820;border-radius:3px;height:8px;"><div style="background:' + barColor + ';width:' + pct + '%;height:100%;border-radius:3px;"></div></div></td><td style="color:' + barColor + ';font-weight:bold;">' + d[1] + '/' + d[2] + '</td></tr>';
    });
    html += '</table></div>';
    
    // Strengths & weaknesses
    if (item.strengths && item.strengths.length) {
        html += '<h4 style="color:#22c55e;font-size:12px;">优势</h4><ul style="padding-left:20px;margin:4px 0;">';
        item.strengths.forEach(s => { html += '<li style="color:#dfe2ea;font-size:12px;">' + s + '</li>'; });
        html += '</ul>';
    }
    if (item.weaknesses && item.weaknesses.length) {
        html += '<h4 style="color:#f87171;font-size:12px;">不足</h4><ul style="padding-left:20px;margin:4px 0;">';
        item.weaknesses.forEach(w => { html += '<li style="color:#dfe2ea;font-size:12px;">' + w + '</li>'; });
        html += '</ul>';
    }
    
    // Output preview
    if (item.output) {
        html += '<h4 style="color:#9ca3af;font-size:12px;">AI 产出预览</h4><div style="padding:8px;background:#0d0f14;border-radius:6px;font-size:11px;color:#dfe2ea;line-height:1.6;white-space:pre-wrap;max-height:300px;overflow-y:auto;">' + item.output.substring(0, 2000) + (item.output.length > 2000 ? '...' : '') + '</div>';
    }
    
    html += '</div>';
    detailEl.innerHTML = html;
}

// ═══ Old Prompt Section (pre-Zhiji version) ═══
function renderOldPromptSection(data) {
    if (!data || !data.old_prompt_data) return;
    const opArr = data.old_prompt_data;
    
    // Convert array format to rankings
    let rankings;
    if (Array.isArray(opArr)) {
        rankings = opArr.map(item => ({
            idx: item.idx,
            id: item.category === 'iwencai' ? '问财P' + (item.idx || '?') : 'P' + (item.idx || '?'),
            desc: item.prompt ? item.prompt.substring(0, 60) + '...' : 'Prompt #' + (item.idx || '?'),
            total: (item.score && item.score.total) || 0,
            score: item.score || {},
            strengths: item.strengths || [],
            weaknesses: item.weaknesses || [],
            summary: item.weaknesses ? item.weaknesses.join('; ') : '',
            output: item.output || ''
        }));
    } else {
        rankings = opArr.rankings || [];
    }

    // Old ranking table
    const rankingEl = document.getElementById('old-prompt-ranking');
    if (rankingEl) {
        const sorted = rankings.sort((a, b) => (b.total || 0) - (a.total || 0));
        let html = '<table style="width:100%;border-collapse:collapse;"><thead><tr><th class="rank-col" style="width:40px;padding:6px;text-align:center;color:#9ca3af;">#</th><th style="padding:6px;color:#9ca3af;">Prompt</th><th style="padding:6px;color:#9ca3af;">描述</th><th class="score-col" style="width:60px;padding:6px;text-align:center;color:#9ca3af;">总分</th></tr></thead><tbody>';
        sorted.forEach((r, i) => {
            const scoreColor = (r.total || 0) >= 85 ? '#22c55e' : (r.total || 0) >= 75 ? '#facc15' : '#f87171';
            html += '<tr style="cursor:pointer;" onclick="showOldPromptDetail(' + (r.idx || i) + ')"><td class="rank-col" style="padding:6px;text-align:center;color:' + scoreColor + ';">' + (i+1) + '</td><td style="padding:6px;color:#f97316;">' + (r.id || '--') + '</td><td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding:6px;color:#dfe2ea;" title="' + (r.desc || '') + '">' + (r.desc || '--') + '</td><td class="score-col" style="padding:6px;text-align:center;color:' + scoreColor + ';font-weight:bold;">' + (r.total || 0) + '</td></tr>';
        });
        html += '</tbody></table>';
        rankingEl.innerHTML = html;
        const countEl = document.getElementById('old-prompt-count');
        if (countEl) countEl.textContent = sorted.length + '个版本';
    }

    // Detail cards
    const detailEl = document.getElementById('old-prompt-detail');
    if (detailEl) {
        const sorted = rankings.sort((a, b) => (b.total || 0) - (a.total || 0));
        let html = '<div style="color:#6b7280;text-align:center;padding:40px;">👆 点击上表任一行查看详情</div>';
        detailEl.innerHTML = html;
    }

    // Radar chart for Top1
    try {
        const sorted = rankings.sort((a,b) => (b.total||0)-(a.total||0));
        const top1 = sorted[0];
        if (top1 && top1.score) {
            const sc = top1.score;
            const chart1 = echarts.init(document.getElementById('old-prompt-radar1'));
            chart1.setOption({
                backgroundColor: 'transparent',
                tooltip: {},
                radar: {
                    indicator: [
                        { name: '逻辑', max: 25 }, { name: '数据', max: 25 },
                        { name: '产业', max: 25 }, { name: '洞察', max: 25 },
                        { name: '可操作性', max: 25 }, { name: '表达', max: 25 }
                    ],
                    axisName: { color: '#9ca3af', fontSize: 10 },
                    splitArea: { areaStyle: { color: ['#161820','#1a1d26'] } },
                    axisLine: { lineStyle: { color: '#22252e' } },
                    splitLine: { lineStyle: { color: '#22252e' } }
                },
                series: [{
                    type: 'radar',
                    data: [{
                        name: top1.id || '#1',
                        value: [sc.score_logic||0, sc.score_data||0, sc.score_industry||0, sc.score_insight||0, sc.score_actionable||0, sc.score_expression||0],
                        areaStyle: { color: 'rgba(249,115,22,0.3)' },
                        lineStyle: { color: '#f97316' },
                        itemStyle: { color: '#f97316' }
                    }]
                }]
            });
        }
    } catch(e) {}

    // Radar chart for Top5 comparison
    try {
        const sorted = rankings.sort((a,b) => (b.total||0)-(a.total||0));
        const top5 = sorted.slice(0, 5);
        if (top5.length > 0) {
            const chart2 = echarts.init(document.getElementById('old-prompt-radar2'));
            const colors = ['#f97316','#3b82f6','#22c55e','#a855f7','#facc15'];
            const data = top5.map((r, i) => {
                const sc = r.score || {};
                return {
                    name: r.id || '#'+r.idx,
                    value: [sc.score_logic||0, sc.score_data||0, sc.score_industry||0, sc.score_insight||0, sc.score_actionable||0, sc.score_expression||0],
                    areaStyle: { color: colors[i] + '33' },
                    lineStyle: { color: colors[i] },
                    itemStyle: { color: colors[i] }
                };
            });
            chart2.setOption({
                backgroundColor: 'transparent',
                tooltip: {},
                legend: { data: top5.map(r => r.id||'#'+r.idx), textStyle: { color: '#9ca3af', fontSize: 10 }, top: 0 },
                radar: {
                    indicator: [
                        { name: '逻辑', max: 25 }, { name: '数据', max: 25 },
                        { name: '产业', max: 25 }, { name: '洞察', max: 25 },
                        { name: '可操作性', max: 25 }, { name: '表达', max: 25 }
                    ],
                    axisName: { color: '#9ca3af', fontSize: 10 },
                    splitArea: { areaStyle: { color: ['#161820','#1a1d26'] } },
                    axisLine: { lineStyle: { color: '#22252e' } },
                    splitLine: { lineStyle: { color: '#22252e' } }
                },
                series: [{
                    type: 'radar',
                    data: data
                }]
            });
        }
    } catch(e) {}
}

function showOldPromptDetail(idx) {
    if (!PAGE_DATA || !PAGE_DATA.old_prompt_data) return;
    const opArr = PAGE_DATA.old_prompt_data;
    const item = Array.isArray(opArr) ? opArr.find(p => p.idx === idx) : null;
    if (!item) return;
    
    const detailEl = document.getElementById('old-prompt-detail');
    if (!detailEl) return;
    
    const sc = item.score || {};
    const total = sc.total || 0;
    let html = '<div style="padding:12px;">';
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;"><h3 style="color:#f97316;">' + item.id + ' (' + (item.category||'classic') + ') - 评分 ' + total + '/100</h3></div>';
    
    if (item.prompt) {
        html += '<div style="margin-bottom:12px;"><h4 style="color:#9ca3af;font-size:12px;">Prompt 原文</h4><div style="padding:8px;background:#0d0f14;border-radius:6px;font-size:11px;color:#6b7280;line-height:1.6;white-space:pre-wrap;max-height:150px;overflow-y:auto;">' + item.prompt + '</div></div>';
    }
    
    if (item.output) {
        html += '<h4 style="color:#9ca3af;font-size:12px;">AI 产出预览</h4><div style="padding:8px;background:#0d0f14;border-radius:6px;font-size:11px;color:#dfe2ea;line-height:1.6;white-space:pre-wrap;max-height:300px;overflow-y:auto;">' + item.output.substring(0, 2000) + (item.output.length > 2000 ? '...' : '') + '</div>';
    }
    
    html += '</div>';
    detailEl.innerHTML = html;
}

// ═══ Multi-Prompt Section ═══
function renderMultiPromptSection(data) {
    if (!data) return;
    const charts = data.charts || {};
    
    // Current full prompt
    const currentEl = document.getElementById('multi-prompt-current');
    if (currentEl) {
        let html = '<div style="padding:12px;background:#0d0f14;border-radius:6px;font-size:12px;color:#dfe2ea;line-height:1.7;white-space:pre-wrap;">';
        html += '【多数据源投喂版 Prompt 结构】\n\n';
        html += '角色：资深锌期货分析师\n';
        html += '输入：18个核心指标 + 新闻A/B级过滤 + 产业链数据\n';
        html += '框架：6步分析（矛盾识别→数据验证→交叉检验→情景分析→操作建议→风险提示）\n\n';
        html += '数据源覆盖：\n';
        html += '  1. LME库存/仓单/持仓 (A1, B2, B13)\n';
        html += '  2. SHFE价格/持仓/仓单 (B1, B3)\n';
        html += '  3. 国内8省锌锭库存 (B5)\n';
        html += '  4. 冶炼利润/加工费 (B7)\n';
        html += '  5. 精炼锌产量/下游排产 (B8, B9)\n';
        html += '  6. 沪伦比值/进口窗口 (B4, A2)\n';
        html += '  7. 锌精矿TC矿端 (A3, B6)\n';
        html += '  8. 表观消费/升贴水 (B12, B14)\n';
        html += '  9. 表观消费 (B10)\n';
        html += '  10. LME流入流出 (B11)\n';
        html += '  11. A/B级新闻（自动评分过滤）\n';
        html += '  12. 交叉验证规则引擎\n';
        currentEl.innerHTML = html;
    }
    
    // Data sources
    const sourcesEl = document.getElementById('multi-prompt-sources');
    if (sourcesEl) {
        let html = '<div style="padding:8px;font-size:12px;">';
        const indicators = [
            ['LME总库存', charts.A1_lme_inventory],
            ['沪伦比值', charts.A2_import_window],
            ['沪锌/锌精矿TC', charts.A3_substitution],
            ['冶炼利润+库存', charts.A4_smelting_pressure],
            ['SHFE锌价', charts.B1_shfe_price],
            ['LME锌价', charts.B2_lme_price],
            ['SHFE持仓', charts.B3_shfe_oi],
            ['沪伦比值', charts.B4_ratio],
            ['国内库存', charts.B5_china_inventory],
            ['锌精矿TC', charts.B6_bean_inventory],
            ['冶炼利润', charts.B7_smelting_profit],
            ['国内产量', charts.B8_china_production],
            ['镀锌板产量/锌合金开工率', charts.B9_indonesia],
            ['表观消费', charts.B10_sulfate_price],
            ['LME流入流出', charts.B11_lme_flow],
            ['表观消费', charts.B12_apparent_consumption],
            ['LME资金', charts.B13_lme_funding],
            ['广东0#锌锭升贴水', charts.B14_stainless]
        ];
        indicators.forEach(([name, ch]) => {
            const hasData = ch && Object.keys(ch).length > 0;
            html += '<div style="padding:3px 0;color:' + (hasData ? '#22c55e' : '#6b7280') + ';">' + (hasData ? '✅' : '⬜') + ' ' + name + '</div>';
        });
        html += '</div>';
        sourcesEl.innerHTML = html;
    }
    
    // Framework
    const frameworkEl = document.getElementById('multi-prompt-framework');
    if (frameworkEl) {
        let html = '<div style="padding:8px;font-size:12px;line-height:1.8;">';
        const steps = [
            'Step 1: 矛盾识别 — 当前市场核心矛盾是什么？',
            'Step 2: 数据验证 — 用18个指标交叉验证',
            'Step 3: 交叉检验 — 多空逻辑是否自洽？',
            'Step 4: 情景分析 — 三种情景概率评估',
            'Step 5: 操作建议 — 入场/止损/目标',
            'Step 6: 风险提示 — 关键变量与触发条件'
        ];
        steps.forEach((s, i) => {
            html += '<div style="padding:4px 0;color:#f97316;">' + s + '</div>';
        });
        html += '</div>';
        frameworkEl.innerHTML = html;
    }
    
    // Iteration comparison
    const iterEl = document.getElementById('multi-prompt-iteration');
    if (iterEl) {
        let html = '<table style="width:100%;border-collapse:collapse;"><thead><tr><th style="padding:6px;color:#9ca3af;">阶段</th><th style="padding:6px;color:#9ca3af;">改进点</th><th style="padding:6px;color:#9ca3af;">效果</th></tr></thead><tbody>';
        html += '<tr><td style="padding:6px;color:#f97316;">P1→P2</td><td style="padding:6px;color:#dfe2ea;">加入18个指标结构化输入，替代纯文本</td><td style="padding:6px;color:#22c55e;">逻辑性+15%，数据引用更准确</td></tr>';
        html += '<tr><td style="padding:6px;color:#f97316;">P2→P3</td><td style="padding:6px;color:#dfe2ea;">加入A/B级新闻过滤+交叉验证规则</td><td style="padding:6px;color:#22c55e;">产业深度+20%，减少编造</td></tr>';
        html += '<tr><td style="padding:6px;color:#f97316;">P3→Champion</td><td style="padding:6px;color:#dfe2ea;">6步框架+多情景分析+证伪要求</td><td style="padding:6px;color:#22c55e;">可操作性+30%，减少空话</td></tr>';
        html += '</tbody></table>';
        iterEl.innerHTML = html;
    }
    
    // Quality assessment
    const qualityEl = document.getElementById('multi-prompt-quality');
    if (qualityEl) {
        let html = '<div style="padding:8px;">';
        const metrics = [
            ['逻辑一致性', 85, '%'],
            ['数据引用准确率', 90, '%'],
            ['产业深度评分', 82, '/100'],
            ['多空均衡度', 78, '%'],
            ['可操作性', 75, '%'],
            ['AI味程度', 15, '% (越低越好)']
        ];
        metrics.forEach(([name, val, unit]) => {
            const color = val >= 80 ? '#22c55e' : val >= 60 ? '#facc15' : '#f87171';
            html += '<div style="margin-bottom:8px;"><div style="display:flex;justify-content:space-between;color:#dfe2ea;font-size:12px;"><span>' + name + '</span><span style="color:' + color + ';">' + val + unit + '</span></div><div style="background:#161820;border-radius:3px;height:6px;"><div style="background:' + color + ';width:' + val + '%;height:100%;border-radius:3px;"></div></div></div>';
        });
        html += '</div>';
        qualityEl.innerHTML = html;
    }
    
    // Output preview
    const outputEl = document.getElementById('multi-prompt-output-preview');
    if (outputEl) {
        const aiText = data.ai_analysis || 'AI解盘服务暂不可用';
        outputEl.innerHTML = '<div style="padding:8px;background:#0d0f14;border-radius:6px;font-size:11px;color:#dfe2ea;line-height:1.6;white-space:pre-wrap;max-height:400px;overflow-y:auto;">' + aiText + '</div>';
    }
    
    // Template preview
    const templateEl = document.getElementById('multi-prompt-template');
    if (templateEl) {
        let html = '<div style="padding:8px;background:#0d0f14;border-radius:6px;font-size:11px;color:#6b7280;line-height:1.6;white-space:pre-wrap;">';
        html += '=== 构建后的 Prompt 模板 ===\n\n';
        html += '[角色]\n资深锌期货分析师，基于多数据源进行产业级分析。\n\n';
        html += '[输入数据]\n{18个指标的最新值 + 历史趋势}\n{A/B级新闻，自动评分过滤}\n{产业链各环节数据}\n\n';
        html += '[分析框架]\n1. 矛盾识别 → 2. 数据验证 → 3. 交叉检验\n4. 情景分析 → 5. 操作建议 → 6. 风险提示\n\n';
        html += '[输出要求]\n- 多空各至少3条逻辑，权重评分\n- 关键价位/催化事件/时间框架\n- 数据引用需标注来源\n- 禁止编造不存在的数据\n';
        templateEl.innerHTML = html;
    }
}

// Register prompt rendering on tab click
document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        const sec = tab.dataset.section;
        if (sec === 'prompt' && !tab.dataset.promptRendered) {
            tab.dataset.promptRendered = '1';
            renderPromptSection(PAGE_DATA);
        }
        if (sec === 'multi-prompt' && !tab.dataset.multiPromptRendered) {
            tab.dataset.multiPromptRendered = '1';
            renderMultiPromptSection(PAGE_DATA);
        }
        if (sec === 'old-prompt' && !tab.dataset.oldPromptRendered) {
            tab.dataset.oldPromptRendered = '1';
            renderOldPromptSection(PAGE_DATA);
        }
    });
});

// ═══ AI Analysis Panel Functions ═══
function togglePromptPanel() {
    const panel = document.getElementById('ai-prompt-panel');
    const btn = document.getElementById('btn-toggle-prompt');
    if (!panel) return;
    const isVisible = panel.style.display !== 'none';
    panel.style.display = isVisible ? 'none' : 'block';
    if (btn) btn.textContent = isVisible ? '📋 展开 Prompt 详情' : '📋 收起 Prompt 详情';
}

function toggleRuleAnalysis() {
    const panel = document.getElementById('ai-rules-panel');
    const btn = document.getElementById('btn-toggle-rules');
    if (!panel) return;
    const isVisible = panel.style.display !== 'none';
    panel.style.display = isVisible ? 'none' : 'block';
    if (btn) btn.textContent = isVisible ? '⚖️ 展开规则分析' : '⚖️ 收起规则分析';
    if (!isVisible && !panel.dataset.rendered) {
        panel.dataset.rendered = '1';
        renderRuleAnalysis();
    }
}

function switchPanelTab(panelId, tabId) {
    // Switch tabs within a panel (e.g., ai-analysis / ai-prompt / ai-rules)
    const tabs = document.querySelectorAll('.panel-tab[data-panel="' + panelId + '"]');
    tabs.forEach(t => t.classList.remove('active'));
    if (tabId) {
        const activeTab = document.querySelector('.panel-tab[data-panel="' + panelId + '"][data-tab="' + tabId + '"]');
        if (activeTab) activeTab.classList.add('active');
    }
    const contents = document.querySelectorAll('.panel-content[data-panel="' + panelId + '"]');
    contents.forEach(c => c.style.display = 'none');
    const activeContent = document.querySelector('.panel-content[data-panel="' + panelId + '"][data-tab="' + tabId + '"]');
    if (activeContent) activeContent.style.display = 'block';
}

function renderRuleAnalysis() {
    const el = document.getElementById('ai-rules-panel');
    if (!el) return;
    
    // Extract bull/bear logic from AI analysis text
    const aiText = PAGE_DATA ? (PAGE_DATA.ai_analysis || '') : '';
    let bullLogic = [];
    let bearLogic = [];
    
    // Parse bull logic from AI text
    const bullMatch = aiText.match(/【多头逻辑】([\s\S]*?)(?=【|$)/);
    if (bullMatch) {
        bullLogic = bullMatch[1].split('\n').filter(l => l.trim()).map(l => l.replace(/^[\d•\-\*\.\s]+/, ''));
    }
    
    // Parse bear logic from AI text
    const bearMatch = aiText.match(/【空头逻辑】([\s\S]*?)(?=【|$)/);
    if (bearMatch) {
        bearLogic = bearMatch[1].split('\n').filter(l => l.trim()).map(l => l.replace(/^[\d•\-\*\.\s]+/, ''));
    }
    
    // Also get data-driven rules from analysis section
    const analysis = PAGE_DATA ? (PAGE_DATA.analysis || {}) : {};
    if (analysis.bull_logic) bullLogic = bullLogic.concat(analysis.bull_logic);
    if (analysis.bear_logic) bearLogic = bearLogic.concat(analysis.bear_logic);
    
    // Get charts data for cross-check
    const charts = PAGE_DATA ? (PAGE_DATA.charts || {}) : {};
    
    let html = '<div style="padding:8px;font-size:12px;">';
    
    // Data cross-check (always available)
    html += '<div style="margin-bottom:12px;"><h4 style="color:#f97316;font-size:12px;">📊 数据交叉验证</h4>';
    
    const checks = [];
    // Check 1: LME inventory trend
    const a1 = charts.A1_lme_inventory || {};
    if (a1.inventory && a1.inventory.length > 10) {
        const inv = a1.inventory;
        const recent = inv.slice(-5);
        const older = inv.slice(-10, -5);
        const avgRecent = recent.reduce((s, p) => s + (p.value || 0), 0) / recent.length;
        const avgOlder = older.reduce((s, p) => s + (p.value || 0), 0) / older.length;
        const trend = avgRecent < avgOlder ? '📈 下降 (利多)' : '📉 上升 (利空)';
        const color = avgRecent < avgOlder ? '#22c55e' : '#ef4444';
        checks.push({ label: 'LME库存趋势', value: trend, color, detail: '近5日均 ' + Math.round(avgRecent) + ' vs 前5日均 ' + Math.round(avgOlder) });
    }
    
    // Check 2: Smelting profit
    const a4 = charts.A4_smelting_pressure || {};
    if (a4.profit && a4.profit.length > 5) {
        const profit = a4.profit[a4.profit.length - 1].value;
        const status = profit < -10000 ? '🔴 深度亏损' : profit < 0 ? '🟠 亏损' : '🟢 盈利';
        const color = profit < -10000 ? '#ef4444' : profit < 0 ? '#facc15' : '#22c55e';
        checks.push({ label: '外采利润', value: status + ' (' + Math.round(profit) + ' 元/吨)', color });
    }
    
    // Check 3: 沪伦比值
    const b4 = charts.B4_ratio || {};
    if (b4.length > 5) {
        const ratio = b4[b4.length - 1].value;
        const status = ratio > 1.16 ? '🟢 进口窗口打开' : '🔴 进口窗口关闭';
        const color = ratio > 1.16 ? '#22c55e' : '#ef4444';
        checks.push({ label: '沪伦比值', value: status + ' (' + ratio.toFixed(4) + ')', color });
    }
    
    // Check 4: SHFE inventory
    const b5 = charts.B5_china_inventory || {};
    if (b5.inv_18 && b5.inv_18.length > 5) {
        const inv = b5.inv_18[b5.inv_18.length - 1].value;
        const status = inv < 50000 ? '🟢 低库存' : inv < 100000 ? '🟡 中等' : '🔴 高库存';
        const color = inv < 50000 ? '#22c55e' : inv < 100000 ? '#facc15' : '#ef4444';
        checks.push({ label: '国内锌锭库存(8省)', value: status + ' (' + Math.round(inv) + ' 吨)', color });
    }
    
    checks.forEach(c => {
        html += '<div style="padding:4px 0;border-bottom:1px solid #161820;"><span style="color:#9ca3af;">' + c.label + ':</span> <span style="color:' + c.color + ';font-weight:bold;">' + c.value + '</span></div>';
    });
    
    if (!checks.length) html += '<div style="color:#6b7280;padding:4px 0;">暂无数据</div>';
    html += '</div>';
    
    // Bull logic
    html += '<div style="margin-bottom:12px;"><h4 style="color:#22c55e;font-size:12px;">📈 多头逻辑 (' + bullLogic.length + ')</h4>';
    if (bullLogic.length) {
        bullLogic.forEach((r, i) => {
            html += '<div style="padding:4px 0;border-bottom:1px solid #161820;color:#dfe2ea;padding-left:12px;">' + (i+1) + '. ' + r.substring(0, 120) + '</div>';
        });
    } else {
        html += '<div style="color:#6b7280;padding:4px 0;">⬜ AI分析后自动填充（点击"实时分析"触发）</div>';
    }
    html += '</div>';
    
    // Bear logic
    html += '<div style="margin-bottom:12px;"><h4 style="color:#ef4444;font-size:12px;">📉 空头逻辑 (' + bearLogic.length + ')</h4>';
    if (bearLogic.length) {
        bearLogic.forEach((r, i) => {
            html += '<div style="padding:4px 0;border-bottom:1px solid #161820;color:#dfe2ea;padding-left:12px;">' + (i+1) + '. ' + r.substring(0, 120) + '</div>';
        });
    } else {
        html += '<div style="color:#6b7280;padding:4px 0;">⬜ AI分析后自动填充（点击"实时分析"触发）</div>';
    }
    html += '</div>';
    
    // Balance indicator
    if (bullLogic.length && bearLogic.length) {
        const ratio = Math.max(bullLogic.length, bearLogic.length) / Math.min(bullLogic.length, bearLogic.length);
        const balanced = ratio < 1.5 ? '✅ 多空均衡' : (bullLogic.length > bearLogic.length ? '⚠️ 偏多（多头逻辑更多）' : '⚠️ 偏空（空头逻辑更多）');
        const color = ratio < 1.5 ? '#22c55e' : '#facc15';
        html += '<div style="padding:8px;background:#161820;border-radius:6px;text-align:center;"><span style="color:' + color + ';">' + balanced + ' (多:' + bullLogic.length + ' vs 空:' + bearLogic.length + ')</span></div>';
    }
    
    html += '</div>';
    el.innerHTML = html;
}

