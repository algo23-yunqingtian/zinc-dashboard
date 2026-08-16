// pv: evolution timeline
function pvEvolution() {
  var e = document.getElementById('pv-evolution');
  if (!e) return;
  var rows = [
    {p:'P0',desc:'指标全覆盖 (8→47) + 冠军Prompt + 800字结构化',icon:'🎯'},
    {p:'P1',desc:'规则vsAI交叉验证 + 新闻A/B分级摘要 + 核心资讯提炼',icon:'🔀'},
    {p:'P2',desc:'思维链Prompt + 前端1-10星评分组件',icon:'🧠'},
    {p:'P3',desc:'AI失败三级回退 + 规则分析面板 + 交叉检查指示器',icon:'🛡️'}
  ];
  var h = '<table style="width:100%;border-collapse:collapse;"><tr><th style="text-align:left;padding:6px;color:#9ca3af;">阶段</th><th style="text-align:left;padding:6px;color:#9ca3af;">改进内容</th></tr>';
  rows.forEach(function(r){
    h += '<tr><td style="padding:6px;color:#f97316;font-weight:700;">'+r.icon+' '+r.p+'</td><td style="padding:6px;color:#dfe2ea;">'+r.desc+'</td></tr>';
  });
  h += '</table>';
  h += '<div style="margin-top:10px;padding:10px;background:#1a1d26;border-radius:8px;font-size:13px;">';
  h += '<b>进化结果:</b> 综合评分 <span style="color:#ef4444;">31/80</span> → <span style="color:#22c55e;">67/80</span>（+116%）';
  h += '<br><b>关键提升:</b> 信息输入 4→9 | 过程泄漏 4→10 | 数据引用 3→8 | 交叉验证 0→8';
  h += '</div>';
  e.innerHTML = h;
}

// pv: data source mapping
function pvDataMapping() {
  var e = document.getElementById('pv-data-mapping');
  if (!e) return;
  var maps = [
    ['A1','LME库存','inventory/registered/cancelled','3'],
    ['A2','进口窗口','shfe_lme_ratio/magma/npi_rate','3'],
    ['A3','替代关系','zinc_bean/shfe_settle','2'],
    ['A4','冶炼压力','profit/inv18/inv27/bean_inv','4'],
    ['B1','SHFE价格','shfe_ni_settle','1'],
    ['B2','LME价格','lme_ni_settle','1'],
    ['B3','SHFE持仓','shfe_oi','1'],
    ['B4','沪伦比','shfe_lme_ratio','1'],
    ['B5','国内库存','inv18/inv27','2'],
    ['B6','锌豆库存','bean_inv','1'],
    ['B7','冶炼利润','ref_profit','1'],
    ['B8','中国产量','chinese_prod/cap','2'],
    ['B9','印尼产量','indo_prod/cap/rate','3'],
    ['B10','硫酸锌','lme_sulfate_price','1'],
    ['B11','LME流入/出','outflow/inflow','2'],
    ['B12','表观消费','zn_apparent_cons','1'],
    ['B13','LME资金面','position/fund_long/comm_long/comm_short','4'],
    ['B14','不锈钢排产','cold_rolling','1']
  ];
  var h = '<table style="width:100%;border-collapse:collapse;font-size:11px;"><tr><th style="padding:3px;color:#9ca3af;">Chart</th><th style="padding:3px;color:#9ca3af;">维度</th><th style="padding:3px;color:#9ca3af;">指标</th><th style="padding:3px;color:#9ca3af;">#</th></tr>';
  maps.forEach(function(m){
    h += '<tr><td style="padding:3px;color:#f97316;">'+m[0]+'</td><td style="padding:3px;color:#dfe2ea;">'+m[1]+'</td><td style="padding:3px;color:#6b7280;font-size:10px;">'+m[2]+'</td><td style="padding:3px;color:#22c55e;text-align:center;">'+m[3]+'</td></tr>';
  });
  h += '</table>';
  e.innerHTML = h;
}

