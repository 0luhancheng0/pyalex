import json
import typer
import pandas as pd
import plotly.express as px
from typing import Optional

app = typer.Typer(help="Visualize topic distribution from a JSONL file.")

@app.command()
def main(
    input_file: str = typer.Option(..., "--input-file", "-i", help="Path to input JSONL file."),
    output_file: str = typer.Option("topics_visualization.html", "--output-file", "-o", help="Path to save the HTML visualization."),
    entity_label: str = typer.Option("Entity", "--entity-label", "-l", help="Label for the top-level entity (e.g. Institution, Author).")
):
    """
    Generate a treemap visualization of topics from a JSONL file.
    
    The JSONL file is expected to contain objects with a 'display_name' and a 'topics' list.
    Each topic should have 'display_name', 'domain', 'field', and 'subfield'.
    """
    data = []
    
    print(f"Reading {input_file}...")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    item = json.loads(line)
                    # Use the provided label for the column name later, but store value here
                    entity_name = item.get('display_name', f'Unknown {entity_label}')
                    
                    # Iterate over topics
                    topics = item.get('topics', [])
                    if not topics:
                        continue
                        
                    for topic in topics:
                        # Extract relevant fields
                        topic_name = topic.get('display_name', 'Unknown Topic')
                        count = topic.get('count', 0) # Some entities might have a count/score per topic, or just presence
                        # If count is missing, maybe default to 1 for presence? 
                        # The original script defaulted to 0. If it's 0, treemap size might be 0? 
                        # Let's check original script logic. It used topic.get('count', 0). 
                        # If it's 0, plotly might hide it. 
                        # For works, topics don't have 'count'. They usually have score. 
                        # For institutions/authors, they have topic counts.
                        # I'll stick to 'count' for now as per original script, but maybe warn or use 1 if 0?
                        # Actually, let's just stick to the original logic for now.
                        
                        domain = topic.get('domain', {}).get('display_name', 'Unknown Domain')
                        field = topic.get('field', {}).get('display_name', 'Unknown Field')
                        subfield = topic.get('subfield', {}).get('display_name', 'Unknown Subfield')
                        
                        data.append({
                            entity_label: entity_name,
                            'Domain': domain,
                            'Field': field,
                            'Subfield': subfield,
                            'Topic': topic_name,
                            'Count': count
                        })
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        print(f"Error: File {input_file} not found.")
        raise typer.Exit(code=1)

    if not data:
        print("No data found to visualize.")
        return

    df = pd.DataFrame(data)

    # Filter out entries with 0 count if that's an issue? 
    # If all counts are 0, the map will be empty.
    # If the input is works, they might not have 'count'. 
    # If 'count' is 0, let's see. 
    # If this is for Works, each work belongs to a topic. The 'count' concept applies to aggregated entities (authors/insts).
    # If the user feeds works, maybe they want to count them?
    # But the structure implies we are reading a list of entities that *have* topics.
    # If the input is works, it has 'primary_topic' or 'topics'.
    # If it's works, 'topics' is a list.
    # If the user wants to visualize topics for a set of works, they would just count occurrences.
    # The original script was for institutions ('au.jsonl' implies Australian institutions maybe?).
    # So it expects entities that have aggregated topic counts.
    
    print("Generating Treemap...")
    fig = px.treemap(
        df, 
        path=[entity_label, 'Domain', 'Field', 'Topic'], 
        values='Count',
        color='Domain', 
        title=f'Topic Distribution by {entity_label}',
        hover_data=['Subfield'],
        height=800
    )

    # Save to HTML
    fig.write_html(output_file)
    print(f"Visualization saved to {output_file}")

if __name__ == "__main__":
    app()
