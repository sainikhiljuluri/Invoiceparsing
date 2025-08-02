"""
Generate embeddings for product names using sentence transformers
"""

import logging
from typing import List
import numpy as np

# Try to import sentence_transformers, provide fallback if not available
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    logging.warning("sentence_transformers not available. Install with: pip install sentence-transformers")

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate embeddings for product similarity matching"""
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model_name = model_name
        self.model = None
        self.embedding_dim = 384  # Default for MiniLM
        
        if EMBEDDINGS_AVAILABLE:
            try:
                self.model = SentenceTransformer(model_name)
                logger.info(f"Loaded embedding model: {model_name}")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        if not self.model:
            # Return random embedding if model not available
            return np.random.randn(self.embedding_dim).tolist()
        
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return np.zeros(self.embedding_dim).tolist()
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        if not self.model:
            return [np.random.randn(self.embedding_dim).tolist() for _ in texts]
        
        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return [np.zeros(self.embedding_dim).tolist() for _ in texts]
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        try:
            # Convert to numpy arrays
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0