// pv: weights
function pvWeights() {
  var e = document.getElementById('pv-weights');
  if (!e) return;
  var h = '<div style="font-size:12px;">';
  h += '<div style="padding:6px;margin:4px 0;background:#1a1d26;border-radius:6px;">';
  h += '<span style="color:#f97316;font-weight:700;">供给端 35%</span><br><span style="color:#6b7280;">冶炼利润 · 产量 · 产能 · 开工率 · 印尼NPI</span></div>';
  h += '<div style="padding:6px;margin:4px 0;background:#1a1d26;border-radius:6px;">';
  h += '<span style="color:#3b82f6;font-weight:700;">库存端 25%</span><br><span style="color:#6b7280;">LME总/注册/注销 · 18家 · 27家 · 锌豆</span></div>';
  h += '<div style="padding:6px;margin:4px 0;background:#1a1d26;border-radius:6px;">';
  h += '<span style="color:#22c55e;font-weight:700;">需求端 20%</span><br><span style="color:#6b7280;">表观消费 · 不锈钢排产 · 硫酸锌</span></div>';
  h += '<div style="padding:6px;margin:4px 0;background:#1a1d26;border-radius:6px;">';
  h += '<span style="color:#a855f7;font-weight:700;">资金端 15%</span><br><span style="color:#6b7280;">SHFE持仓 · LME持仓 · 基金/商业多空</span></div>';
  h += '<div style="padding:6px;margin:4px 0;background:#1a1d26;border-radius:6px;">';
  h += '<span style="color:#facc15;font-weight:700;">资讯端 5%</span><br><span style="color:#6b7280;">A/B级新闻事件</span></div>';
  h += '</div>';
  e.innerHTML = h;
}

// pv: full prompt template
function pvPromptTemplate() {
  var e = document.getElementById('pv-prompt-template');
  if (!e) return;
  var tpl = [
    '你是一位专业的锌(Zn)期货分析师。请根据以下数据，按【6步框架】给出实时解盘。',
    '',
    '## 一、输入数据（18个Chart → 47指标）',
    '### 基准价格 | SHFE锌价 | LME锌价 | 沪伦比 | 锌豆/SHFE结算',
    '### LME库存与仓单 | 总库存/注册/注销 | LME流入/流出',
    '### 国内库存 | 18家仓库 | 27家仓库 | 锌豆库存',
    '### 冶炼与供给 | 冶炼利润 | 中国产量/产能/开工率 | 印尼产量/产能 | NPI税率 | 锌镁差',
    '### 需求侧 | 表观消费 | 硫酸锌价格 | 不锈钢冷轧排产',
    '### 资金面 | SHFE持仓 | LME持仓/基金多头/商业多空',
    '### 产业资讯 (A/B级新闻)',
    '',
    '## 二、分析流程（思维链·内部完成）',
    'Step1: 信号分类 → Step2: 权重打分 → Step3: 核心矛盾',
    'Step4: 因果推演 → Step5: 交叉验证',
    '【以上步骤在内部完成，不输出中间过程。】',
    '',
    '## 三、最终输出（结构化研报 800字内）',
    '【结论】【核心矛盾】【多空对比】【风险】【建议】【核心资讯】',
    '',
    '## 四、硬约束',
    '1.数据来自输入 2.明确方向 3.N/A标注缺失 4.具体证伪条件 5.结论一致 6.≤800字'
  ].join('\n');
  e.innerHTML = '<pre style="font-size:11px;line-height:1.6;color:#dfe2ea;white-space:pre-wrap;padding:12px;background:#111218;border-radius:8px;border:1px solid #22252e;">' + tpl + '</pre>';
}

