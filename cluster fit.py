import pandas as pd
from collections import Counter

src = 'supplements_data.xlsx'
df = pd.read_excel(src)

# Normalize columns
cols = {c: c.strip().replace('\n',' ').replace(' ', '_') for c in df.columns}
df.rename(columns=cols, inplace=True)

# Parse date
df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

# Define pseudo-customer id from demographics and location
key_cols = ['Location','Gender','Age']
df['customer_id'] = df[key_cols].astype(str).agg('_'.join, axis=1)

# Ensure numeric
for c in ['Revenue','Units_Sold','Price']:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors='coerce')

# Category mapping for shares
protein_mask = df['Category'].fillna('').str.strip().str.lower().eq('protein')
vitamin_mask = df['Category'].fillna('').str.strip().str.lower().eq('vitamin')

# Aggregate revenue per group
grp = df.groupby('customer_id', as_index=False)

rev_total = grp['Revenue'].sum().rename(columns={'Revenue':'total_spent'})
rev_protein = df.assign(x=protein_mask.astype(int)*df['Revenue']).groupby('customer_id', as_index=False)['x'].sum().rename(columns={'x':'rev_protein'})
rev_vitamins = df.assign(x=vitamin_mask.astype(int)*df['Revenue']).groupby('customer_id', as_index=False)['x'].sum().rename(columns={'x':'rev_vitamins'})

# Preferred channel by revenue
rev_by_platform = df.groupby(['customer_id','Platform'], as_index=False)['Revenue'].sum()
preferred = rev_by_platform.sort_values(['customer_id','Revenue'], ascending=[True, False]).drop_duplicates('customer_id')
preferred = preferred[['customer_id','Platform']].rename(columns={'Platform':'preferred_channel'})

# Purchase frequency = distinct order days for this pseudo-customer
freq = df.dropna(subset=['Date']).groupby('customer_id', as_index=False)['Date'].nunique().rename(columns={'Date':'purchase_freq'})

# Merge features
feat = rev_total.merge(rev_protein, on='customer_id', how='left')\
                .merge(rev_vitamins, on='customer_id', how='left')\
                .merge(preferred, on='customer_id', how='left')\
                .merge(freq, on='customer_id', how='left')

feat[['rev_protein','rev_vitamins']] = feat[['rev_protein','rev_vitamins']].fillna(0.0)
feat['purchase_freq'] = feat['purchase_freq'].fillna(0).astype(int)

# Compute shares
feat['pct_protein'] = (feat['rev_protein'] / feat['total_spent']).fillna(0.0).clip(0,1)
feat['pct_vitamins'] = (feat['rev_vitamins'] / feat['total_spent']).fillna(0.0).clip(0,1)
feat['pct_accessories'] = (1.0 - feat['pct_protein'] - feat['pct_vitamins']).clip(lower=0.0)

# Final ordering of columns
final_cols = ['customer_id','total_spent','purchase_freq','pct_protein','pct_vitamins','pct_accessories','preferred_channel']
feat = feat[final_cols].sort_values('total_spent', ascending=False)

# Save CSV
out = 'customers_features.csv'
feat.to_csv(out, index=False)

print('ROWS', len(feat), 'COLUMNS', list(feat.columns))