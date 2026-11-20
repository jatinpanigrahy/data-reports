"""Automated financial spend report generator.

Generates single-page executive PDF dashboards from raw transaction exports.
"""

from reportgen.config import (
    DataLoadError,
    DataProcessingError,
    PDFBuildError,
    RenderingError,
    ReportConfig,
    ReportGenError,
    SchemaValidationError,
)
from reportgen.pipeline import generate_report

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "DataLoadError",
    "DataProcessingError",
    "PDFBuildError",
    "RenderingError",
    "ReportConfig",
    "ReportGenError",
    "SchemaValidationError",
    "generate_report",
]
