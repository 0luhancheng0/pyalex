import json
import typer
import pandas as pd
import plotly.express as px

app = typer.Typer(help="Visualize topic distribution from a JSONL file.")

@app.command()
def main(
    input_file: str = typer.Option(..., "--input-file", "-i", help="Path to input JSONL file."),
    output_file: str = typer.Option("topics_visualization.html", "--output-file", "-o", help="Path to save the HTML visualization."),
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
                    entity_name = item.get('display_name', 'Unknown Entity')
                    
                    # Iterate over topics
                    topics = item.get('topics', [])
                    if not topics:
                        continue
                        
                    for topic in topics:
                        # Extract relevant fields
                        topic_name = topic.get('display_name', 'Unknown Topic')
                        count = topic.get('count', 0) # Some entities might have a count/score per topic, or just presence
                        
                        domain = topic.get('domain', {}).get('display_name', 'Unknown Domain')
                        field = topic.get('field', {}).get('display_name', 'Unknown Field')
                        subfield = topic.get('subfield', {}).get('display_name', 'Unknown Subfield')
                        
                        data.append({
                            'Entity': entity_name,
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

    print("Generating Treemap...")
    fig = px.treemap(
        df, 
        path=['Entity', 'Domain', 'Field', 'Topic'], 
        values='Count',
        color='Domain', 
        hover_data=['Subfield'],
        height=800
    )

    # Save to HTML
    fig.write_html(output_file)
    print(f"Visualization saved to {output_file}")

if __name__ == "__main__":
    app()
