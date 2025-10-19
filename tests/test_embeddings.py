"""
Tests for pyalex.embeddings module
"""

import pandas as pd
import pytest


class TestEmbeddingsUtils:
    """Test data preparation utilities."""

    def test_prepare_works_for_embeddings_basic(self):
        """Test basic works preparation."""
        from pyalex.embeddings.utils import prepare_works_for_embeddings

        # Create sample works DataFrame
        df = pd.DataFrame(
            {
                "id": ["W1", "W2", "W3"],
                "title": ["Title 1", "Title 2", "Title 3"],
                "abstract": ["Abstract 1", "Abstract 2", "Abstract 3"],
                "cited_by_count": [10, 20, 30],
            }
        )

        result = prepare_works_for_embeddings(df)

        # Check required columns
        assert "id" in result.columns
        assert "text" in result.columns
        assert "label" in result.columns
        assert len(result) == 3

    def test_prepare_works_with_custom_text_column(self):
        """Test works preparation with custom text column."""
        from pyalex.embeddings.utils import prepare_works_for_embeddings

        df = pd.DataFrame(
            {
                "id": ["W1"],
                "title": ["Title"],
                "abstract": ["Custom abstract"],
            }
        )

        result = prepare_works_for_embeddings(df, text_column="abstract")

        assert result["text"].iloc[0] == "Custom abstract"

    def test_prepare_works_with_missing_text(self):
        """Test works preparation handles missing text values."""
        from pyalex.embeddings.utils import prepare_works_for_embeddings

        df = pd.DataFrame(
            {
                "id": ["W1", "W2"],
                "title": ["Title", None],
            }
        )

        result = prepare_works_for_embeddings(df)

        # Should convert None to empty string
        assert result["text"].iloc[1] == ""

    def test_prepare_authors_for_embeddings(self):
        """Test authors preparation."""
        from pyalex.embeddings.utils import prepare_authors_for_embeddings

        df = pd.DataFrame(
            {
                "id": ["A1", "A2"],
                "display_name": ["Author 1", "Author 2"],
                "works_count": [100, 200],
            }
        )

        result = prepare_authors_for_embeddings(df)

        assert "id" in result.columns
        assert "text" in result.columns
        assert result["text"].iloc[0] == "Author 1"

    def test_prepare_topics_for_embeddings(self):
        """Test topics preparation."""
        from pyalex.embeddings.utils import prepare_topics_for_embeddings

        df = pd.DataFrame(
            {
                "id": ["T1", "T2"],
                "display_name": ["Topic 1", "Topic 2"],
                "description": ["Desc 1", "Desc 2"],
            }
        )

        result = prepare_topics_for_embeddings(df)

        assert "id" in result.columns
        assert "text" in result.columns
        # Text should combine display_name and description
        assert "Topic 1" in result["text"].iloc[0]
        assert "Desc 1" in result["text"].iloc[0]

    def test_prepare_topics_without_description(self):
        """Test topics preparation when description column is missing."""
        from pyalex.embeddings.utils import prepare_topics_for_embeddings

        df = pd.DataFrame(
            {
                "id": ["T1"],
                "display_name": ["Topic 1"],
            }
        )

        result = prepare_topics_for_embeddings(df, description_column=None)

        assert result["text"].iloc[0] == "Topic 1"

    def test_additional_columns_preserved(self):
        """Test that additional columns are preserved in output."""
        from pyalex.embeddings.utils import prepare_works_for_embeddings

        df = pd.DataFrame(
            {
                "id": ["W1"],
                "title": ["Title"],
                "custom_field": ["Custom"],
                "another_field": [42],
            }
        )

        result = prepare_works_for_embeddings(
            df, additional_columns=["custom_field", "another_field"]
        )

        assert "custom_field" in result.columns
        assert "another_field" in result.columns
        assert result["custom_field"].iloc[0] == "Custom"


class TestStreamlitComponent:
    """Test Streamlit component wrapper."""

    def test_import_error_handling(self):
        """Test that ImportError is raised when embedding-atlas not installed."""
        from pyalex.embeddings.streamlit import EMBEDDING_ATLAS_AVAILABLE

        # If embedding-atlas is not installed, should have flag set
        if not EMBEDDING_ATLAS_AVAILABLE:
            from pyalex.embeddings.streamlit import pyalex_embedding_atlas

            df = pd.DataFrame({"id": ["W1"], "text": ["Test"]})

            with pytest.raises(ImportError, match="embedding-atlas"):
                pyalex_embedding_atlas(df)

    def test_module_imports(self):
        """Test that main imports work."""
        from pyalex.embeddings import prepare_authors_for_embeddings
        from pyalex.embeddings import prepare_topics_for_embeddings
        from pyalex.embeddings import prepare_works_for_embeddings
        from pyalex.embeddings import pyalex_embedding_atlas

        # Just check they're callable
        assert callable(prepare_works_for_embeddings)
        assert callable(prepare_authors_for_embeddings)
        assert callable(prepare_topics_for_embeddings)
        assert callable(pyalex_embedding_atlas)
