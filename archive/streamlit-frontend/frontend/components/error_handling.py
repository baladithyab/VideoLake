#!/usr/bin/env python3
"""
Unified Error Handling and Loading Management

Comprehensive error handling, graceful degradation, fallback mechanisms,
and loading state management for the S3Vector application.
"""

import streamlit as st
import traceback
import logging
import time
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
    """Centralized error handling for the S3Vector application."""
    
    def __init__(self):
        self.error_count = 0
        self.last_error_time = None
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
        context: str = "Unknown", 
        show_user_message: bool = True,
        user_message: Optional[str] = None,
        recovery_action: Optional[Callable] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        fallback_func: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Handle an error with proper logging and user feedback.
        
        Args:
            error: The exception that occurred
            context: Context where the error occurred
            show_user_message: Whether to show error to user
            user_message: Custom user message (if None, generates from error)
            recovery_action: Optional recovery action function
            severity: Error severity level
            fallback_func: Optional fallback function
            
        Returns:
            Dictionary with error details and recovery status
        """
        self.error_count += 1
        self.last_error_time = time.time()
        
        # Create error info
        error_info = ErrorInfo(
            error_type=type(error).__name__,
            message=str(error),
            severity=severity,
            component=context,
            fallback_available=fallback_func is not None or recovery_action is not None,
            user_message=user_message,
            technical_details=traceback.format_exc()
        )
        
        # Log error
        self._log_error(error_info)
        
        # Store in history
        self.error_history.append(error_info)
        
        # Show user message if requested
        if show_user_message:
            if user_message:
                self._display_error_message(error_info)
            else:
                self._show_default_error_message(error, context)
        
        # Try recovery action or fallback
        recovery_successful = False
        if recovery_action:
            try:
                recovery_action()
                recovery_successful = True
                st.info("✅ Recovery action completed successfully")
            except Exception as recovery_error:
                logger.error(f"Recovery action failed: {str(recovery_error)}")
                st.warning(f"⚠️ Recovery action failed: {str(recovery_error)}")
        elif fallback_func:
            try:
                result = fallback_func()
                recovery_successful = True
                st.info("🔄 Using fallback solution...")
                return {
                    'error_handled': True,
                    'recovery_successful': recovery_successful,
                    'error_details': error_info.__dict__,
                    'fallback_result': result
                }
            except Exception as fallback_error:
                logger.error(f"Fallback function failed: {str(fallback_error)}")
                st.error(f"🚨 Fallback failed for {context}: {fallback_error}")
        
        return {
            'error_handled': True,
            'recovery_successful': recovery_successful,
            'error_details': error_info.__dict__
        }
    
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
            f"[{error_info.component}] {error_info.error_type}: {error_info.message}",
            exc_info=True
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
    
    def _show_default_error_message(self, error: Exception, context: str):
        """Show a default error message to the user."""
        error_type = type(error).__name__
        
        if "connection" in str(error).lower() or "network" in str(error).lower():
            st.error(f"🌐 **Connection Error in {context}**\n\nUnable to connect to backend services. Please check your network connection and try again.")
        elif "timeout" in str(error).lower():
            st.error(f"⏱️ **Timeout Error in {context}**\n\nThe operation took too long to complete. Please try again with a smaller request.")
        elif "permission" in str(error).lower() or "access" in str(error).lower():
            st.error(f"🔒 **Access Error in {context}**\n\nInsufficient permissions to perform this operation. Please check your credentials.")
        elif "not found" in str(error).lower():
            st.error(f"❌ **Resource Not Found in {context}**\n\nThe requested resource could not be found. Please verify your request.")
        else:
            st.error(f"⚠️ **Error in {context}**\n\n`{error_type}`: {str(error)}")
        
        # Add troubleshooting tips
        with st.expander("🔧 Troubleshooting Tips"):
            st.markdown("""
            **Common Solutions:**
            - Refresh the page and try again
            - Check if backend services are running
            - Verify your AWS credentials and permissions
            - Try with a different query or smaller parameters
            - Check the browser console for additional details
            """)
    
    def with_error_handling(self, 
                           context: str, 
                           fallback_action: Optional[Callable] = None,
                           user_message: Optional[str] = None,
                           severity: ErrorSeverity = ErrorSeverity.MEDIUM):
        """
        Decorator for adding error handling to functions.
        
        Args:
            context: Context description for the function
            fallback_action: Fallback function to call on error
            user_message: Custom error message for users
            severity: Error severity level
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    result = self.handle_error(
                        e, 
                        context=context,
                        user_message=user_message,
                        recovery_action=fallback_action,
                        severity=severity
                    )
                    
                    # Return fallback result if available
                    if fallback_action and result['recovery_successful']:
                        try:
                            return fallback_action(*args, **kwargs)
                        except Exception as fallback_error:
                            logger.error(f"Fallback action also failed: {str(fallback_error)}")
                    
                    return result.get('fallback_result')
            return wrapper
        return decorator
    
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
    
    def show_error_summary(self):
        """Show a summary of recent errors."""
        if not self.error_history:
            st.success("✅ No errors recorded in this session")
            return
        
        st.warning(f"⚠️ {self.error_count} error(s) occurred in this session")
        
        # Show recent errors
        recent_errors = self.error_history[-5:]  # Last 5 errors
        
        for i, error in enumerate(reversed(recent_errors), 1):
            with st.expander(f"Error {i}: {error.error_type} in {error.component}"):
                st.code(error.message)
                st.caption(f"Occurred at: {time.ctime(self.last_error_time) if self.last_error_time else 'Unknown'}")


