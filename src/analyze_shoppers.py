from pathlib import Path
from math import erfc, sqrt
from statistics import NormalDist
import html
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "raw" / "online_shoppers_intention.csv"
OUT = ROOT / "outputs"
TABLES = OUT / "tables"
CHARTS = OUT / "charts"
for folder in (TABLES, CHARTS):
    folder.mkdir(parents=True, exist_ok=True)


def save_svg(path, title, rows, max_value, unit="%"):
    width, height = 900, 140 + len(rows) * 78
    left, right = 225, 600
    scale = (right - left) / max_value
    chunks = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
              '<rect width="100%" height="100%" fill="white"/>',
              f'<text x="36" y="48" font-family="Arial,sans-serif" font-size="25" font-weight="bold">{html.escape(title)}</text>']
    for tick in range(0, int(max_value) + 1, 5):
        x = left + tick * scale
        chunks += [f'<line x1="{x}" y1="78" x2="{x}" y2="{height-28}" stroke="#e5e7eb"/>',
                   f'<text x="{x}" y="{height-8}" text-anchor="middle" font-family="Arial,sans-serif" font-size="13" fill="#555">{tick}{unit}</text>']
    colors = ['#3273dc', '#ee8c36', '#777777']
    for i, (label, value, note) in enumerate(rows):
        y = 95 + i * 78
        chunks += [f'<text x="36" y="{y+25}" font-family="Arial,sans-serif" font-size="16">{html.escape(label)}</text>',
                   f'<rect x="{left}" y="{y}" width="{max(1,value*scale)}" height="36" rx="5" fill="{colors[i%len(colors)]}"/>',
                   f'<text x="{left+value*scale+10}" y="{y+24}" font-family="Arial,sans-serif" font-size="15">{value:.2f}{unit}  {html.escape(note)}</text>']
    chunks.append('</svg>')
    path.write_text('\n'.join(chunks), encoding='utf-8')


def main():
    df = pd.read_csv(INPUT)
    purchase_rate = df.groupby('VisitorType')['Revenue'].agg(sessions='size', purchases='sum', rate='mean').reset_index()
    purchase_rate['rate_pct'] = (purchase_rate['rate'] * 100).round(2)
    purchase_rate.to_csv(TABLES / 'purchase_rate_by_visitor.csv', index=False, encoding='utf-8-sig')

    quality = pd.DataFrame([
        ('数据行数', len(df), '预期 12,330'), ('字段数', df.shape[1], '预期 18'),
        ('缺失值总数', int(df.isna().sum().sum()), '应为 0'),
        ('重复记录数', int(df.duplicated().sum()), '记录后评估，不自动删除'),
        ('ProductRelated 最小值', int(df['ProductRelated'].min()), '应为非负整数'),
        ('ProductRelated 最大值', int(df['ProductRelated'].max()), '观察范围')
    ], columns=['检查项目','结果','说明'])
    quality.to_csv(TABLES / 'data_quality_summary.csv', index=False, encoding='utf-8-sig')
    df.isna().sum().rename_axis('字段').reset_index(name='缺失值数').to_csv(TABLES / 'missing_values_by_field.csv', index=False, encoding='utf-8-sig')

    chosen = purchase_rate[purchase_rate['VisitorType'].isin(['New_Visitor','Returning_Visitor'])].copy()
    names = {'New_Visitor':'新访客','Returning_Visitor':'回访者'}
    rows = [(names[r.VisitorType], float(r.rate_pct), f'{int(r.purchases):,}/{int(r.sessions):,} 次购买/访问') for r in chosen.itertuples()]
    diff = float(chosen.loc[chosen.VisitorType=='New_Visitor','rate_pct'].iloc[0] - chosen.loc[chosen.VisitorType=='Returning_Visitor','rate_pct'].iloc[0])
    save_svg(CHARTS / 'purchase_rate_bar.svg', '不同访客类型的购买率', rows, 30)
    save_svg(CHARTS / 'purchase_rate_difference.svg', '购买率差值（新访客 − 回访者）', [('差值', diff, '百分点')], 15, unit='')

    visitor_counts = df['VisitorType'].value_counts()
    save_svg(CHARTS / 'visitor_sessions.svg', '不同访客类型的访问会话数', [(names.get(k,k), float(v), f'{int(v):,} 次') for k,v in visitor_counts.items()], max(100, int(visitor_counts.max()/1000)*1000), unit='')
    print(f'Input: {INPUT}')
    print(f'Shape: {df.shape}; missing: {int(df.isna().sum().sum())}; duplicates: {int(df.duplicated().sum())}')
    print(f'Purchase rate difference (New_Visitor - Returning_Visitor): {diff:.2f} percentage points')
    print(f'Tables: {TABLES}')
    print(f'Charts (SVG; earlier PNG files retained): {CHARTS}')



