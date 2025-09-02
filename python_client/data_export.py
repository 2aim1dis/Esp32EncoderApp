"""
Data export functionality for the Encoder GUI.
Handles exporting measurement data to various formats.
"""

import pandas as pd
from typing import List
from data_models import Sample
from config import DEFAULT_EXPORT_EXTENSION, EXCEL_SHEET_NAME


class DataExporter:
    """Handles exporting measurement data to various formats."""
    
    @staticmethod
    def export_to_excel(samples: List[Sample], filename: str) -> bool:
        """
        Export samples to Excel format.
        
        Args:
            samples: List of Sample objects to export
            filename: Output filename
            
        Returns:
            True if export successful, False otherwise
        """
        if not samples:
            return False
            
        try:
            # Convert samples to dictionary format
            data_rows = []
            for sample in samples:
                row = {
                    "time_s": sample.t,
                    "pulses": sample.pulses,
                    "delta": sample.delta,
                    "force_kg": sample.force if sample.force is not None else ""
                }
                data_rows.append(row)
            
            # Create DataFrame and export
            df = pd.DataFrame(data_rows)
            
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name=EXCEL_SHEET_NAME)
                
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def export_to_csv(samples: List[Sample], filename: str) -> bool:
        """
        Export samples to CSV format.
        
        Args:
            samples: List of Sample objects to export
            filename: Output filename
            
        Returns:
            True if export successful, False otherwise
        """
        if not samples:
            return False
            
        try:
            # Convert samples to dictionary format
            data_rows = []
            for sample in samples:
                row = {
                    "time_s": sample.t,
                    "pulses": sample.pulses,
                    "delta": sample.delta,
                    "force_kg": sample.force if sample.force is not None else ""
                }
                data_rows.append(row)
            
            # Create DataFrame and export
            df = pd.DataFrame(data_rows)
            df.to_csv(filename, index=False)
            
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def get_export_summary(samples: List[Sample]) -> dict:
        """
        Get summary statistics for the data to be exported.
        
        Args:
            samples: List of Sample objects
            
        Returns:
            Dictionary with summary statistics
        """
        if not samples:
            return {"count": 0}
            
        total_time = samples[-1].t - samples[0].t if len(samples) > 1 else 0
        total_pulses = samples[-1].pulses - samples[0].pulses if len(samples) > 1 else 0
        
        # Calculate force statistics if available
        forces = [s.force for s in samples if s.force is not None]
        force_stats = {}
        if forces:
            force_stats = {
                "min_force": min(forces),
                "max_force": max(forces),
                "avg_force": sum(forces) / len(forces)
            }
        
        return {
            "count": len(samples),
            "total_time_s": total_time,
            "total_pulses": total_pulses,
            "sample_rate_hz": len(samples) / total_time if total_time > 0 else 0,
            **force_stats
        }
