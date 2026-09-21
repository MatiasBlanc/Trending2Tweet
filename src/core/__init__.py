"""Modelos del dominio compartidos por la CLI y la TUI."""

from src.core.models import Candidate, GenerationResult, PipelineEvent, PipelineStatus

__all__ = ["Candidate", "GenerationResult", "PipelineEvent", "PipelineStatus"]