# Stage 2: confidence intervals, test, and product-page groups.
Z = NormalDist().inv_cdf(0.975)
GROUPS = ['New_Visitor', 'Returning_Visitor']

def wilson(x, n):
    p = x / n
    den = 1 + Z*Z/n
    mid = (p + Z*Z/(2*n))/den
    half = Z*sqrt(p*(1-p)/n + Z*Z/(4*n*n))/den
    return mid-half, mid+half

def newcombe(a, b):
    x1,n1 = a
    x2,n2 = b
    p1,p2 = x1/n1,x2/n2
    l1,u1 = wilson(x1,n1)
    l2,u2 = wilson(x2,n2)
    d = p1-p2
    return d-sqrt((p1-l1)**2+(u2-p2)**2), d+sqrt((u1-p1)**2+(p2-l2)**2)

def summarize(df):
    s = df.groupby('VisitorType', sort=False)['Revenue'].agg(sessions='size', purchases='sum')
    return {g:(int(s.loc[g,'purchases']),int(s.loc[g,'sessions'])) for g in GROUPS}

def write_csv(name, rows):
    pd.DataFrame(rows).to_csv(TABLES/name,index=False,encoding='utf-8-sig')

def chart(name, title, items, x_max=40, zero=False):
    """Simple SVG dot and interval plot; values are in percentage points."""
    left,right=230,780
    h=130+len(items)*65
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="{h}" viewBox="0 0 1120 {h}">',
           '<rect width="100%" height="100%" fill="white"/>',
           f'<text x="35" y="38" font-size="23" font-family="Arial" font-weight="bold">{html.escape(title)}</text>']
    if zero:
        parts.append(f'<line x1="{left}" x2="{left}" y1="55" y2="{h-45}" stroke="#b91c1c" stroke-dasharray="5 4"/>')
    for tick in range(0,x_max+1,5):
        x=left+(right-left)*tick/x_max
        parts.append(f'<line x1="{x}" x2="{x}" y1="60" y2="{h-45}" stroke="#e5e7eb"/>')
        parts.append(f'<text x="{x}" y="{h-18}" text-anchor="middle" font-size="13" font-family="Arial">{tick}%</text>')
    for i,(label,val,lo,hi,note) in enumerate(items):
        y=85+i*65
        x=lambda v:left+(right-left)*v/x_max
        parts += [f'<text x="35" y="{y+5}" font-size="16" font-family="Arial">{html.escape(label)}</text>',
                  f'<line x1="{x(lo)}" x2="{x(hi)}" y1="{y}" y2="{y}" stroke="#2563eb" stroke-width="4"/>',
                  f'<circle cx="{x(val)}" cy="{y}" r="7" fill="#ea580c"/>',
                  f'<text x="{right+15}" y="{y+5}" font-size="14" font-family="Arial">{val:.2f}% {html.escape(note)}</text>']
    parts.append('</svg>')
    (CHARTS/name).write_text('\n'.join(parts),encoding='utf-8')

