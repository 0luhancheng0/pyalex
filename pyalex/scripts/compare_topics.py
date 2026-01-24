import json
import typer
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from typing import List, Dict, Any

app = typer.Typer(help="Compare topic distributions between entities.")

@app.command()
def main(
    input_file: str = typer.Option(..., "--input-file", "-i", help="Path to aggregated JSONL file (can contain any number of entities)."),
    output_file: str = typer.Option("topic_comparison.html", "--output-file", "-o", help="Path to save the HTML comparison."),
    log_scale: bool = typer.Option(True, "--log-scale", help="Use log scale for axes (better for visualizing long-tail distributions)."),
    min_share: float = typer.Option(0.001, "--min-share", help="Minimum percentage share (0-100) in at least one entity to keep a topic."),
):
    """
    Generates an interactive scatter plot comparing topic prevalence between groups.
    
    The resulting HTML will contain dropdown menus to select which entities to map to the X and Y axes.
    """
    entities = []
    
    print(f"Reading {input_file}...")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    if line.strip():
                        entities.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        print(f"Error: File {input_file} not found.")
        raise typer.Exit(code=1)

    if len(entities) < 2:
        print(f"Error: Input file must contain at least 2 entities. Found {len(entities)}.")
        raise typer.Exit(code=1)

    print(f"Found {len(entities)} entities: {[e.get('display_name') for e in entities]}")
    print("Processing topic distributions...")

    # 1. Process all entities into a unified structure
    # schema: { topic_id: { 'meta': ..., 'stats': { entity_name: { 'count': ..., 'share': ... } } } }
    all_topics: Dict[str, Dict[str, Any]] = {}
    entity_names = []

    for entity in entities:
        e_name = entity.get('display_name', 'Unknown')
        entity_names.append(e_name)
        
        topics = entity.get('topics', [])
        total_count = sum(t.get('count', 0) for t in topics)
        
        for t in topics:
            t_id = t.get('id')
            if not t_id: continue
            
            if t_id not in all_topics:
                all_topics[t_id] = {
                    'meta': {
                        'name': t.get('display_name', 'Unknown'),
                        'domain': t.get('domain', {}).get('display_name', 'Unknown'),
                        'field': t.get('field', {}).get('display_name', 'Unknown')
                    },
                    'stats': {}
                }
            
            count = t.get('count', 0)
            share_pct = (count / total_count * 100) if total_count > 0 else 0
            
            all_topics[t_id]['stats'][e_name] = {
                'count': count,
                'share': share_pct
            }

    # 2. Convert to DataFrame
    print(f"Aggregating data for {len(all_topics)} unique topics...")
    rows = []
    
    for t_id, data in all_topics.items():
        row = {
            'Topic': data['meta']['name'],
            'Domain': data['meta']['domain'],
            'Field': data['meta']['field'],
        }
        
        # Check max share to filter noise
        max_share = 0
        
        # Fill stats for all entities (default to 0 if missing)
        for name in entity_names:
            stats = data['stats'].get(name, {'count': 0, 'share': 0})
            row[f'Share_{name}'] = stats['share']
            row[f'Count_{name}'] = stats['count']
            if stats['share'] > max_share:
                max_share = stats['share']
        
        if max_share >= min_share:
            rows.append(row)

    df = pd.DataFrame(rows)
    print(f"Kept {len(df)} topics after filtering (max_share >= {min_share}%).")

    if df.empty:
        print("No topics met the criteria.")
        return

    # 3. Create Plotly Figure
    # Initial view: First two entities
    x_name = entity_names[0]
    y_name = entity_names[1]

    # Prepare Hover Text
    # We construct a single hover string per topic containing all entity stats
    # This avoids needing to update customdata dynamically via dropdowns
    hover_texts = []
    for _, row in df.iterrows():
        txt = f"<b>{row['Topic']}</b><br>{row['Domain']} / {row['Field']}<br><br>"
        for name in entity_names:
            txt += f"<b>{name}</b>: {row[f'Share_{name}']:.3f}% ({int(row[f'Count_{name}'])} works)<br>"
        hover_texts.append(txt)

    # Assign colors to domains consistently
    domains = df['Domain'].unique()
    color_map = {d: i for i, d in enumerate(domains)}
    colors = df['Domain'].map(color_map)

    fig = go.Figure()

    # Add Scatter Trace
    fig.add_trace(go.Scatter(
        x=df[f'Share_{x_name}'],
        y=df[f'Share_{y_name}'],
        mode='markers',
        text=hover_texts,
        hoverinfo='text',
        marker=dict(
            color=colors,
            colorscale='Viridis', # Or any qualitative set if mapped manually, but continuous works for now or use separate traces
            showscale=False,
            opacity=0.7,
            size=8
        ),
        name="Topics"
    ))
    
    # Improve coloring: actually better to use discrete colors by Domain if possible
    # But go.Scatter with single trace handles colors via array. 
    # To get a legend for domains, we'd need separate traces, which complicates the dropdown logic significantly.
    # We will stick to a single trace with colored markers for simplicity in dropdown logic.
    
    # 4. Add Diagonal Line
    # Calculate global range for fixed diagonal
    all_shares = []
    for name in entity_names:
        all_shares.extend(df[f'Share_{name}'])
    
    min_val = min(s for s in all_shares if s > 0) if log_scale else 0
    max_val = max(all_shares) * 1.1 # 10% buffer

    fig.add_shape(
        type="line",
        x0=min_val, y0=min_val,
        x1=max_val, y1=max_val,
        line=dict(color="rgba(0,0,0,0.3)", dash="dash"),
    )

    fig.add_annotation(
        x=np.log10(max_val) if log_scale else max_val, 
        y=np.log10(max_val) if log_scale else max_val,
        text="Equal Share",
        showarrow=False,
        yshift=10,
        xshift=-10
    )

    # 5. Create Dropdowns
    # Dropdown 1: X Axis
    x_buttons = []
    for name in entity_names:
        x_buttons.append(dict(
            method='update',
            label=name,
            args=[{'x': [df[f'Share_{name}']]}, # Update data
                  {'xaxis.title': f"{name} Share (%)"}] # Update layout
        ))

    # Dropdown 2: Y Axis
    y_buttons = []
    for name in entity_names:
        y_buttons.append(dict(
            method='update',
            label=name,
            args=[{'y': [df[f'Share_{name}']]}, 
                  {'yaxis.title': f"{name} Share (%)"}]
        ))

    fig.update_layout(
        updatemenus=[
            dict(
                buttons=x_buttons,
                direction="down",
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.1,
                xanchor="left",
                y=1.15,
                yanchor="top",
                active=0 # Default to first entity
            ),
            dict(
                buttons=y_buttons,
                direction="down",
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.3, # Offset to place next to first dropdown
                xanchor="left",
                y=1.15,
                yanchor="top",
                active=1 # Default to second entity
            ),
        ],
        annotations=[
            dict(text="X-Axis:", x=0.1, y=1.2, xref="paper", yref="paper", showarrow=False, xanchor="left", yanchor="bottom"),
            dict(text="Y-Axis:", x=0.3, y=1.2, xref="paper", yref="paper", showarrow=False, xanchor="left", yanchor="bottom")
        ]
    )

    # 6. Final Layout Polish
    fig.update_layout(
        title="Interactive Topic Comparison",
        xaxis_title=f"{x_name} Share (%)",
        yaxis_title=f"{y_name} Share (%)",
        xaxis_type="log" if log_scale else "linear",
        yaxis_type="log" if log_scale else "linear",
        height=800,
        hovermode='closest'
    )

    fig.write_html(output_file)
    print(f"Visualization saved to {output_file}")

if __name__ == "__main__":
    app()
