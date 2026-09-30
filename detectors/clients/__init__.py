"""
ARKHÉ Semantic Baseline Clients
===============================
Provides structured semantic classification clients:
- OpenAISemanticClient: Real OpenAI API client with Pydantic structured output.
- OfflineSemanticProxy: Deterministic local heuristic proxy for offline testing.
"""

from detectors.clients.schema import SemanticClassificationResponse
from detectors.clients.offline_semantic_proxy import OfflineSemanticProxy
from detectors.clients.openai_semantic_client import OpenAISemanticClient

__all__ = [
    "SemanticClassificationResponse",
    "OfflineSemanticProxy",
    "OpenAISemanticClient",
]