def stage2_main():
    df = pd.read_csv(INPUT)
    assert df.shape == (12330,18)
    assert df.isna().sum().sum() == 0
    assert set(df.VisitorType.unique()) == set(GROUPS+['Other'])
    assert set(df.Revenue.unique()) == {False,True}
    assert (df.ProductRelated >= 0).all() and (df.ProductRelated%1 == 0).all()
    counts = summarize(df)
    a,b = counts[GROUPS[0]],counts[GROUPS[1]]
    p1,p2 = a[0]/a[1],b[0]/b[1]
    diff = p1-p2
    dl,du = newcombe(a,b)
    rows=[]
    for g in GROUPS:
        x,n = counts[g]
        lo,hi = wilson(x,n)
        rows.append(dict(group=g,sessions=n,purchases=x,rate=x/n,ci95_low=lo,ci95_high=hi))
    write_csv('stage2_confidence_intervals.csv',rows)
    chart('stage2_purchase_rate_ci.svg','新访客与回访者购买率及95%置信区间',[
        ('新访客',p1*100,rows[0]['ci95_low']*100,rows[0]['ci95_high']*100,f'访问会话数={a[1]}'),
        ('回访者',p2*100,rows[1]['ci95_low']*100,rows[1]['ci95_high']*100,f'访问会话数={b[1]}')])
    pooled=(a[0]+b[0])/(a[1]+b[1])
    se=sqrt(pooled*(1-pooled)*(1/a[1]+1/b[1]))
    z=diff/se
    pval=erfc(abs(z)/sqrt(2))
    write_csv('stage2_test.csv',[dict(test='two-sided pooled two-proportion z',difference=diff,
        ci95_low=dl,ci95_high=du,pooled_rate=pooled,standard_error=se,z=z,p_value=pval,
        reject_at_005=pval<0.05)])
    chart('stage2_difference_ci.svg','新访客与回访者购买率差值及95%置信区间',[
        ('新访客 − 回访者',diff*100,dl*100,du*100,'个百分点')],x_max=20,zero=True)
    chosen=df[df.VisitorType.isin(GROUPS)].copy()
    q=chosen.ProductRelated.quantile([.25,.5,.75]).astype(int).tolist()
    assert len(set(q))==3
    edges=[-1]+q+[float('inf')]
    labels=[f'0-{q[0]}',f'{q[0]+1}-{q[1]}',f'{q[1]+1}-{q[2]}',f'{q[2]+1}+']
    chosen['product_group']=pd.cut(chosen.ProductRelated,bins=edges,labels=labels)
    tab=chosen.groupby(['product_group','VisitorType'],observed=True)['Revenue'].agg(sessions='size',purchases='sum').reset_index()
    tab['rate']=tab.purchases/tab.sessions
    tab['nonpurchases'] = tab.sessions - tab.purchases
    tab['sparse_check'] = (tab.sessions < 30) | (tab.purchases < 5) | (tab.nonpurchases < 5)
    cell_intervals = [wilson(int(r.purchases), int(r.sessions)) for r in tab.itertuples()]
    tab['ci95_low'] = [lo for lo, _ in cell_intervals]
    tab['ci95_high'] = [hi for _, hi in cell_intervals]
    tab.to_csv(TABLES/'stage2_productrelated_groups.csv',index=False,encoding='utf-8-sig')
    group_items = []
    for label in labels:
        for group in GROUPS:
            row = tab[(tab.product_group == label) & (tab.VisitorType == group)].iloc[0]
            visitor_name = '新访客' if group == GROUPS[0] else '回访者'
            group_items.append((f'{label}页 / {visitor_name}', float(row.rate*100),
                float(row.ci95_low*100), float(row.ci95_high*100),
                f'购买/访问={int(row.purchases)}/{int(row.sessions)}'))
    chart('stage2_productrelated.svg','不同产品相关页面浏览量下的购买率（Wilson 95%区间）',
          group_items,x_max=45)
    wide=tab.pivot(index='product_group',columns='VisitorType',values=['sessions','purchases','rate']).reindex(labels)
    weights=chosen.product_group.value_counts().reindex(labels)/len(chosen)
    standardized={g:float((wide['rate'][g]*weights).sum()) for g in GROUPS}
    write_csv('stage2_standardized.csv',[dict(group=g,raw_rate=counts[g][0]/counts[g][1],
        standardized_rate=standardized[g]) for g in GROUPS])
    chart('stage2_raw_vs_standardized.svg','原始差值与标准化差值比较',[
        ('原始购买率差值',diff*100,diff*100,diff*100,'个百分点'),
        ('标准化购买率差值',(standardized[GROUPS[0]]-standardized[GROUPS[1]])*100,
         (standardized[GROUPS[0]]-standardized[GROUPS[1]])*100,
         (standardized[GROUPS[0]]-standardized[GROUPS[1]])*100,'个百分点')],x_max=20)
    write_csv('stage2_group_weights.csv',[dict(product_group=k,weight=float(v)) for k,v in weights.items()])
    de=df.drop_duplicates()
    dc=summarize(de)
    write_csv('stage2_duplicate_sensitivity.csv',[dict(dataset=tag,group=g,sessions=c[g][1],purchases=c[g][0],rate=c[g][0]/c[g][1])
        for tag,c in [('all',counts),('deduplicated_sensitivity_only',dc)] for g in GROUPS])
    print('Data:',len(df),'rows;',df.duplicated().sum(),'identical rows (kept in main analysis)')
    print('Counts:',counts,'Rates:',p1,p2,'Difference:',diff)
    print('Wilson intervals:',[(r['group'],r['ci95_low'],r['ci95_high']) for r in rows])
    print('Newcombe difference CI:',dl,du)
    print('Z:',z,'P:',pval)
    print('ProductRelated common quartile boundaries:',q)
    print(tab.to_string(index=False))
    print('Standardized rates:',standardized,'Difference:',standardized[GROUPS[0]]-standardized[GROUPS[1]])
    print('Deduplicated sensitivity:',dc)



if __name__ == '__main__':
    main()
    stage2_main()
