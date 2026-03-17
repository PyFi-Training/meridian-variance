from dataclasses import dataclass, field
from typing import List


@dataclass
class Config:
    # Company
    company_name: str = "Meridian Components Ltd"
    period: str = "Full Year 2025"
    industry: str = "precision manufacturing"
    plants: List[str] = field(default_factory=lambda: ["Plant A", "Plant B"])

    # Models
    commentary_model: str = "gpt-4o"
    summary_model: str = "gpt-4o"
    chat_model: str = "gpt-4o"

    # Generation settings
    commentary_max_tokens: int = 90
    summary_max_tokens: int = 280
    cfo_brief_max_tokens: int = 600
    commentary_temperature: float = 0.4
    summary_temperature: float = 0.5
    chat_temperature: float = 0.7

    # Paths
    plant_a_path: str = "data/input/plant_a.csv"
    plant_b_path: str = "data/input/plant_b.csv"
    output_path: str = "data/output/variance_report.csv"


CONFIG = Config()
