"""
Error Handler Component

Centralized error handling for frontend components with proper
logging, user feedback, and recovery strategies.
"""

import streamlit as st
import logging
from typing import Optional, Dict, Any, Callable
from functools import wraps
import traceback
import time

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Centralized error handling for frontend components."""
    
    def __init__(self):
        self.error_count = 0
        self.last_error_time = None
        self.error_history = []
    
    def handle_error(self, 
                    error: Exception, 
                    context: str = "Unknown", 
                    show_user_message: bool = True,
                    user_message: Optional[str] = None,
                    recovery_action: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Handle an error with proper logging and user feedback.
        
        Args:
            error: The exception that occurred
            context: Context where the error occurred
            show_user_message: Whether to show error to user
            user_message: Custom user message (if None, generates from error)
            recovery_action: Optional recovery action function
            
        Returns:
            Dictionary with error details and recovery status
        """
        self.error_count += 1
        self.last_error_time = time.time()
        
        # Log the error
        error_details = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context,
            'timestamp': self.last_error_time,
            'traceback': traceback.format_exc()
        }
        
        self.error_history.append(error_details)
        logger.error(f"Error in {context}: {str(error)}", exc_info=True)
        
        # Show user message if requested
        if show_user_message:
            if user_message:
                st.error(user_message)
            else:
                self._show_default_error_message(error, context)
        
        # Try recovery action
        recovery_successful = False
        if recovery_action:
            try:
                recovery_action()
                recovery_successful = True
                st.info("✅ Recovery action completed successfully")
            except Exception as recovery_error:
                logger.error(f"Recovery action failed: {str(recovery_error)}")
                st.warning(f"⚠️ Recovery action failed: {str(recovery_error)}")
        
        return {
            'error_handled': True,
            'recovery_successful': recovery_successful,
            'error_details': error_details
        }
    
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
                           user_message: Optional[str] = None):
        """
        Decorator for adding error handling to functions.
        
        Args:
            context: Context description for the function
            fallback_action: Fallback function to call on error
            user_message: Custom error message for users
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
                        recovery_action=fallback_action
                    )
                    
                    # Return fallback result if available
                    if fallback_action and result['recovery_successful']:
                        try:
                            return fallback_action(*args, **kwargs)
                        except Exception as fallback_error:
                            logger.error(f"Fallback action also failed: {str(fallback_error)}")
                    
                    return None
            return wrapper
        return decorator
    
    def show_error_summary(self):
        """Show a summary of recent errors."""
        if not self.error_history:
            st.success("✅ No errors recorded in this session")
            return
        
        st.warning(f"⚠️ {self.error_count} error(s) occurred in this session")
        
        # Show recent errors
        recent_errors = self.error_history[-5:]  # Last 5 errors
        
        for i, error in enumerate(reversed(recent_errors), 1):
            with st.expander(f"Error {i}: {error['error_type']} in {error['context']}"):
                st.code(error['error_message'])
                st.caption(f"Occurred at: {time.ctime(error['timestamp'])}")


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
    
    def update_loading(self, operation_id: str, progress: float, message: Optional[str] = None):
        """Update loading progress for an operation."""
        if operation_id in self.active_operations:
            operation = self.active_operations[operation_id]
            
            if operation.get('progress_bar'):
                # Update progress bar (this would need to be implemented with placeholders)
                pass
            
            if message:
                operation['message'] = message
    
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


# Global instances
_error_handler = None
_loading_manager = None


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


def get_loading_manager() -> LoadingStateManager:
    """Get global loading manager instance."""
    global _loading_manager
    if _loading_manager is None:
        _loading_manager = LoadingStateManager()
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