import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import glob
import os
import re

# Automatically find all JSON files with year in filename
json_files = glob.glob("*.json")
year_file_map = {}
year_pattern = re.compile(r"(\d{4})\.json$")
for fname in json_files:
    match = year_pattern.match(os.path.basename(fname))
    if match:
        year = int(match.group(1))
        year_file_map[year] = fname

years = sorted(year_file_map.keys())

dfs = []
for year in years:
    df = pd.read_json(year_file_map[year])
    df['year'] = year
    dfs.append(df)

# Merge all DataFrames on 'key'
merged = dfs[0][['key', 'key_display_name', 'count']].rename(columns={'count': f'count_{years[0]}'})
for i, year in enumerate(years[1:], 1):
    merged = pd.merge(
        merged,
        dfs[i][['key', 'count']].rename(columns={'count': f'count_{year}'}),
        on='key',
        how='inner'
    )

# Calculate differences between consecutive years
for i in range(len(years) - 1):
    y1, y2 = years[i], years[i+1]
    merged[f'count_diff_{y1}_{y2}'] = merged[f'count_{y2}'] - merged[f'count_{y1}']

# Constants
TOP_N_TOPICS = 10

# Sort by largest change between the last two years in the range
if len(years) >= 2:
    last_two_years = (years[-2], years[-1])
    diff_col = f'count_diff_{last_two_years[0]}_{last_two_years[1]}'
    merged_sorted = merged.sort_values(by=diff_col, ascending=False)
    # Display the comparison for the last two years
    print(merged_sorted[['key_display_name', f'count_{last_two_years[0]}', f'count_{last_two_years[1]}', diff_col]])
else:
    merged_sorted = merged

# Select top N topics by total count across all years
merged['total'] = merged[[f'count_{y}' for y in years]].sum(axis=1)
top_topics = merged.sort_values('total', ascending=False).head(TOP_N_TOPICS)

# Prepare data for line plot (proportions)
plot_df = top_topics.melt(
    id_vars=['key_display_name'],
    value_vars=[f'count_{y}' for y in years],
    var_name='year',
    value_name='count'
)
plot_df['year'] = plot_df['year'].str.extract(r'(\d+)').astype(int)

# Normalize counts to proportions per year
year_totals = plot_df.groupby('year')['count'].transform('sum')
plot_df['proportion'] = plot_df['count'] / year_totals

# Prepare data for stacked area plot (proportions)
pivot_df = plot_df.pivot(index='year', columns='key_display_name', values='proportion').fillna(0)
years_sorted = sorted(pivot_df.index)
topics_sorted = list(pivot_df.columns)

plt.figure(figsize=(14, 8))
plt.stackplot(
    years_sorted,
    [pivot_df[topic] for topic in topics_sorted],
    labels=topics_sorted
)

plt.xlabel('Year')
plt.ylabel('Proportion')
plt.title(f'Topic Evolution (Top {TOP_N_TOPICS} Topics, Stacked Proportion)')
plt.legend(title='Topic', bbox_to_anchor=(1.05, 1), loc='upper left')
plt.tight_layout()
plt.show()