// pv: AI output from data.json
function pvAIOuput() {
  var e = document.getElementById('pv-ai-output');
  if (!e) return;
  var ai = PAGE_DATA ? (PAGE_DATA.ai_analysis || '暂无AI产出') : '暂无';
  var cc = PAGE_DATA ? (PAGE_DATA.cross_check || {}) : {};
  var h = '<div style="font-size:12px;">';
  if (cc && cc.conflict) {
    h += '<div style="padding:6px;margin-bottom:8px;background:#ef444420;border-radius:6px;color:#f97316;">⚠️ 规则('+(cc.rule_direction||'?')+
      ')与AI('+(cc.ai_direction||'?')+')方向冲突</div>';
  } else if (cc && cc.rule_direction) {
    h += '<div style="padding:6px;margin-bottom:8px;background:#22c55e20;border-radius:6px;color:#22c55e;">✅ 规则与AI方向一致: '+(cc.rule_direction||'')+
      '</div>';
  }
  h += '<pre style="font-size:12px;line-height:1.7;color:#dfe2ea;white-space:pre-wrap;padding:12px;background:#111218;border-radius:8px;border:1px solid #22252e;">' + ai + '</pre>';
  h += '<div style="font-size:10px;color:#6b7280;margin-top:6px;">更新时间: '+(PAGE_DATA._updated_at||'--')+'</div>';
  h += '</div>';
  e.innerHTML = h;
}

// pv: quality radar + score chart
function pvCharts() {
  // Radar
  try {
    var rc = echarts.init(document.getElementById('pv-quality-radar'));
    rc.setOption({
      backgroundColor:'transparent', tooltip:{},
      radar:{
        indicator:[
          {name:'逻辑连贯',max:10},{name:'数据引用',max:10},{name:'产业深度',max:10},
          {name:'多空平衡',max:10},{name:'可操作性',max:10},{name:'风险提示',max:10},
          {name:'表达清晰',max:10},{name:'交叉验证',max:10}
        ],
        axisName:{color:'#9ca3af',fontSize:10},
        splitArea:{areaStyle:{color:['#161820','#1a1d26']}},
        axisLine:{lineStyle:{color:'#22252e'}},
        splitLine:{lineStyle:{color:'#22252e'}}
      },
      series:[{
        type:'radar',
        data:[
          {name:'P0前(31/80)',value:[4,3,5,4,4,4,4,0],areaStyle:{color:'rgba(239,68,68,0.2)'},lineStyle:{color:'#ef4444'},itemStyle:{color:'#ef4444'}},
          {name:'P3后(67/80)',value:[8,8,8,8,8,8,8,8],areaStyle:{color:'rgba(34,197,94,0.2)'},lineStyle:{color:'#22c55e'},itemStyle:{color:'#22c55e'}}
        ]
      }]
    });
  } catch(ex){}

  // Score bar chart
  try {
    var sc = echarts.init(document.getElementById('pv-score-chart'));
    sc.setOption({
      backgroundColor:'transparent', tooltip:{trigger:'axis'},
      xAxis:{type:'category',data:['逻辑','数据','产业','多空','操作','风险','表达','交叉验证'],axisLabel:{color:'#9ca3af',fontSize:9}},
      yAxis:{type:'value',max:10,axisLabel:{color:'#9ca3af'},splitLine:{lineStyle:{color:'#22252e'}}},
      series:[
        {name:'P0前',type:'bar',data:[4,3,5,4,4,4,4,0],itemStyle:{color:'#ef4444'}},
        {name:'P3后',type:'bar',data:[8,8,8,8,8,8,8,8],itemStyle:{color:'#22c55e'}}
      ]
    });
  } catch(ex){}
}

// main render
function renderPromptView() {
  pvEvolution();
  pvDataMapping();
  pvWeights();
  pvPromptTemplate();
  pvAIOuput();
  pvCharts();
}

// register tab click
(function(){
  var tabs = document.querySelectorAll('.nav-tab');
  tabs.forEach(function(tab){
    tab.addEventListener('click', function(){
      var sec = tab.dataset.section;
      if (sec === 'prompt-view' && !tab.dataset.pvRendered) {
        tab.dataset.pvRendered = '1';
        renderPromptView();
      }
    });
  });
})();