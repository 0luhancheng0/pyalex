import json
from pathlib import Path
from typing import List, Dict, Any, Optional

import typer
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

def create_visualize_topics_command(app: typer.Typer):
    @app.command(name="visualize-topics", rich_help_panel="Utility Commands")
    def visualize_topics(
        inputs: List[str] = typer.Option(
            ...,
            "--input",
            "-i",
            help="Input file in format 'Label:Path' or just 'Path' (label will be inferred from filename). Can be used multiple times."
        ),
        output_dir: Path = typer.Option(
            ".",
            "--output-dir",
            "-o",
            help="Directory to save the generated artifacts (aggregated JSONL, comparison HTML, treemap HTML)."
        ),
        log_scale: bool = typer.Option(
            True,
            "--log-scale",
            help="Use log scale for axes in comparison plot (better for visualizing long-tail distributions)."
        ),
        min_share: float = typer.Option(
            0.001,
            "--min-share",
            help="Minimum percentage share (0-100) in at least one entity to keep a topic for comparison."
        ),
    ):
        """
        Aggregate, compare, and visualize topics from multiple JSONL files.

        This command performs three main steps:
        1. **Aggregate**: Reads multiple input JSONL files (each representing a group/entity like a country or institution),
           and aggregates topic counts. It creates an `aggregated_topics.jsonl` file.
        2. **Compare**: Generates an interactive scatter plot (`topic_comparison.html`) comparing topic prevalence between the groups.
        3. **Visualize**: Generates a treemap (`topics_treemap.html`) for each group to show their topic hierarchy.
        """
        
        # Ensure output directory exists
        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)

        aggregated_data = {}
        
        # --- Step 1: Aggregation ---
        print("Step 1: Aggregating topics...")
        for input_str in inputs:
            if ":" in input_str:
                label, path_str = input_str.split(":", 1)
            else:
                path_str = input_str
                label = Path(path_str).stem
                
            file_path = Path(path_str)
            if not file_path.exists():
                print(f"Error: File {file_path} not found.")
                raise typer.Exit(code=1)
                
            print(f"Processing group '{label}' from {file_path}...")
            
            # Initialize storage for this group
            # structure: { topic_id: { count: total_count, meta: topic_object } }
            group_topics = {}
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            item = json.loads(line)
                            topics = item.get('topics', [])
                            
                            for topic in topics:
                                t_id = topic.get('id')
                                if not t_id:
                                    continue
                                    
                                count = topic.get('count', 0)
                                if count == 0:
                                     # sometimes count isn't present, or we just count occurrences
                                     count = 1

                                if t_id not in group_topics:
                                    # Store metadata from the first occurrence
                                    meta = topic.copy()
                                    meta.pop('count', None)
                                    meta.pop('score', None)
                                    group_topics[t_id] = {
                                        'count': 0,
                                        'meta': meta
                                    }
                                
                                group_topics[t_id]['count'] += count
                                
                        except json.JSONDecodeError:
                            print(f"Warning: Skipping invalid JSON line in {file_path}")
                            continue
                            
                aggregated_data[label] = group_topics
                
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
                raise typer.Exit(code=1)

        # Write aggregated output
        aggregated_output_path = output_dir / "aggregated_topics.jsonl"
        print(f"Writing aggregated results to {aggregated_output_path}...")
        
        final_entities = []
        
        try:
            with open(aggregated_output_path, 'w', encoding='utf-8') as f:
                for label, topics_map in aggregated_data.items():
                    # Reconstruct the topics list for this group
                    topics_list = []
                    for t_data in topics_map.values():
                        topic_obj = t_data['meta']
                        topic_obj['count'] = t_data['count']
                        topics_list.append(topic_obj)
                    
                    # Create the group entity
                    group_entity = {
                        "display_name": label,
                        "topics": topics_list
                    }
                    
                    # Keep in memory for next steps
                    final_entities.append(group_entity)
                    
                    f.write(json.dumps(group_entity) + "\n")
                    
        except Exception as e:
            print(f"Error writing aggregated output: {e}")
            raise typer.Exit(code=1)

        if not final_entities:
            print("No data aggregated. Exiting.")
            return

        # --- Step 2: Compare Topics (Scatter Plot) ---
        if len(final_entities) >= 2:
            print("\nStep 2: Generating comparison plot...")
            _generate_comparison_plot(final_entities, output_dir / "topic_comparison.html", log_scale, min_share)
        else:
            print("\nStep 2: Skipping comparison plot (need at least 2 entities).")

        # --- Step 3: Visualize Topics (Treemap) ---
        print("\nStep 3: Generating treemaps...")
        _generate_treemap(final_entities, output_dir / "topics_treemap.html")
        
        print("\nDone!")


