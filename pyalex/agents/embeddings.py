
from sentence_transformers import SentenceTransformer 
from sklearn.metrics.pairwise import cosine_similarity
import seaborn as sns
from einops import reduce


embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = aspects_df.apply(lambda x: embedding_model.encode(x.values), axis=0)
inputs = aspects_df.to_numpy().flatten()
embeddings = embedding_model.encode(inputs).reshape(aspects_df.shape[0], aspects_df.shape[1], -1)

publication_embedding = reduce(embeddings, 'n_publication n_aspect d_model -> n_publication d_model', 'mean')
aspect_embeddings = reduce(embeddings, 'n_publication n_aspect d_model -> n_aspect d_model', 'mean')


publication_sim = cosine_similarity(publication_embedding)
aspect_sim = cosine_similarity(aspect_embeddings)
sns.heatmap(publication_sim, annot=True, fmt=".2f", cmap="Blues")
sns.heatmap(aspect_sim, annot=True, fmt=".2f", cmap="Greens", xticklabels=aspects_df.columns, yticklabels=aspects_df.columns)

