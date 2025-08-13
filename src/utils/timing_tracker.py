"""
Performance Timing Tracker

Utility class for tracking and reporting detailed performance metrics
across video processing, embedding generation, and search operations.
"""

import time
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from contextlib import contextmanager
from datetime import datetime

@dataclass
class TimingEntry:
    """Individual timing measurement."""
    operation: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def finish(self, **metadata):
        """Mark timing entry as finished."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.metadata.update(metadata)
        return self.duration_ms

@dataclass 
class TimingReport:
    """Complete timing report for an operation."""
    operation_id: str
    operation_type: str
    total_duration_ms: float
    timings: List[TimingEntry] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'operation_id': self.operation_id,
            'operation_type': self.operation_type, 
            'total_duration_ms': self.total_duration_ms,
            'timestamp': self.timestamp,
            'metadata': self.metadata,
            'timings': [
                {
                    'operation': entry.operation,
                    'duration_ms': entry.duration_ms,
                    'metadata': entry.metadata
                }
                for entry in self.timings if entry.duration_ms is not None
            ]
        }
    
    def format_summary(self) -> str:
        """Format timing report as readable summary."""
        lines = [
            f"## ⏱️ Performance Timing Report",
            f"**Operation**: {self.operation_type}",
            f"**Total Duration**: {self.total_duration_ms:.1f}ms ({self.total_duration_ms/1000:.2f}s)",
            f"**Timestamp**: {self.timestamp}",
            ""
        ]
        
        if self.metadata:
            lines.append("**Operation Metadata**:")
            for key, value in self.metadata.items():
                lines.append(f"- **{key.replace('_', ' ').title()}**: {value}")
            lines.append("")
        
        if self.timings:
            lines.append("**Detailed Breakdown**:")
            for entry in sorted(self.timings, key=lambda x: x.duration_ms or 0, reverse=True):
                if entry.duration_ms is not None:
                    percentage = (entry.duration_ms / self.total_duration_ms) * 100
                    lines.append(f"- **{entry.operation}**: {entry.duration_ms:.1f}ms ({percentage:.1f}%)")
                    
                    # Add metadata if available
                    if entry.metadata:
                        for key, value in entry.metadata.items():
                            lines.append(f"  - {key.replace('_', ' ').title()}: {value}")
            lines.append("")
        
        # Performance insights
        lines.extend(self._generate_insights())
        
        return "\n".join(lines)
    
    def _generate_insights(self) -> List[str]:
        """Generate performance insights based on timing data."""
        insights = ["**🔍 Performance Insights**:"]
        
        if not self.timings:
            insights.append("- No detailed timing data available")
            return insights
        
        # Find slowest operation
        slowest = max(self.timings, key=lambda x: x.duration_ms or 0)
        if slowest.duration_ms:
            slowest_percentage = (slowest.duration_ms / self.total_duration_ms) * 100
            insights.append(f"- **Bottleneck**: {slowest.operation} ({slowest_percentage:.1f}% of total time)")
        
        # Embedding vs storage analysis
        embedding_time = sum(entry.duration_ms or 0 for entry in self.timings 
                            if 'embedding' in entry.operation.lower())
        storage_time = sum(entry.duration_ms or 0 for entry in self.timings 
                          if any(word in entry.operation.lower() for word in ['storage', 'upload', 'store']))
        
        if embedding_time > 0 and storage_time > 0:
            insights.append(f"- **Embedding Time**: {embedding_time:.1f}ms vs **Storage Time**: {storage_time:.1f}ms")
            if embedding_time > storage_time * 2:
                insights.append("  - Embedding generation is the primary time consumer")
            elif storage_time > embedding_time * 2:
                insights.append("  - Storage operations are the primary time consumer")
            else:
                insights.append("  - Well-balanced embedding/storage performance")
        
        # Speed insights
        if self.total_duration_ms < 1000:
            insights.append("- **Speed**: Excellent performance (sub-second)")
        elif self.total_duration_ms < 5000:
            insights.append("- **Speed**: Good performance (under 5s)")
        elif self.total_duration_ms < 15000:
            insights.append("- **Speed**: Moderate performance (5-15s)")
        else:
            insights.append("- **Speed**: Slow performance (>15s) - consider optimization")
        
        return insights


class TimingTracker:
    """Performance timing tracker for detailed operation analysis."""
    
    def __init__(self, operation_type: str, operation_id: Optional[str] = None):
        """Initialize timing tracker."""
        self.operation_type = operation_type
        self.operation_id = operation_id or f"{operation_type}_{int(time.time()*1000)}"
        self.start_time = time.time()
        self.end_time = None
        self.timings: List[TimingEntry] = []
        self.metadata: Dict[str, Any] = {}
        self.active_entries: Dict[str, TimingEntry] = {}
    
    @contextmanager
    def time_operation(self, operation_name: str, **metadata):
        """Context manager for timing a specific operation."""
        entry = TimingEntry(
            operation=operation_name,
            start_time=time.time(),
            metadata=metadata
        )
        self.active_entries[operation_name] = entry
        
        try:
            yield entry
        finally:
            duration = entry.finish()
            self.timings.append(entry)
            if operation_name in self.active_entries:
                del self.active_entries[operation_name]
    
    def start_operation(self, operation_name: str, **metadata) -> TimingEntry:
        """Start timing an operation manually."""
        entry = TimingEntry(
            operation=operation_name,
            start_time=time.time(),
            metadata=metadata
        )
        self.active_entries[operation_name] = entry
        return entry
    
    def finish_operation(self, operation_name: str, **additional_metadata) -> float:
        """Finish timing an operation manually."""
        if operation_name in self.active_entries:
            entry = self.active_entries[operation_name]
            duration = entry.finish(**additional_metadata)
            self.timings.append(entry)
            del self.active_entries[operation_name]
            return duration
        return 0.0
    
    def add_metadata(self, **metadata):
        """Add metadata to the overall operation."""
        self.metadata.update(metadata)
    
    def finish(self) -> TimingReport:
        """Finish timing tracking and generate report."""
        self.end_time = time.time()
        total_duration = (self.end_time - self.start_time) * 1000
        
        # Finish any active entries
        for operation_name in list(self.active_entries.keys()):
            self.finish_operation(operation_name, incomplete=True)
        
        return TimingReport(
            operation_id=self.operation_id,
            operation_type=self.operation_type,
            total_duration_ms=total_duration,
            timings=self.timings.copy(),
            metadata=self.metadata.copy()
        )
    
    def get_current_duration(self) -> float:
        """Get current duration in milliseconds."""
        return (time.time() - self.start_time) * 1000
    
    def get_summary(self) -> str:
        """Get current timing summary."""
        current_duration = self.get_current_duration()
        
        summary = f"**Current Operation**: {self.operation_type}\n"
        summary += f"**Running Time**: {current_duration:.1f}ms\n"
        summary += f"**Completed Steps**: {len(self.timings)}\n"
        
        if self.active_entries:
            summary += f"**Active Operations**: {', '.join(self.active_entries.keys())}\n"
        
        if self.timings:
            total_completed = sum(entry.duration_ms or 0 for entry in self.timings)
            summary += f"**Completed Time**: {total_completed:.1f}ms\n"
        
        return summary


# Convenience decorators and context managers
@contextmanager
def time_video_processing(operation_id: Optional[str] = None):
    """Context manager for timing video processing operations."""
    tracker = TimingTracker("video_processing", operation_id)
    try:
        yield tracker
    finally:
        report = tracker.finish()
        # Could log or store the report here if needed
        return report

@contextmanager  
def time_search_operation(operation_id: Optional[str] = None):
    """Context manager for timing search operations."""
    tracker = TimingTracker("search_operation", operation_id)
    try:
        yield tracker
    finally:
        report = tracker.finish()
        return report

@contextmanager
def time_embedding_generation(operation_id: Optional[str] = None):
    """Context manager for timing embedding generation."""
    tracker = TimingTracker("embedding_generation", operation_id)
    try:
        yield tracker  
    finally:
        report = tracker.finish()
        return report