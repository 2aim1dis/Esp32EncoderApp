# Μάθημα: Κατανοώντας το data_export.py - Professional Data Export & Analysis

## Περιεχόμενα
1. [Data Export Architecture](#1-data-export-architecture)
2. [DataExporter Class Design](#2-dataexporter-class-design)
3. [Excel Export Implementation](#3-excel-export-implementation)
4. [CSV Export Strategy](#4-csv-export-strategy)
5. [Data Transformation Pipeline](#5-data-transformation-pipeline)
6. [Export Statistics & Validation](#6-export-statistics--validation)
7. [Error Handling & Recovery](#7-error-handling--recovery)
8. [Professional Export Patterns](#8-professional-export-patterns)

---

## 1. Data Export Architecture

### Export System Design Philosophy

```python
"""
Data export functionality for the Encoder GUI.
Handles exporting measurement data to various formats.
"""

import pandas as pd
from typing import List
from data_models import Sample
from config import DEFAULT_EXPORT_EXTENSION, EXCEL_SHEET_NAME
```

**Export Pipeline Architecture:**
```
┌─────────────────────────────────────────────────────────────┐
│                   DATA EXPORT PIPELINE                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐    ┌─────────────────────────────────┐  │
│  │   DATA MODELS   │    │      DATA EXPORTER              │  │
│  │                 │ ──►│    (Format Abstraction)         │  │
│  │ • Sample objects│    │                                 │  │
│  │ • DataBuffer    │    │ • Format selection              │  │
│  │ • Memory mgmt   │    │ • Data transformation           │  │
│  └─────────────────┘    │ • Error handling               │  │
│                         │ • Progress tracking             │  │
│                         └─────────────┬───────────────────┘  │
│                                       │                      │
│                                       ▼                      │
│                         ┌─────────────────────────────────┐  │
│                         │      FORMAT HANDLERS            │  │
│                         │                                 │  │
│  ┌─────────────────────┐│ Excel (.xlsx):                  │  │
│  │     OUTPUT FILES    │││ • Rich formatting              │  │
│  │                     │││ • Multiple sheets              │  │ 
│  │ • Professional      │││ • Metadata support             │  │
│  │   Excel reports     │││                                │  │
│  │ • CSV data files    │││ CSV (.csv):                    │  │
│  │ • Analysis ready    │││ • Universal compatibility       │  │
│  │ • Import friendly   │││ • Fast processing              │  │
│  └─────────────────────┘││ • Lightweight                 │  │
│                         └─────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Design Benefits:**
```python
# ✅ GOOD - Modular Export Architecture:

# Layer 1: Data abstraction (Sample objects)
samples = [Sample(t=0.1, pulses=1000, delta=10, force=2.3), ...]

# Layer 2: Export coordination (DataExporter)
exporter = DataExporter()
success = exporter.export_to_excel(samples, "data.xlsx")

# Layer 3: Format-specific handling (pandas integration)
# - Excel: Rich formatting, multiple sheets, metadata
# - CSV: Universal compatibility, fast processing

# Benefits:
# ✅ Format independence - Easy to add new export formats
# ✅ Error isolation - Format errors don't affect application
# ✅ Testability - Each layer can be tested independently  
# ✅ Reusability - Export logic can be used in different contexts
```

---

## 2. DataExporter Class Design

### Static Method Architecture

```python
class DataExporter:
    """Handles exporting measurement data to various formats."""
    
    @staticmethod
    def export_to_excel(samples: List[Sample], filename: str) -> bool:
        """Export samples to Excel format."""
        
    @staticmethod
    def export_to_csv(samples: List[Sample], filename: str) -> bool:
        """Export samples to CSV format."""
        
    @staticmethod
    def get_export_summary(samples: List[Sample]) -> dict:
        """Get summary statistics for the data to be exported."""
```

**Why Static Methods?**

```python
# Static method benefits for export operations:

# ✅ Stateless operations - No instance state needed
exporter_result = DataExporter.export_to_excel(data, "file.xlsx")

# ✅ Thread safety - No shared state between calls
# Multiple threads can export simultaneously:
thread1: DataExporter.export_to_excel(data1, "file1.xlsx")  
thread2: DataExporter.export_to_csv(data2, "file2.csv")

# ✅ Memory efficiency - No object allocation overhead
# Direct class method call without instantiation

# ✅ Functional style - Clear input → output relationship
samples_in → export_to_excel() → bool_success

# ❌ Alternative instance-based approach:
class DataExporter:
    def __init__(self):
        self.last_export_time = None  # Unnecessary state
        self.export_count = 0         # Not needed per export
    
# Static approach is cleaner for pure transformation operations
```

**Static vs Instance Design Trade-offs:**

```python
# When to use static methods (DataExporter case):
# ✅ Pure functions - Same input always produces same output
# ✅ No state needed - Each export is independent 
# ✅ Utility functions - General-purpose export operations
# ✅ Thread safety - No shared mutable state

# When to use instance methods (alternative design):
class StatefulExporter:
    def __init__(self, default_format="xlsx", progress_callback=None):
        self.default_format = default_format
        self.progress_callback = progress_callback
        self.export_history = []
    
    def export(self, samples, filename=None):
        # Uses instance configuration and tracks history
        pass

# Current design choice: Static methods are correct for this use case
```

---

## 3. Excel Export Implementation

### Excel Export Pipeline

```python
@staticmethod
def export_to_excel(samples: List[Sample], filename: str) -> bool:
    """Export samples to Excel format with comprehensive error handling."""
    
    if not samples:
        return False
        
    try:
        # Step 1: Data transformation
        data_rows = []
        for sample in samples:
            row = {
                "time_s": sample.t,
                "pulses": sample.pulses,  
                "delta": sample.delta,
                "force_kg": sample.force if sample.force is not None else ""
            }
            data_rows.append(row)
        
        # Step 2: DataFrame creation  
        df = pd.DataFrame(data_rows)
        
        # Step 3: Excel export with formatting
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name=EXCEL_SHEET_NAME)
            
        return True
        
    except Exception:
        return False
```

**Excel Implementation Analysis:**

### 3.1 Data Transformation Strategy
```python
# Transformation pipeline design:

# Input: Sample objects with typed fields
sample = Sample(t=1.234, pulses=12345, delta=10, force=2.34)

# Transformation: Sample → Dictionary
row = {
    "time_s": sample.t,                    # float → float (direct)
    "pulses": sample.pulses,               # int → int (direct)  
    "delta": sample.delta,                 # int → int (direct)
    "force_kg": sample.force if sample.force is not None else ""  # Optional[float] → str
}

# Benefits of dictionary transformation:
# ✅ Pandas compatibility - Direct DataFrame construction
# ✅ Column naming - Explicit field names with units
# ✅ None handling - Graceful handling of missing force data
# ✅ Type preservation - Maintains numeric types where possible
```

**Force Field Handling:**
```python
# Force field special handling rationale:
"force_kg": sample.force if sample.force is not None else ""

# Why empty string instead of None?
# ✅ Excel display: Empty cell vs "#N/A" 
# ✅ User experience: Clean appearance in spreadsheet
# ✅ Import compatibility: Other tools handle empty strings better
# ✅ Formula compatibility: Empty strings don't break Excel formulas

# Alternative approaches and their issues:
"force_kg": sample.force or 0.0          # ❌ Confuses missing data with zero force
"force_kg": sample.force or "N/A"        # ❌ Breaks numeric analysis
"force_kg": sample.force or pd.NaN       # ✅ Technically correct but less user-friendly
```

### 3.2 Excel Engine Selection

```python
with pd.ExcelWriter(filename, engine='openpyxl') as writer:
    df.to_excel(writer, index=False, sheet_name=EXCEL_SHEET_NAME)
```

**Engine Comparison:**
```python
# Excel engine options and trade-offs:

engines = {
    'openpyxl': {
        'format': '.xlsx',
        'read_write': 'both',
        'features': ['formatting', 'charts', 'images', 'multiple_sheets'],
        'performance': 'medium',
        'memory_usage': 'medium',
        'dependencies': 'openpyxl package'
    },
    'xlsxwriter': {
        'format': '.xlsx', 
        'read_write': 'write_only',
        'features': ['advanced_formatting', 'charts', 'conditional_formatting'],
        'performance': 'fast',
        'memory_usage': 'low',
        'dependencies': 'xlsxwriter package'
    },
    'xlwt': {
        'format': '.xls (legacy)',
        'read_write': 'write_only', 
        'features': ['basic_formatting'],
        'performance': 'fast',
        'memory_usage': 'very_low',
        'dependencies': 'xlwt package'
    }
}

# Why openpyxl chosen?
# ✅ Modern format (.xlsx) - Industry standard
# ✅ Read/write capability - Future expansion possible
# ✅ Rich features - Professional output
# ✅ Pandas integration - Well supported
# ❌ Performance penalty - Acceptable for typical data sizes
```

### 3.3 Context Manager Usage

```python
with pd.ExcelWriter(filename, engine='openpyxl') as writer:
    df.to_excel(writer, index=False, sheet_name=EXCEL_SHEET_NAME)
```

**Context Manager Benefits:**
```python
# ✅ Automatic resource cleanup:
with pd.ExcelWriter(filename) as writer:
    df.to_excel(writer, ...)
    # File automatically closed and finalized here
    # Even if exception occurs during export

# ❌ Manual resource management (error-prone):
writer = pd.ExcelWriter(filename)
try:
    df.to_excel(writer, ...)
    writer.save()  # Could be forgotten!
except Exception:
    # File might remain open or corrupted
    pass
finally:
    writer.close()  # Required manual cleanup

# Context manager handles:
# ✅ File closing on success
# ✅ File closing on exception  
# ✅ Proper Excel file finalization
# ✅ Memory cleanup
```

---

## 4. CSV Export Strategy

### CSV Export Implementation

```python
@staticmethod
def export_to_csv(samples: List[Sample], filename: str) -> bool:
    """Export samples to CSV format for universal compatibility."""
    
    if not samples:
        return False
        
    try:
        # Identical data transformation to Excel
        data_rows = []
        for sample in samples:
            row = {
                "time_s": sample.t,
                "pulses": sample.pulses,
                "delta": sample.delta, 
                "force_kg": sample.force if sample.force is not None else ""
            }
            data_rows.append(row)
        
        # DataFrame creation and CSV export
        df = pd.DataFrame(data_rows)
        df.to_csv(filename, index=False)
        
        return True
        
    except Exception:
        return False
```

**CSV vs Excel Trade-offs:**

```python
# Format comparison for encoder data:

csv_characteristics = {
    'file_size': 'Small (text-based compression)',
    'compatibility': 'Universal (any text editor, Excel, Python, R)',
    'features': 'Data only (no formatting, formulas, charts)',
    'performance': 'Fast read/write',
    'human_readable': 'Yes (plain text)',
    'analysis_ready': 'Excellent (direct import to analysis tools)',
    'professional_appearance': 'Basic'
}

excel_characteristics = {
    'file_size': 'Larger (binary format)',
    'compatibility': 'High (Microsoft Office, LibreOffice, Google Sheets)',
    'features': 'Rich (formatting, formulas, charts, multiple sheets)',
    'performance': 'Slower read/write',
    'human_readable': 'No (binary format)',
    'analysis_ready': 'Good (import needed)',
    'professional_appearance': 'Excellent'
}

# When to choose CSV:
# ✅ Data analysis workflows (Python, R, MATLAB)
# ✅ Large datasets (performance critical)
# ✅ Cross-platform compatibility needed
# ✅ Automated processing pipelines
# ✅ Version control friendly (text-based)

# When to choose Excel:
# ✅ Business reports and presentations
# ✅ Manual data review and annotation
# ✅ Sharing with non-technical users
# ✅ Rich formatting and visualization needed
# ✅ Multiple related datasets (multiple sheets)
```

### CSV Format Optimization

```python
# Advanced CSV export with optimization options:
@staticmethod
def export_to_csv_advanced(samples: List[Sample], filename: str, 
                          precision: int = 3, delimiter: str = ',') -> bool:
    """Advanced CSV export with formatting control."""
    
    try:
        data_rows = []
        for sample in samples:
            row = {
                "time_s": round(sample.t, precision) if sample.t else "",
                "pulses": sample.pulses,
                "delta": sample.delta,
                "force_kg": round(sample.force, precision) if sample.force is not None else ""
            }
            data_rows.append(row)
        
        df = pd.DataFrame(data_rows)
        
        # Advanced CSV options:
        df.to_csv(
            filename, 
            index=False,                    # No row indices
            sep=delimiter,                  # Customizable delimiter
            float_format=f'%.{precision}f', # Control decimal places
            lineterminator='\n',           # Unix line endings
            encoding='utf-8'                # Unicode support
        )
        
        return True
        
    except Exception as e:
        print(f"CSV export error: {e}")
        return False

# Usage examples:
DataExporter.export_to_csv_advanced(samples, "data.csv", precision=2)        # 2 decimal places
DataExporter.export_to_csv_advanced(samples, "data.tsv", delimiter='\t')     # Tab-separated
```

---

## 5. Data Transformation Pipeline

### Transformation Design Patterns

```python
# Data transformation abstraction:
class DataTransformer:
    """Handles transformation of Sample objects to export formats."""
    
    @staticmethod
    def samples_to_dict_rows(samples: List[Sample]) -> List[dict]:
        """Convert samples to list of dictionaries for export."""
        
        rows = []
        for sample in samples:
            row = DataTransformer._sample_to_dict(sample)
            rows.append(row)
        
        return rows
    
    @staticmethod
    def _sample_to_dict(sample: Sample) -> dict:
        """Convert single sample to dictionary with proper formatting."""
        
        return {
            "time_s": sample.t,
            "pulses": sample.pulses,
            "delta": sample.delta,
            "force_kg": DataTransformer._format_force(sample.force)
        }
    
    @staticmethod
    def _format_force(force: Optional[float]) -> str:
        """Format force value for export."""
        
        if force is None:
            return ""
        
        # Round to 3 decimal places for reasonable precision
        return f"{force:.3f}"
```

**Pipeline Benefits:**
```python
# Transformation pipeline advantages:

# Before: Inline transformation (repeated code)
def export_to_excel(samples, filename):
    rows = []
    for sample in samples:  # ❌ Repeated in every export method
        row = {"time_s": sample.t, ...}  # ❌ Formatting logic duplicated
        rows.append(row)
    # ... export logic

def export_to_csv(samples, filename):
    rows = []
    for sample in samples:  # ❌ Same transformation code again
        row = {"time_s": sample.t, ...}  # ❌ Inconsistent formatting risk
        rows.append(row)
    # ... export logic

# After: Pipeline approach (DRY principle)
def export_to_excel(samples, filename):
    rows = DataTransformer.samples_to_dict_rows(samples)  # ✅ Reusable
    df = pd.DataFrame(rows)
    # ... Excel-specific export logic

def export_to_csv(samples, filename):
    rows = DataTransformer.samples_to_dict_rows(samples)  # ✅ Same transformation
    df = pd.DataFrame(rows)
    # ... CSV-specific export logic

# Benefits:
# ✅ DRY principle - Single transformation implementation
# ✅ Consistency - Same formatting across all formats
# ✅ Testability - Transformation logic can be tested independently
# ✅ Maintainability - Changes in one place affect all exports
```

### Advanced Transformation Options

```python
class ConfigurableTransformer:
    """Transformer with configurable output options."""
    
    def __init__(self, time_unit='s', force_unit='kg', precision=3):
        self.time_unit = time_unit
        self.force_unit = force_unit  
        self.precision = precision
    
    def transform_samples(self, samples: List[Sample]) -> List[dict]:
        """Transform with configuration options."""
        
        return [self._transform_sample(sample) for sample in samples]
    
    def _transform_sample(self, sample: Sample) -> dict:
        """Transform single sample with unit conversions."""
        
        # Time conversion
        time_value = sample.t
        time_label = f"time_{self.time_unit}"
        
        if self.time_unit == 'ms':
            time_value *= 1000
        elif self.time_unit == 'min':  
            time_value /= 60
        
        # Force conversion  
        force_value = sample.force
        force_label = f"force_{self.force_unit}"
        
        if force_value is not None and self.force_unit == 'g':
            force_value *= 1000  # kg to grams
        elif force_value is not None and self.force_unit == 'lb':
            force_value *= 2.20462  # kg to pounds
        
        return {
            time_label: round(time_value, self.precision) if time_value else "",
            "pulses": sample.pulses,
            "delta": sample.delta,
            force_label: round(force_value, self.precision) if force_value else ""
        }

# Usage for different requirements:
transformer_metric = ConfigurableTransformer('s', 'kg', 3)      # Standard
transformer_imperial = ConfigurableTransformer('s', 'lb', 2)    # US units
transformer_ms = ConfigurableTransformer('ms', 'g', 1)          # High precision
```

---

## 6. Export Statistics & Validation

### Statistical Summary Implementation

```python
@staticmethod
def get_export_summary(samples: List[Sample]) -> dict:
    """Get comprehensive summary statistics for export data."""
    
    if not samples:
        return {"count": 0}
        
    # Basic statistics
    count = len(samples)
    total_time = samples[-1].t - samples[0].t if count > 1 else 0
    total_pulses = samples[-1].pulses - samples[0].pulses if count > 1 else 0
    
    # Force statistics (if available)
    forces = [s.force for s in samples if s.force is not None]
    force_stats = {}
    
    if forces:
        force_stats = {
            "min_force": min(forces),
            "max_force": max(forces), 
            "avg_force": sum(forces) / len(forces),
            "force_samples": len(forces),
            "force_coverage": len(forces) / count * 100  # Percentage
        }
    
    # Derived statistics
    sample_rate = count / total_time if total_time > 0 else 0
    
    return {
        "count": count,
        "total_time_s": total_time,
        "total_pulses": total_pulses,
        "sample_rate_hz": sample_rate,
        **force_stats
    }
```

**Statistics Analysis:**

```python
# Export summary usage and interpretation:

samples = load_measurement_data()  # Example data
summary = DataExporter.get_export_summary(samples)

print(f"Export Summary:")
print(f"  Total samples: {summary['count']:,}")
print(f"  Duration: {summary['total_time_s']:.1f} seconds")
print(f"  Sample rate: {summary['sample_rate_hz']:.1f} Hz")
print(f"  Pulse range: {summary['total_pulses']:,} pulses")

if 'force_coverage' in summary:
    print(f"  Force coverage: {summary['force_coverage']:.1f}%")
    print(f"  Force range: {summary['min_force']:.3f} - {summary['max_force']:.3f} kg")
    print(f"  Average force: {summary['avg_force']:.3f} kg")

# Output example:
# Export Summary:
#   Total samples: 36,000
#   Duration: 360.0 seconds  
#   Sample rate: 100.0 Hz
#   Pulse range: 50,000 pulses
#   Force coverage: 95.2%
#   Force range: 0.120 - 5.670 kg
#   Average force: 2.345 kg
```

**Data Quality Validation:**

```python
def validate_export_data(samples: List[Sample]) -> dict:
    """Validate data quality before export."""
    
    issues = []
    warnings = []
    
    if not samples:
        issues.append("No data to export")
        return {"valid": False, "issues": issues, "warnings": warnings}
    
    # Check for time consistency
    if len(samples) > 1:
        time_diffs = [samples[i].t - samples[i-1].t for i in range(1, len(samples))]
        avg_interval = sum(time_diffs) / len(time_diffs)
        
        # Check for large gaps (>10x average interval)
        large_gaps = [dt for dt in time_diffs if dt > avg_interval * 10]
        if large_gaps:
            warnings.append(f"Found {len(large_gaps)} large time gaps")
    
    # Check pulse count consistency  
    pulse_jumps = []
    for i in range(1, len(samples)):
        delta = abs(samples[i].pulses - samples[i-1].pulses)
        if delta > 10000:  # Unreasonably large jump
            pulse_jumps.append((i, delta))
    
    if pulse_jumps:
        warnings.append(f"Found {len(pulse_jumps)} large pulse jumps")
    
    # Check force data coverage
    force_samples = [s for s in samples if s.force is not None]
    force_coverage = len(force_samples) / len(samples) * 100
    
    if force_coverage < 50:
        warnings.append(f"Low force data coverage: {force_coverage:.1f}%")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "force_coverage": force_coverage,
        "total_samples": len(samples)
    }

# Usage before export:
validation = validate_export_data(samples)
if not validation["valid"]:
    print("Export validation failed:", validation["issues"])
    return False

if validation["warnings"]:
    print("Export warnings:", validation["warnings"])
    # Continue with export but inform user
```

---

## 7. Error Handling & Recovery

### Comprehensive Error Handling

```python
@staticmethod
def export_to_excel_robust(samples: List[Sample], filename: str) -> dict:
    """Robust Excel export with detailed error reporting."""
    
    result = {
        "success": False,
        "error": None,
        "samples_processed": 0,
        "file_size": 0
    }
    
    # Input validation
    if not samples:
        result["error"] = "No data to export"
        return result
    
    if not filename:
        result["error"] = "No filename provided"
        return result
    
    try:
        # Pre-export validation
        validation = validate_export_data(samples)
        if not validation["valid"]:
            result["error"] = f"Data validation failed: {validation['issues']}"
            return result
        
        # Data transformation with progress tracking
        data_rows = []
        for i, sample in enumerate(samples):
            try:
                row = {
                    "time_s": sample.t,
                    "pulses": sample.pulses,
                    "delta": sample.delta,
                    "force_kg": sample.force if sample.force is not None else ""
                }
                data_rows.append(row)
                result["samples_processed"] = i + 1
                
            except Exception as e:
                result["error"] = f"Error processing sample {i}: {e}"
                return result
        
        # DataFrame creation
        df = pd.DataFrame(data_rows)
        
        # Export with error handling
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name=EXCEL_SHEET_NAME)
        
        # Verify file was created
        import os
        if os.path.exists(filename):
            result["file_size"] = os.path.getsize(filename)
            result["success"] = True
        else:
            result["error"] = "File was not created"
        
    except PermissionError:
        result["error"] = f"Permission denied: Cannot write to {filename}"
    except FileNotFoundError:
        result["error"] = f"Invalid path: {filename}"
    except pd.errors.ExcelWriterError as e:
        result["error"] = f"Excel export error: {e}"
    except Exception as e:
        result["error"] = f"Unexpected error: {e}"
    
    return result

# Usage with comprehensive feedback:
export_result = DataExporter.export_to_excel_robust(samples, "data.xlsx")

if export_result["success"]:
    print(f"Export successful: {export_result['samples_processed']} samples")
    print(f"File size: {export_result['file_size']} bytes")
else:
    print(f"Export failed: {export_result['error']}")
```

### Recovery Strategies

```python
class RecoveryExporter:
    """Exporter with automatic recovery strategies."""
    
    @staticmethod
    def export_with_recovery(samples: List[Sample], base_filename: str) -> dict:
        """Export with automatic recovery and fallback options."""
        
        import os
        from pathlib import Path
        
        # Try primary export format
        result = DataExporter.export_to_excel_robust(samples, base_filename)
        
        if result["success"]:
            return result
        
        # Recovery strategy 1: Try alternative filename
        if "Permission denied" in result.get("error", ""):
            alt_filename = f"{Path(base_filename).stem}_backup.xlsx"
            print(f"Trying alternative filename: {alt_filename}")
            
            result = DataExporter.export_to_excel_robust(samples, alt_filename)
            if result["success"]:
                return result
        
        # Recovery strategy 2: Fallback to CSV
        csv_filename = f"{Path(base_filename).stem}.csv"
        print(f"Falling back to CSV format: {csv_filename}")
        
        csv_success = DataExporter.export_to_csv(samples, csv_filename)
        if csv_success:
            return {
                "success": True,
                "format": "csv",
                "filename": csv_filename,
                "note": "Exported as CSV due to Excel export failure"
            }
        
        # Recovery strategy 3: Reduced dataset
        if len(samples) > 10000:
            print("Trying with reduced dataset (every 10th sample)")
            reduced_samples = samples[::10]  # Every 10th sample
            
            result = DataExporter.export_to_excel_robust(reduced_samples, 
                                                        f"{Path(base_filename).stem}_reduced.xlsx")
            if result["success"]:
                result["note"] = "Exported reduced dataset due to size constraints"
                return result
        
        # All recovery strategies failed
        return {
            "success": False,
            "error": "All export strategies failed",
            "attempted_formats": ["xlsx", "csv", "reduced_xlsx"]
        }
```

---

## 8. Professional Export Patterns

### Enterprise Export Framework

```python
class EnterpriseDataExporter:
    """Enterprise-grade exporter with advanced features."""
    
    def __init__(self, config: dict = None):
        self.config = config or self._get_default_config()
        self.export_history = []
        
    def _get_default_config(self) -> dict:
        """Get default export configuration."""
        return {
            "default_format": "xlsx",
            "include_metadata": True,
            "compress_large_files": True,
            "size_threshold_mb": 10,
            "backup_exports": True,
            "progress_callback": None
        }
    
    def export(self, samples: List[Sample], filename: str, 
               format_override: str = None) -> dict:
        """Enterprise export with full feature set."""
        
        start_time = time.time()
        export_format = format_override or self.config["default_format"]
        
        # Pre-export analysis
        analysis = self._analyze_export_requirements(samples, export_format)
        
        # Progress tracking
        progress_callback = self.config.get("progress_callback")
        
        try:
            # Execute export based on analysis
            if analysis["requires_compression"]:
                result = self._export_compressed(samples, filename, export_format, progress_callback)
            elif analysis["requires_chunking"]:
                result = self._export_chunked(samples, filename, export_format, progress_callback)
            else:
                result = self._export_standard(samples, filename, export_format, progress_callback)
            
            # Post-export processing
            if result["success"] and self.config["include_metadata"]:
                self._add_metadata(filename, samples, analysis)
            
            # Record export in history
            export_record = {
                "timestamp": start_time,
                "filename": filename,
                "format": export_format,
                "sample_count": len(samples),
                "duration": time.time() - start_time,
                "success": result["success"]
            }
            self.export_history.append(export_record)
            
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _analyze_export_requirements(self, samples: List[Sample], format: str) -> dict:
        """Analyze data and determine export strategy."""
        
        sample_count = len(samples)
        estimated_size_mb = sample_count * 0.1 / 1024  # Rough estimate
        
        return {
            "sample_count": sample_count,
            "estimated_size_mb": estimated_size_mb,
            "requires_compression": estimated_size_mb > self.config["size_threshold_mb"],
            "requires_chunking": sample_count > 100000,
            "format": format
        }

# Usage:
exporter = EnterpriseDataExporter({
    "include_metadata": True,
    "compress_large_files": True,
    "progress_callback": lambda pct: print(f"Export progress: {pct}%")
})

result = exporter.export(samples, "enterprise_data.xlsx")
```

### Multi-Sheet Excel Export

```python
def export_to_excel_multi_sheet(samples: List[Sample], filename: str) -> bool:
    """Export to Excel with multiple sheets for different data views."""
    
    try:
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            
            # Sheet 1: Raw data
            raw_data = DataTransformer.samples_to_dict_rows(samples)
            df_raw = pd.DataFrame(raw_data)
            df_raw.to_excel(writer, sheet_name='Raw Data', index=False)
            
            # Sheet 2: Summary statistics
            summary = DataExporter.get_export_summary(samples)
            df_summary = pd.DataFrame([summary])
            df_summary.to_excel(writer, sheet_name='Summary', index=False)
            
            # Sheet 3: Force analysis (if force data available)
            force_samples = [s for s in samples if s.force is not None]
            if force_samples:
                force_data = [{"time_s": s.t, "force_kg": s.force} for s in force_samples]
                df_force = pd.DataFrame(force_data)
                df_force.to_excel(writer, sheet_name='Force Analysis', index=False)
            
            # Sheet 4: Velocity analysis
            velocity_data = []
            for i in range(1, len(samples)):
                dt = samples[i].t - samples[i-1].t
                if dt > 0:
                    velocity_rps = samples[i].delta / dt / 2048  # Assuming 2048 PPR encoder
                    velocity_data.append({
                        "time_s": samples[i].t,
                        "velocity_rps": velocity_rps,
                        "velocity_rpm": velocity_rps * 60
                    })
            
            if velocity_data:
                df_velocity = pd.DataFrame(velocity_data)
                df_velocity.to_excel(writer, sheet_name='Velocity Analysis', index=False)
        
        return True
        
    except Exception as e:
        print(f"Multi-sheet export error: {e}")
        return False
```

---

## Συμπέρασμα: Professional Data Export Excellence

Το **data_export.py** module αποδεικνύει τις αρχές **enterprise-grade data export systems**:

### 🎯 **Export Architecture Excellence**
- **Format abstraction** - Clean separation between data και presentation
- **Static method design** - Stateless operations για thread safety
- **Pipeline approach** - Reusable transformation logic
- **Configuration flexibility** - Adaptable to different requirements

### ⚡ **Professional Output Quality**
- **Multi-format support** - Excel για presentation, CSV για analysis
- **Rich metadata** - Comprehensive statistics και data validation
- **Error resilience** - Robust handling of edge cases και failures
- **Recovery strategies** - Automatic fallbacks για reliable operation

### 📊 **Data Transformation Mastery**
- **Type preservation** - Maintains numeric precision where appropriate
- **Unit handling** - Professional formatting με proper units
- **Missing data strategy** - Graceful handling of Optional fields
- **Schema consistency** - Uniform column naming across formats

### 🛡️ **Production Reliability**
- **Input validation** - Comprehensive checking before processing
- **Progress tracking** - User feedback για long-running exports
- **File system safety** - Permission και path validation
- **Memory efficiency** - Streaming approach για large datasets

**Το data_export.py είναι ένα excellent foundation για professional data reporting systems - transforms raw measurement data into polished, analysis-ready formats που meet industry standards για technical documentation και data exchange.** 🎉

**Key Insight:** Professional data export requires sophisticated error handling, multiple format support, και comprehensive validation για reliable operation σε production environments! 🚀
