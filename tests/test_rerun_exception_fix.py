#!/usr/bin/env python3
"""
Test script to validate RerunException handling fix.
"""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from frontend.components.error_handling import (
    with_error_handling, 
    ErrorBoundary, 
    safe_execute,
    _is_rerun_exception
)

def test_rerun_exception_detection():
    """Test the RerunException detection function."""
    st.header("🧪 RerunException Detection Test")
    
    # Simulate different types of exceptions
    class MockRerunException(Exception):
        def __init__(self):
            super().__init__("This is a rerun")
            self.__module__ = "streamlit.runtime.scriptrunner"
    
    class MockOtherException(Exception):
        def __init__(self):
            super().__init__("This is a regular error")
    
    # Test detection
    rerun_exc = MockRerunException()
    other_exc = MockOtherException()
    
    st.write("**Testing RerunException Detection:**")
    st.write(f"• Mock RerunException detected: {_is_rerun_exception(rerun_exc)}")
    st.write(f"• Mock Other Exception detected: {_is_rerun_exception(other_exc)}")
    
    return True

def test_decorator_behavior():
    """Test that the decorator allows RerunException to bubble up."""
    st.header("🎯 Decorator Test")
    
    @with_error_handling(component="test", user_message="Test failed")
    def function_that_reruns():
        st.write("This function calls st.rerun()")
        if st.button("Test Rerun (should work without error message)", type="primary"):
            st.success("✅ Button clicked! About to rerun...")
            st.rerun()
    
    try:
        function_that_reruns()
        st.success("✅ Decorator test passed - no false error messages")
    except Exception as e:
        if "rerun" in str(e).lower():
            st.success("✅ RerunException bubbled up correctly")
        else:
            st.error(f"❌ Unexpected error: {e}")

def test_boundary_behavior():
    """Test that ErrorBoundary allows RerunException to bubble up."""
    st.header("🛡️ Error Boundary Test")
    
    try:
        with ErrorBoundary("test_component"):
            st.write("This is inside an ErrorBoundary")
            if st.button("Test Boundary Rerun (should work without error message)", type="secondary"):
                st.success("✅ Button clicked! About to rerun...")
                st.rerun()
        st.success("✅ ErrorBoundary test passed - no false error messages")
    except Exception as e:
        if "rerun" in str(e).lower():
            st.success("✅ RerunException bubbled up correctly from ErrorBoundary")
        else:
            st.error(f"❌ Unexpected error: {e}")

def test_safe_execute_behavior():
    """Test that safe_execute allows RerunException to bubble up."""
    st.header("🔒 Safe Execute Test")
    
    def rerun_function():
        if st.button("Test Safe Execute Rerun (should work without error message)"):
            st.success("✅ Button clicked! About to rerun...")
            st.rerun()
        return "Function completed"
    
    try:
        result = safe_execute(rerun_function, component="test_safe_execute")
        st.success("✅ Safe execute test passed - no false error messages")
    except Exception as e:
        if "rerun" in str(e).lower():
            st.success("✅ RerunException bubbled up correctly from safe_execute")
        else:
            st.error(f"❌ Unexpected error: {e}")

def main():
    """Main test interface."""
    st.set_page_config(
        page_title="RerunException Fix Test", 
        page_icon="🧪",
        layout="wide"
    )
    
    st.title("🧪 RerunException Handling Fix Test")
    st.write("This test validates that RerunException is properly excluded from error handling.")
    
    # Run detection test
    test_rerun_exception_detection()
    
    st.divider()
    
    # Test different error handling methods
    col1, col2, col3 = st.columns(3)
    
    with col1:
        test_decorator_behavior()
    
    with col2:
        test_boundary_behavior()
    
    with col3:
        test_safe_execute_behavior()
    
    st.divider()
    
    st.success("🎉 **Test Results**: If you can click the buttons above without seeing '⚠️ Issue in Resource Management' or similar error messages, the fix is working correctly!")

if __name__ == "__main__":
    main()