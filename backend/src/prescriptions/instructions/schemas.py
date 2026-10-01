"""Pydantic schemas for prescription instruction parsing, dose, frequency, duration, route, and timing."""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class InstructionStatus(str, Enum):
    """Extraction status for individual instruction fields."""
    PARSED = "parsed"
    UNCERTAIN = "uncertain"
    NOT_FOUND = "not_found"


class FrequencyType(str, Enum):
    """Standardized clinical frequency pattern categories."""
    DAILY_COUNT = "daily_count"      # e.g., twice daily, 3 times a day
    INTERVAL = "interval"            # e.g., every 8 hours, every 12 hours
    AS_NEEDED = "as_needed"          # e.g., PRN, as needed, عند اللزوم
    SPECIFIC_TIME = "specific_time"  # e.g., at bedtime, in morning
    UNCERTAIN = "uncertain"          # e.g., ambiguous or corrupt text


class DoseInstruction(BaseModel):
    """Structured explicit dose amount and unit extracted from prescription text."""
    value: Optional[float] = Field(None, description="Numeric quantity of the single dose (e.g., 1.0, 0.5, 5.0)")
    unit: Optional[str] = Field(None, description="Standardized unit (e.g., tablet, capsule, ml, spoon, drops)")
    raw_text: str = Field(..., description="Verbatim raw text snippet from OCR")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence in dose extraction")
    status: InstructionStatus = Field(InstructionStatus.PARSED, description="Field extraction status")


class FrequencyInstruction(BaseModel):
    """Structured frequency, interval, and timing schedule extracted from text."""
    frequency_type: FrequencyType = Field(FrequencyType.DAILY_COUNT, description="Pattern category")
    times_per_day: Optional[int] = Field(None, description="Number of times per day if daily_count or interval")
    interval_hours: Optional[int] = Field(None, description="Interval in hours if interval pattern (e.g. 8, 12)")
    specific_timing: Optional[str] = Field(None, description="Specific time of day (e.g., morning, evening, bedtime)")
    is_prn: bool = Field(False, description="Flag indicating as-needed / PRN administration")
    raw_text: str = Field(..., description="Verbatim raw frequency text from prescription")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score")
    status: InstructionStatus = Field(InstructionStatus.PARSED, description="Field extraction status")


class DurationInstruction(BaseModel):
    """Structured duration of treatment extracted strictly from written text."""
    value: Optional[float] = Field(None, description="Duration magnitude (e.g., 5.0, 7.0, 1.0)")
    unit: Optional[str] = Field(None, description="Duration time unit: days, weeks, months")
    raw_text: str = Field(..., description="Verbatim raw duration text")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score")
    status: InstructionStatus = Field(InstructionStatus.PARSED, description="Field extraction status")


class RouteInstruction(BaseModel):
    """Explicitly stated route of administration."""
    route: Optional[str] = Field(None, description="Normalized route (e.g., oral, topical, ophthalmic, otic, inhalation, IV, IM)")
    raw_text: str = Field(..., description="Verbatim route token")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score")
    status: InstructionStatus = Field(InstructionStatus.PARSED, description="Field extraction status")


class FoodTimingInstruction(BaseModel):
    """Food and meal timing relationship explicitly stated in text."""
    timing: Optional[str] = Field(None, description="Normalized timing: before_food, after_food, with_food, before_breakfast, empty_stomach, bedtime")
    raw_text: str = Field(..., description="Verbatim food timing token")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score")
    status: InstructionStatus = Field(InstructionStatus.PARSED, description="Field extraction status")


class ParsedPrescriptionInstructions(BaseModel):
    """Master structured instructions parsed strictly from explicit prescription text."""
    dose: Optional[DoseInstruction] = Field(None, description="Explicit dose instruction if present")
    frequency: Optional[FrequencyInstruction] = Field(None, description="Explicit frequency instruction if present")
    duration: Optional[DurationInstruction] = Field(None, description="Explicit treatment duration if present")
    route: Optional[RouteInstruction] = Field(None, description="Explicit administration route if present")
    food_timing: Optional[FoodTimingInstruction] = Field(None, description="Explicit meal/food timing if present")
    prn: bool = Field(False, description="Whether medication is marked as-needed / PRN")
    special_instructions: List[str] = Field(default_factory=list, description="Other explicit non-standard directions")
    raw_instruction_text: str = Field(..., description="Full raw input line containing instructions")
    overall_confidence: float = Field(0.0, ge=0.0, le=1.0, description="Composite instruction extraction confidence")
    uncertain_fields: List[str] = Field(default_factory=list, description="List of instruction fields marked uncertain")
