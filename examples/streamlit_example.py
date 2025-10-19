"""
Example Streamlit app demonstrating PyAlex + Embedding Atlas integration.

Run with: streamlit run examples/streamlit_example.py
"""

import streamlit as st

from pyalex import Works
from pyalex.embeddings import prepare_works_for_embeddings
from pyalex.embeddings import pyalex_embedding_atlas

# Page config
st.set_page_config(page_title="OpenAlex Explorer", layout="wide")

st.title("🔬 OpenAlex Research Explorer")
st.markdown(
    "Interactive visualization of research works using PyAlex + Embedding Atlas"
)

# Sidebar controls
with st.sidebar:
    st.header("Query Settings")
    search_query = st.text_input(
        "Search Query", value="machine learning", help="Search OpenAlex works"
    )
    limit = st.slider("Number of works", 100, 5000, 1000, step=100)
    text_column = st.selectbox(
        "Text field",
        ["title", "abstract"],
        help="Column to use for embedding text",
    )

    if st.button("Fetch Data", type="primary"):
        with st.spinner(f"Fetching {limit} works..."):
            # Query OpenAlex
            works = Works().search(search_query).get(limit=limit)
            st.session_state["works"] = works
            st.session_state["text_column"] = text_column
            st.success(f"✓ Fetched {len(works)} works")

# Main content
if "works" in st.session_state:
    st.subheader("Embedding Visualization")

    # Prepare data
    prepared = prepare_works_for_embeddings(
        st.session_state["works"],
        text_column=st.session_state["text_column"],
        additional_columns=["publication_year", "open_access.is_oa"],
    )

    # Create visualization
    selection = pyalex_embedding_atlas(
        prepared,
        text="text",
        show_table=True,
        show_charts=True,
        show_embedding=True,
        labels="automatic",
        key="works_atlas",
    )

    # Show selection details
    if selection.get("predicate"):
        st.divider()
        st.subheader("📊 Selection Details")

        import duckdb

        filtered = duckdb.query_df(
            prepared,
            "df",
            f"SELECT * FROM df WHERE {selection['predicate']}",
        ).df()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Selected Works", len(filtered))
        with col2:
            avg_citations = filtered["cited_by_count"].mean()
            st.metric("Avg Citations", f"{avg_citations:.1f}")
        with col3:
            if "publication_year" in filtered.columns:
                year_range = (
                    f"{filtered['publication_year'].min()}-"
                    f"{filtered['publication_year'].max()}"
                )
                st.metric("Year Range", year_range)

        # Show data table
        st.dataframe(
            filtered[["label", "publication_year", "cited_by_count"]].head(20),
            use_container_width=True,
        )
else:
    st.info("👈 Configure your query in the sidebar and click 'Fetch Data'")
