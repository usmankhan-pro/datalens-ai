"""
DataLens AI - Data Ingestion Module.

Provides file loading, validation, and encoding/delimiter detection
for CSV, Excel (.xlsx/.xls), and JSON formats.
"""

from core.ingestion.models import LoadResult
from core.ingestion.loader import load_file
from core.ingestion.excel_loader import get_sheet_names

__all__ = ["LoadResult", "load_file", "get_sheet_names"]