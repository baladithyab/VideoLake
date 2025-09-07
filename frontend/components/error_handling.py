#!/usr/bin/env python3
"""
Error Handling and Fallback Components

Comprehensive error handling, graceful degradation, and fallback mechanisms
for the S3Vector unified demo.
"""

import streamlit as st
import traceback
import logging
from typing import Any, Callable, Dict, Optional, Union
from functools import wraps
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorInfo:
    """Error information container."""
    error_type: str
    message: str
    severity: ErrorSeverity
    component: str
    fallback_available: bool = False
    user_message: Optional[str] = None
    technical_details: Optional[str] = None


class ErrorHandler:
    """Centralized error handling for the demo."""
    
    def __init__(self):
        self.error_history = []
        self.fallback_modes = {
            'visualization': True,
            'video_player': True,
            'search': True,
            'processing': True
        }
    
    def handle_error(
        self, 
        error: Exception, 
        component: str, 
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        fallback_func: Optional[Callable] = None,
        user_message: Optional[str] = None
    ) -> Any:
        """Handle an error with appropriate fallback."""
        
        error_info = ErrorInfo(
            error_type=type(error).__name__,
            message=str(error),
            severity=severity,
            component=component,
            fallback_available=fallback_func is not None,
            user_message=user_message,
            technical_details=traceback.format_exc()
        )
        
        # Log error
        self._log_error(error_info)
        
        # Store in history
        self.error_history.append(error_info)
        
        # Display user-friendly message
        self._display_error_message(error_info)
        
        # Execute fallback if available
        if fallback_func:
            try:
                return fallback_func()
            except Exception as fallback_error:
                self._handle_fallback_failure(fallback_error, component)
        
        return None
    
    def _log_error(self, error_info: ErrorInfo):
        """Log error information."""
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }.get(error_info.severity, logging.WARNING)
        
        logger.log(
            log_level,
            f"[{error_info.component}] {error_info.error_type}: {error_info.message}"
        )
    
    def _display_error_message(self, error_info: ErrorInfo):
        """Display user-friendly error message."""
        if error_info.severity == ErrorSeverity.CRITICAL:
            st.error(f"🚨 Critical Error in {error_info.component}")
            st.error(error_info.user_message or error_info.message)
        elif error_info.severity == ErrorSeverity.HIGH:
            st.error(f"❌ Error in {error_info.component}")
            st.error(error_info.user_message or error_info.message)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            st.warning(f"⚠️ Issue in {error_info.component}")
            st.warning(error_info.user_message or error_info.message)
        else:
            st.info(f"ℹ️ Notice in {error_info.component}")
            st.info(error_info.user_message or error_info.message)
        
        # Show fallback availability
        if error_info.fallback_available:
            st.info("🔄 Attempting fallback solution...")
    
    def _handle_fallback_failure(self, error: Exception, component: str):
        """Handle fallback failure."""
        st.error(f"🚨 Fallback failed for {component}: {error}")
        st.error("Please try refreshing the page or contact support.")
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of errors encountered."""
        if not self.error_history:
            return {"total_errors": 0, "by_severity": {}, "by_component": {}}
        
        by_severity = {}
        by_component = {}
        
        for error in self.error_history:
            # Count by severity
            severity_key = error.severity.value
            by_severity[severity_key] = by_severity.get(severity_key, 0) + 1
            
            # Count by component
            by_component[error.component] = by_component.get(error.component, 0) + 1
        
        return {
            "total_errors": len(self.error_history),
            "by_severity": by_severity,
            "by_component": by_component
        }


# Global error handler instance
_error_handler = ErrorHandler()


def with_error_handling(
    component: str,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    fallback_func: Optional[Callable] = None,
    user_message: Optional[str] = None
):
    """Decorator for adding error handling to functions."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                return _error_handler.handle_error(
                    error=e,
                    component=component,
                    severity=severity,
                    fallback_func=fallback_func,
                    user_message=user_message
                )
        return wrapper
    return decorator


