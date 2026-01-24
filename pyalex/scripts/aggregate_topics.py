import json
import typer
from typing import List
from pathlib import Path

app = typer.Typer(help="Aggregate topics from multiple JSONL files into grouped entities.")

@app.command()
def main(
    inputs: List[str] = typer.Option(
        ..., 
        "--input", 
        "-i", 
        help="Input file in format 'Label:Path'. Can be used multiple times. Example: 'US:examples/us.jsonl'"
    ),
    output_file: str = typer.Option(
        "aggregated_topics.jsonl", 
        "--output-file", 
        "-o", 
        help="Path to save the aggregated JSONL file."
    ),
):
    """
    Aggregates topic counts from multiple JSONL files.
    
    For each input file (representing a group like 'US' or 'Australia'), 
    it sums up the counts of each topic across all entities in that file.
    The output is a single JSONL file with one entry per group, compatible with visualize_topics.py.
    """
    
    aggregated_data = {}

    for input_str in inputs:
        try:
            label, path_str = input_str.split(":", 1)
        except ValueError:
            print(f"Error: Invalid input format '{input_str}'. Expected 'Label:Path'.")
            raise typer.Exit(code=1)
            
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
                            
                            if t_id not in group_topics:
                                # Store metadata from the first occurrence
                                # We remove 'count' and 'score' from meta to avoid confusion, 
                                # as we are calculating our own aggregate count.
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

    # Write output
    print(f"Writing results to {output_file}...")
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
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
                
                f.write(json.dumps(group_entity) + "\n")
                
    except Exception as e:
        print(f"Error writing output: {e}")
        raise typer.Exit(code=1)

    print("Aggregation complete.")

if __name__ == "__main__":
    app()
