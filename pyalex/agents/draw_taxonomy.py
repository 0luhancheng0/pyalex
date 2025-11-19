import pickle
import networkx as nx
import plotly.graph_objects as go
from pathlib import Path
import sys


def draw_taxonomy(G):
    VisG = nx.DiGraph()
    root_id = "ROOT"
    VisG.add_node(root_id, name="Root", node_type="root")

    categories = []
    works = []
    
    # Separate nodes
    for node, data in G.nodes(data=True):
        if data.get("node_type") == "category":
            categories.append(node)
            VisG.add_node(node, **data)
        elif data.get("node_type") == "work":
            works.append(node)
            VisG.add_node(node, **data)

    # Add edges: Category -> Category
    for u, v in G.edges():
        if u in categories and v in categories:
            VisG.add_edge(u, v)
    
    # Connect Root to top-level categories
    # Top-level are those with no incoming edges from other categories
    for cat in categories:
        in_edges = [u for u, _ in G.in_edges(cat) if u in categories]
        if not in_edges:
            VisG.add_edge(root_id, cat)

    # Add edges: Category -> Work
    # In G, edges are Work -> Category. We reverse them.
    for work in works:
        # Find categories this work belongs to
        for neighbor in G.neighbors(work):
            if neighbor in categories:
                VisG.add_edge(neighbor, work)

    # Calculate Depths (X)
    depths = {}
    # BFS from Root
    try:
        depths = nx.shortest_path_length(VisG, source=root_id)
    except Exception as e:
        print(f"Error calculating depths: {e}")
        return

    # Determine max category depth
    max_cat_depth = 0
    for cat in categories:
        d = depths.get(cat, 0)
        if d > max_cat_depth:
            max_cat_depth = d
    
    # Set work depth
    work_depth = max_cat_depth + 1
    for work in works:
        depths[work] = work_depth

    # Calculate Y positions
    y_positions = {}
    next_y = 0

    # Helper for tree layout (categories)
    def layout_category(node):
        nonlocal next_y
        children = [n for n in VisG.successors(node) if n in categories]
        # Sort children by name for consistent layout
        children.sort()
        
        if not children:
            y_positions[node] = next_y
            next_y += 1
        else:
            child_ys = []
            for child in children:
                layout_category(child)
                child_ys.append(y_positions[child])
            y_positions[node] = sum(child_ys) / len(child_ys)

    layout_category(root_id)

    # Layout works
    work_y_map = []
    for work in works:
        parents = [p for p in VisG.predecessors(work) if p in categories]
        if parents:
            avg_y = sum(y_positions.get(p, 0) for p in parents) / len(parents)
            work_y_map.append((work, avg_y))
        else:
            work_y_map.append((work, next_y)) # Orphan work?

    # Sort works by ideal Y
    work_y_map.sort(key=lambda x: x[1])
    
    # Assign final Ys with spacing
    sorted_works = [w for w, y in work_y_map]
    if sorted_works:
        final_work_ys = {}
        min_dist = 0.8 # Adjust as needed
        
        curr_y = work_y_map[0][1]
        final_work_ys[sorted_works[0]] = curr_y
        
        for i in range(1, len(sorted_works)):
            w = sorted_works[i]
            ideal_y = work_y_map[i][1]
            # Ensure at least min_dist from previous, but try to stay close to ideal
            new_y = max(ideal_y, final_work_ys[sorted_works[i-1]] + min_dist)
            final_work_ys[w] = new_y
            
        y_positions.update(final_work_ys)

    # Prepare Plotly data
    node_x = []
    node_y = []
    node_text = []
    node_color = []
    node_size = []
    node_hover = []

    for node in VisG.nodes():
        if node not in depths or node not in y_positions:
            continue
            
        node_x.append(depths[node])
        node_y.append(y_positions[node])
        
        data = VisG.nodes[node]
        name = data.get("name", node)
        node_type = data.get("node_type", "category")
        
        node_hover.append(name)
        
        if node_type == "root":
            node_color.append("#FFD700") # Gold
            node_size.append(20)
            node_text.append("Root")
        elif node_type == "category":
            node_color.append("#87CEEB") # SkyBlue
            node_size.append(15)
            node_text.append(name)
        else: # work
            node_color.append("#FA8072") # Salmon
            node_size.append(10)
            node_text.append("") 

    # Edges
    edge_x = []
    edge_y = []
    
    for u, v in VisG.edges():
        if u in depths and v in depths and u in y_positions and v in y_positions:
            edge_x.extend([depths[u], depths[v], None])
            edge_y.extend([y_positions[u], y_positions[v], None])

    fig = go.Figure()

    # Edges trace
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines'
    ))

    # Nodes trace
    fig.add_trace(go.Scatter(
        x=node_x, y=node_y,
        mode='markers',
        marker=dict(
            showscale=False,
            color=node_color,
            size=node_size,
            line_width=1
        ),
        text=node_hover,
        hoverinfo='text'
    ))

    fig.update_layout(
        title='Taxonomy Visualization',
        title_x=0.5,
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title="Depth"),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor='white',
        width=1200,
        height=800
    )
    
    fig.show()

if __name__ == "__main__":
    draw_taxonomy()