class FallbackComponents:
    """Fallback implementations for when main components fail."""
    
    @staticmethod
    def fallback_visualization():
        """Fallback visualization when main viz fails."""
        st.info("📊 Visualization temporarily unavailable")
        st.write("**Fallback Mode**: Showing text-based results")
        
        # Simple text-based visualization
        st.write("```")
        st.write("Query Embedding: [1024-dim vector]")
        st.write("Result Embeddings: [10 x 1024-dim vectors]")
        st.write("Similarity Scores: [0.85, 0.82, 0.79, 0.76, 0.73, ...]")
        st.write("```")
    
    @staticmethod
    def fallback_video_player():
        """Fallback video player when main player fails."""
        st.info("🎬 Video player temporarily unavailable")
        st.write("**Fallback Mode**: Showing segment information")
        
        # Simple segment list
        segments = [
            {"time": "0:00-0:05", "score": 0.85, "type": "visual-text"},
            {"time": "0:05-0:10", "score": 0.82, "type": "visual-image"},
            {"time": "0:10-0:15", "score": 0.79, "type": "audio"}
        ]
        
        for i, seg in enumerate(segments):
            st.write(f"**Segment {i+1}**: {seg['time']} - Score: {seg['score']:.2f} ({seg['type']})")
    
    @staticmethod
    def fallback_search():
        """Fallback search when main search fails."""
        st.info("🔍 Search temporarily unavailable")
        st.write("**Fallback Mode**: Showing cached results")
        
        # Mock results
        st.write("**Sample Results:**")
        for i in range(3):
            st.write(f"- Result {i+1}: Similarity {0.8 - i*0.1:.1f}")
    
    @staticmethod
    def fallback_processing():
        """Fallback processing when main processing fails."""
        st.info("⚙️ Processing temporarily unavailable")
        st.write("**Fallback Mode**: Simulation only")
        
        st.write("**Simulated Processing Results:**")
        st.write("- Video uploaded successfully")
        st.write("- Embeddings generated (simulated)")
        st.write("- Storage completed (simulated)")


class ErrorBoundary:
    """Error boundary component for wrapping UI sections."""
    
    def __init__(self, component_name: str):
        self.component_name = component_name
        self.error_handler = _error_handler
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.error_handler.handle_error(
                error=exc_val,
                component=self.component_name,
                severity=ErrorSeverity.MEDIUM,
                user_message=f"An error occurred in {self.component_name}. Using fallback mode."
            )
            return True  # Suppress the exception
        return False


def safe_execute(func: Callable, fallback_func: Optional[Callable] = None, component: str = "unknown") -> Any:
    """Safely execute a function with error handling."""
    try:
        return func()
    except Exception as e:
        return _error_handler.handle_error(
            error=e,
            component=component,
            fallback_func=fallback_func
        )


def display_error_dashboard():
    """Display error dashboard for debugging."""
    st.subheader("🐛 Error Dashboard")
    
    summary = _error_handler.get_error_summary()
    
    if summary["total_errors"] == 0:
        st.success("✅ No errors encountered")
        return
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Errors", summary["total_errors"])
    
    with col2:
        if summary["by_severity"]:
            highest_severity = max(summary["by_severity"].keys())
            st.metric("Highest Severity", highest_severity.title())
    
    with col3:
        if summary["by_component"]:
            most_errors = max(summary["by_component"], key=summary["by_component"].get)
            st.metric("Most Errors", f"{most_errors} ({summary['by_component'][most_errors]})")
    
    # Error details
    if st.checkbox("Show Error Details"):
        for i, error in enumerate(_error_handler.error_history[-10:]):  # Last 10 errors
            with st.expander(f"Error {i+1}: {error.component} - {error.error_type}"):
                st.write(f"**Message**: {error.message}")
                st.write(f"**Severity**: {error.severity.value}")
                st.write(f"**Fallback Available**: {error.fallback_available}")
                if error.technical_details:
                    st.code(error.technical_details)


# Example usage functions
def example_with_decorator():
    """Example of using the error handling decorator."""
    
    @with_error_handling(
        component="example",
        severity=ErrorSeverity.MEDIUM,
        fallback_func=lambda: "Fallback result",
        user_message="Example function failed, using fallback"
    )
    def risky_function():
        # This might fail
        raise ValueError("Example error")
    
    return risky_function()


def example_with_boundary():
    """Example of using error boundary."""
    
    with ErrorBoundary("example_component"):
        # This code is protected by error boundary
        st.write("This might fail...")
        raise RuntimeError("Example boundary error")


def _is_rerun_exception(exception: Exception) -> bool:
    """Check if an exception is a Streamlit rerun exception."""
    return (
        hasattr(exception, '__class__') and
        exception.__class__.__name__ == 'RerunException'
    )


# Export the global error handler for use in other components
def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    return _error_handler
