from pathlib import Path
import csv
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
    print(f'Charts (SVG source and PNG exports): {CHARTS}')

if __name__ == '__main__':
    main()
