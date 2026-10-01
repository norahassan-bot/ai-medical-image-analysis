"""Abstract Base Provider for Medication Information and Concept Resolution."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from ..schemas import MedicationConcept


class MedicationInfoProvider(ABC):
    """Abstract interface for medication concept resolution providers (RxNorm, Local Catalogs)."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider system."""
        pass

    @property
    @abstractmethod
    def provider_version(self) -> str:
        """Release or database version of the provider."""
        pass

    @abstractmethod
    def search(self, query: str, limit: int = 5) -> List[MedicationConcept]:
        """Search canonical concepts by exact or prefix name."""
        pass

    @abstractmethod
    def get_by_identifier(self, identifier: str) -> Optional[MedicationConcept]:
        """Retrieve full medication concept by unique concept ID."""
        pass

    @abstractmethod
    def find_candidates(self, query: str, limit: int = 5) -> List[MedicationConcept]:
        """Search approximate or fuzzy candidates matching query."""
        pass

    def get_provider_info(self) -> Dict[str, str]:
        """Return provider metadata dictionary."""
        return {
            "provider": self.provider_name,
            "version": self.provider_version
        }