def _generate_comparison_plot(entities: List[Dict], output_file: Path, log_scale: bool, min_share: float):
    entity_names = [e.get('display_name', 'Unknown') for e in entities]
    
    # 1. Process all entities into a unified structure
    all_topics: Dict[str, Dict[str, Any]] = {}

    for entity in entities:
        e_name = entity.get('display_name', 'Unknown')
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
    print(f"  Comparison: Kept {len(df)} topics after filtering (max_share >= {min_share}%).")

    if df.empty:
        print("  No topics met the criteria for comparison.")
        return

    # 3. Create Plotly Figure
    x_name = entity_names[0]
    y_name = entity_names[1]

    # Prepare Hover Text
    hover_texts = []
    for _, row in df.iterrows():
        txt = f"<b>{row['Topic']}</b><br>{row['Domain']} / {row['Field']}<br><br>"
        for name in entity_names:
            txt += f"<b>{name}</b>: {row[f'Share_{name}']:.3f}% ({int(row[f'Count_{name}'])} works)<br>"
        hover_texts.append(txt)

    # Assign colors to domains
    domains = df['Domain'].unique()
    # Handle potentially NaN domains
    domains = [d for d in domains if isinstance(d, str)]
    color_map = {d: i for i, d in enumerate(domains)}
    colors = df['Domain'].map(color_map)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df[f'Share_{x_name}'],
        y=df[f'Share_{y_name}'],
        mode='markers',
        text=hover_texts,
        hoverinfo='text',
        marker=dict(
            color=colors,
            colorscale='Viridis',
            showscale=False,
            opacity=0.7,
            size=8
        ),
        name="Topics"
    ))
    
    # Add Diagonal Line
    all_shares = []
    for name in entity_names:
        all_shares.extend(df[f'Share_{name}'])
    
    # Filter out zeros for log scale calc if needed, though 0 usually handled by plotly log axis ok (it hides them)
    # but for manual range calculation:
    pos_shares = [s for s in all_shares if s > 0]
    if not pos_shares:
        min_val = 0
    else:
        min_val = min(pos_shares) if log_scale else 0
        
    max_val = max(all_shares) * 1.1 if all_shares else 1

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

    # Dropdowns
    x_buttons = []
    for name in entity_names:
        x_buttons.append(dict(
            method='update',
            label=name,
            args=[{'x': [df[f'Share_{name}']]}, 
                  {'xaxis.title': f"{name} Share (%)"}]
        ))

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
                x=0.1, xanchor="left",
                y=1.15, yanchor="top",
                active=0
            ),
            dict(
                buttons=y_buttons,
                direction="down",
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.3, xanchor="left",
                y=1.15, yanchor="top",
                active=1
            ),
        ],
        annotations=[
            dict(text="X-Axis:", x=0.1, y=1.2, xref="paper", yref="paper", showarrow=False, xanchor="left", yanchor="bottom"),
            dict(text="Y-Axis:", x=0.3, y=1.2, xref="paper", yref="paper", showarrow=False, xanchor="left", yanchor="bottom")
        ],
        title="Interactive Topic Comparison",
        xaxis_title=f"{x_name} Share (%)",
        yaxis_title=f"{y_name} Share (%)",
        xaxis_type="log" if log_scale else "linear",
        yaxis_type="log" if log_scale else "linear",
        height=800,
        hovermode='closest'
    )

    fig.write_html(output_file)
    print(f"  Saved comparison to {output_file}")


def _generate_treemap(entities: List[Dict], output_file: Path):
    all_data = []
    
    for item in entities:
        entity_name = item.get('display_name', 'Unknown Entity')
        topics = item.get('topics', [])
        
        for topic in topics:
            topic_name = topic.get('display_name', 'Unknown Topic')
            count = topic.get('count', 0)
            
            domain = topic.get('domain', {}).get('display_name', 'Unknown Domain')
            field = topic.get('field', {}).get('display_name', 'Unknown Field')
            subfield = topic.get('subfield', {}).get('display_name', 'Unknown Subfield')
            
            all_data.append({
                'Entity': entity_name,
                'Domain': domain,
                'Field': field,
                'Subfield': subfield,
                'Topic': topic_name,
                'Count': count
            })

    if not all_data:
        print("  No data found for treemap.")
        return

    df = pd.DataFrame(all_data)

    # We can create a faceted treemap or just one big one. 
    # Let's try to make it interactively selectable or just color by domain.
    # Given we might have totally different entities, putting them all in one treemap 
    # under a root of "All" or just using 'path' starting with Entity is good.
    
    fig = px.treemap(
        df, 
        path=['Entity', 'Domain', 'Field', 'Topic'], 
        values='Count',
        color='Domain', 
        hover_data=['Subfield'],
        height=800,
        title="Topic Distribution Treemap (Click to Zoom)"
    )

    fig.write_html(output_file)
    print(f"  Saved treemap to {output_file}")
