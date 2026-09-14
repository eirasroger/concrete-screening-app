"""
Pydantic schemas describing the structured data extracted by the LLM calls.

These models are passed to the OpenAI API as response formats, so the schema is
enforced during decoding rather than requested in the prompt text. Each model
mirrors, field for field, the dictionary structure consumed downstream by
`compliance_checker.py`, so `.model_dump()` yields exactly the shape the rest of
the application expects.

Note for maintainers: the API requires every field to be required, so optional
values are declared as `Optional[...]` (nullable) and never given a default.
"""

from typing import List, Optional

from pydantic import BaseModel


class Material(BaseModel):
    """A single line of an EPD material composition table."""
    name: str
    percentage: float


class EPDData(BaseModel):
    """Data extracted from an Environmental Product Declaration."""
    EPD_name: Optional[str]
    EPD_registration_number: Optional[str]
    density: Optional[float]
    MPa: Optional[int]
    max_aggregate_size: Optional[float]
    mat_comp: List[Material]


class ElementSpecificReqs(BaseModel):
    """Concrete requirements attached to a specific element in a drawing."""
    strength_class_mpa: Optional[float]
    min_cement_content: Optional[float]
    max_w_c_ratio: Optional[float]
    max_aggregate_size: Optional[float]


class DrawingAnalysis(BaseModel):
    """Result of analysing a technical drawing or project document."""
    element_specific_reqs: ElementSpecificReqs
    drawing_exposure_classes: List[str]
    analysis_notes: str


class CustomConstraints(BaseModel):
    """Technical constraints extracted from the user's free-text description."""
    min_cement_content: Optional[float]
    max_w_c_ratio: Optional[float]
    min_mpa_strength: Optional[float]
    max_aggregate_size: Optional[float]


class ExposureClassAssignment(BaseModel):
    """Exposure classes assigned to a user scenario under a given standard."""
    assigned_exposure_classes: List[str]