class LoadingStateManager:
    """Manage loading states and progress indicators."""
    
    def __init__(self):
        self.active_operations = {}
    
    def show_loading(self, 
                    operation_id: str, 
                    message: str = "Loading...",
                    progress_bar: bool = False,
                    estimated_duration: Optional[float] = None):
        """
        Show loading state for an operation.
        
        Args:
            operation_id: Unique ID for the operation
            message: Loading message to display
            progress_bar: Whether to show a progress bar
            estimated_duration: Estimated duration in seconds
        """
        self.active_operations[operation_id] = {
            'start_time': time.time(),
            'message': message,
            'progress_bar': progress_bar,
            'estimated_duration': estimated_duration
        }
        
        # Create UI elements
        if progress_bar:
            progress_placeholder = st.empty()
            message_placeholder = st.empty()
            
            if estimated_duration:
                # Animated progress bar
                for i in range(int(estimated_duration * 10)):
                    progress = min(i / (estimated_duration * 10), 1.0)
                    progress_placeholder.progress(progress)
                    message_placeholder.text(f"{message} ({progress*100:.0f}%)")
                    time.sleep(0.1)
            else:
                progress_placeholder.progress(0.5)
                message_placeholder.text(message)
        else:
            st.spinner(message)
    
    def complete_loading(self, operation_id: str, success: bool = True, message: Optional[str] = None):
        """Complete a loading operation."""
        if operation_id in self.active_operations:
            operation = self.active_operations[operation_id]
            duration = time.time() - operation['start_time']
            
            if success:
                if message:
                    st.success(f"✅ {message} (completed in {duration:.1f}s)")
                else:
                    st.success(f"✅ Operation completed in {duration:.1f}s")
            else:
                if message:
                    st.error(f"❌ {message}")
                else:
                    st.error("❌ Operation failed")
            
            del self.active_operations[operation_id]
    
    def loading_context(self, operation_id: str, message: str = "Processing...", show_progress: bool = True):
        """Context manager for loading states."""
        class LoadingContext:
            def __init__(self, manager, op_id, msg, show_prog):
                self.manager = manager
                self.operation_id = op_id
                self.message = msg
                self.show_progress = show_prog
                self.success = False
            
            def __enter__(self):
                if self.show_progress:
                    self.spinner = st.spinner(self.message)
                    self.spinner.__enter__()
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                if self.show_progress:
                    self.spinner.__exit__(exc_type, exc_val, exc_tb)
                
                if exc_type is None:
                    self.success = True
                
                return False  # Don't suppress exceptions
        
        return LoadingContext(self, operation_id, message, show_progress)


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
        self.error_handler = None  # Will be set to global instance
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Only catch actual errors, not RerunException
            if _is_rerun_exception(exc_val):
                raise  # Let RerunException bubble up
            
            handler = get_error_handler()
            handler.handle_error(
                error=exc_val,
                context=self.component_name,
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
        handler = get_error_handler()
        return handler.handle_error(
            error=e,
            context=component,
            fallback_func=fallback_func
        )


def display_error_dashboard():
    """Display error dashboard for debugging."""
    st.subheader("🐛 Error Dashboard")
    
    handler = get_error_handler()
    summary = handler.get_error_summary()
    
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
        for i, error in enumerate(handler.error_history[-10:]):  # Last 10 errors
            with st.expander(f"Error {i+1}: {error.component} - {error.error_type}"):
                st.write(f"**Message**: {error.message}")
                st.write(f"**Severity**: {error.severity.value}")
                st.write(f"**Fallback Available**: {error.fallback_available}")
                if error.technical_details:
                    st.code(error.technical_details)


def _is_rerun_exception(exception: Exception) -> bool:
    """Check if an exception is a Streamlit rerun exception."""
    return (
        hasattr(exception, '__class__') and
        exception.__class__.__name__ == 'RerunException'
    )


# Global instances
_error_handler = ErrorHandler()
_loading_manager = LoadingStateManager()


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance."""
    return _error_handler


def get_loading_manager() -> LoadingStateManager:
    """Get global loading manager instance."""
    return _loading_manager


def handle_error(error: Exception, 
                context: str = "Unknown",
                show_user_message: bool = True,
                user_message: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function for handling errors."""
    handler = get_error_handler()
    return handler.handle_error(error, context, show_user_message, user_message)


def with_loading(operation_id: str, message: str = "Processing...", show_progress: bool = True):
    """Convenience decorator for loading states."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            manager = get_loading_manager()
            with manager.loading_context(operation_id, message, show_progress):
                return func(*args, **kwargs)
        return wrapper
    return decorator


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
                handler = get_error_handler()
                return handler.handle_error(
                    error=e,
                    context=component,
                    severity=severity,
                    fallback_func=fallback_func,
                    user_message=user_message
                )
        return wrapper
    return decorator


# Example usage functions for reference
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
