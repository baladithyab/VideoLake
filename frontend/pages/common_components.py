"""
Common Components for Frontend Pages

Shared functionality, preview capabilities, and utility components
used across multiple demo pages.
"""

import os
import sys
import tempfile
import requests
import json
from typing import Tuple, Optional, Any, Dict, List
from pathlib import Path
import logging

import gradio as gr
import cv2
import numpy as np
from PIL import Image

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.config import config_manager
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

class CommonComponents:
    """Shared components and utilities for all demo pages."""
    
    # Sample Creative Commons videos for demos
    SAMPLE_VIDEOS = {
        "short_action": {
            "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
            "name": "ForBiggerBlazes.mp4",
            "description": "15-second action sequence - fast cars and blazing scenes",
            "duration": 15,
            "content_type": "action",
            "keywords": ["cars", "action", "speed", "urban"]
        },
        "animation": {
            "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4", 
            "name": "BigBuckBunny.mp4",
            "description": "Creative Commons animated adventure - comedy with characters",
            "duration": 60,
            "content_type": "animation",
            "keywords": ["animation", "comedy", "characters", "adventure"]
        },
        "outdoor_adventure": {
            "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4",
            "name": "ForBiggerJoyrides.mp4", 
            "description": "15-second outdoor adventure - scenic drives and nature",
            "duration": 15,
            "content_type": "adventure",
            "keywords": ["outdoor", "adventure", "nature", "scenic"]
        }
    }
    
    # Sample text descriptions for cross-modal search
    SAMPLE_TEXT_DESCRIPTIONS = [
        {
            "text": "High-speed car chase through city streets with dramatic lighting",
            "category": "action",
            "keywords": ["cars", "chase", "city", "speed"],
            "matches_video": "short_action"
        },
        {
            "text": "Animated characters embarking on a whimsical adventure",
            "category": "animation", 
            "keywords": ["animation", "characters", "adventure", "comedy"],
            "matches_video": "animation"
        },
        {
            "text": "Peaceful outdoor journey through beautiful natural landscapes",
            "category": "nature",
            "keywords": ["outdoor", "nature", "peaceful", "scenic"],
            "matches_video": "outdoor_adventure"
        },
        {
            "text": "Urban action scene with fast-moving vehicles and excitement",
            "category": "action",
            "keywords": ["urban", "action", "vehicles", "excitement"],
            "matches_video": "short_action"
        },
        {
            "text": "Colorful animated world with playful characters and storytelling",
            "category": "animation",
            "keywords": ["colorful", "animated", "playful", "storytelling"],
            "matches_video": "animation"
        }
    ]
    
    @staticmethod
    def create_video_preview(video_path: Optional[str]) -> Tuple[Optional[str], str]:
        """
        Create video preview with thumbnail and basic info.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Tuple of (thumbnail_path, video_info_text)
        """
        if not video_path or not os.path.exists(video_path):
            return None, "No video selected"
        
        try:
            # Get video info using OpenCV
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                return None, "Failed to open video file"
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            file_size = os.path.getsize(video_path)
            
            # Generate thumbnail from middle frame
            thumbnail_path = None
            try:
                # Seek to middle of video
                middle_frame = frame_count // 2
                cap.set(cv2.CAP_PROP_POS_FRAMES, middle_frame)
                
                ret, frame = cap.read()
                if ret:
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Create PIL image
                    pil_image = Image.fromarray(frame_rgb)
                    
                    # Resize for thumbnail (max 400x300)
                    pil_image.thumbnail((400, 300), Image.Resampling.LANCZOS)
                    
                    # Save thumbnail
                    thumbnail_path = tempfile.mktemp(suffix='.png')
                    pil_image.save(thumbnail_path)
                    
            except Exception as thumb_error:
                logger.warning(f"Failed to generate thumbnail: {thumb_error}")
            finally:
                cap.release()
            
            # Create info text
            info_text = f"""**Video Information:**
- **Filename**: {os.path.basename(video_path)}
- **Duration**: {duration:.1f} seconds
- **Resolution**: {width}x{height}
- **Frame Rate**: {fps:.1f} FPS
- **Total Frames**: {frame_count:,}
- **File Size**: {file_size / (1024*1024):.1f} MB
- **Estimated Segments** (5s): {max(1, int(duration / 5))}
"""
            
            return thumbnail_path, info_text
            
        except Exception as e:
            logger.error(f"Video preview failed: {e}")
            return None, f"Error reading video: {str(e)}"
    
    @staticmethod
    def download_sample_video(video_key: str, progress_callback=None) -> Tuple[str, str, str]:
        """
        Download a sample video and return path with preview.
        
        Args:
            video_key: Key from SAMPLE_VIDEOS
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple of (status, message, video_path)
        """
        if video_key not in CommonComponents.SAMPLE_VIDEOS:
            return "❌ Error", "Invalid video selection", ""
        
        video_info = CommonComponents.SAMPLE_VIDEOS[video_key]
        
        try:
            # Create temp directory
            temp_dir = tempfile.mkdtemp(prefix="s3vector_samples_")
            video_path = os.path.join(temp_dir, video_info["name"])
            
            logger.info(f"Downloading {video_info['name']} from {video_info['url']}")
            
            # Download with progress
            response = requests.get(video_info["url"], stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(video_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Call progress callback if provided
                        if progress_callback and total_size > 0:
                            progress = (downloaded / total_size) * 100
                            progress_callback(f"Downloading: {progress:.1f}%")
            
            # Verify download
            if not os.path.exists(video_path) or os.path.getsize(video_path) == 0:
                return "❌ Error", "Download failed - empty file", ""
            
            result_msg = f"""✅ **Download Complete!**

**Video Details:**
- **Name**: {video_info['name']}
- **Description**: {video_info['description']}
- **Content Type**: {video_info['content_type']}
- **Duration**: ~{video_info['duration']} seconds
- **Keywords**: {', '.join(video_info['keywords'])}
- **File Size**: {os.path.getsize(video_path):,} bytes
- **Local Path**: {video_path}

Ready for processing or preview!"""
            
            return "✅ Download Complete", result_msg, video_path
            
        except Exception as e:
            logger.error(f"Sample video download failed: {e}")
            return "❌ Download Failed", f"Error downloading video: {str(e)}", ""
    
    @staticmethod
    def create_text_preview(text: str, metadata: Optional[Dict] = None) -> str:
        """
        Create a formatted preview of text content.
        
        Args:
            text: Text content to preview
            metadata: Optional metadata dictionary
            
        Returns:
            Formatted preview text
        """
        if not text:
            return "No text content provided"
        
        preview = f"**Text Content Preview:**\n\n"
        preview += f"*\"{text}\"*\n\n"
        
        if metadata:
            preview += "**Metadata:**\n"
            for key, value in metadata.items():
                if isinstance(value, list):
                    preview += f"- **{key.title()}**: {', '.join(map(str, value))}\n"
                else:
                    preview += f"- **{key.title()}**: {value}\n"
            preview += "\n"
        
        # Add text statistics
        word_count = len(text.split())
        char_count = len(text)
        
        preview += "**Statistics:**\n"
        preview += f"- **Words**: {word_count}\n"
        preview += f"- **Characters**: {char_count}\n"
        preview += f"- **Estimated embedding tokens**: ~{max(1, word_count // 4)}\n"
        
        return preview
    
    @staticmethod
    def create_custom_data_input() -> Tuple[gr.components.Component, ...]:
        """
        Create custom data input components for user-provided content.
        
        Returns:
            Tuple of Gradio components for custom input
        """
        with gr.Accordion("🔧 Custom Data Input", open=False):
            gr.Markdown("""
            **Provide your own content for testing:**
            - Upload custom videos (MP4 format recommended)
            - Enter custom text descriptions
            - Set custom metadata and parameters
            """)
            
            # Custom video upload
            custom_video = gr.File(
                label="Upload Custom Video",
                file_types=[".mp4", ".mov", ".avi", ".mkv"],
                file_count="single"
            )
            
            # Custom text input
            custom_text = gr.Textbox(
                label="Custom Text Description",
                placeholder="Enter your own text description for cross-modal search...",
                lines=3,
                max_lines=5
            )
            
            # Custom metadata
            with gr.Row():
                custom_category = gr.Textbox(
                    label="Category",
                    placeholder="e.g., action, comedy, documentary",
                    scale=1
                )
                custom_keywords = gr.Textbox(
                    label="Keywords (comma-separated)",
                    placeholder="e.g., cars, chase, urban, speed",
                    scale=2
                )
            
            # Processing parameters
            with gr.Row():
                custom_segment_duration = gr.Slider(
                    label="Segment Duration (seconds)",
                    minimum=2,
                    maximum=30,
                    value=5,
                    step=1
                )
                custom_max_segments = gr.Slider(
                    label="Max Segments",
                    minimum=1,
                    maximum=100,
                    value=20,
                    step=1
                )
        
        return (custom_video, custom_text, custom_category, 
                custom_keywords, custom_segment_duration, custom_max_segments)
    
    @staticmethod
    def create_status_display() -> Tuple[gr.components.Component, ...]:
        """
        Create standardized status display components.
        
        Returns:
            Tuple of status components
        """
        with gr.Row():
            status_indicator = gr.Textbox(
                label="Status",
                interactive=False,
                scale=1
            )
            progress_info = gr.Textbox(
                label="Progress",
                interactive=False,
                scale=2
            )
        
        return status_indicator, progress_info
    
    @staticmethod
    def create_results_display() -> gr.components.Component:
        """
        Create standardized results display component with markdown rendering.
        
        Returns:
            Results display component that renders markdown
        """
        return gr.Markdown(
            value="*Results will appear here...*",
            label="Results"
        )
    
    @staticmethod
    def format_text_for_markdown(text: str) -> str:
        """
        Format text for proper markdown rendering.
        
        Args:
            text: Raw text that may contain escaped newlines
            
        Returns:
            Text formatted for markdown display
        """
        if not text:
            return text
            
        # Convert escaped newlines to proper line breaks for markdown
        formatted_text = text.replace('\\n', '\n')
        
        # Handle double-escaped newlines that might come from JSON or string representations
        formatted_text = formatted_text.replace('\\\\n', '\n')
        
        # Ensure proper markdown formatting
        # Replace multiple consecutive newlines with proper spacing (max 2 newlines)
        import re
        formatted_text = re.sub(r'\n{3,}', '\n\n', formatted_text)
        
        # Convert single newlines within sentences to double newlines for proper markdown breaks
        # But preserve intentional double newlines
        lines = formatted_text.split('\n')
        result_lines = []
        
        for i, line in enumerate(lines):
            result_lines.append(line)
            # Add an extra newline after lines that end with certain characters for better markdown formatting
            if line.strip() and i < len(lines) - 1 and lines[i+1].strip():
                # If current line ends with these characters, it's likely end of a section
                if line.rstrip().endswith((':', '**', '*')):
                    continue
                # For lines that don't end with punctuation, add extra spacing
                if not line.rstrip().endswith(('.', '!', '?', ':', ';', ')', ']', '}')):
                    result_lines.append('')  # Add empty line for spacing
        
        return '\n'.join(result_lines)
    
    @staticmethod
    def format_cost_info(costs: Dict[str, float]) -> str:
        """
        Format cost information for display.
        
        Args:
            costs: Dictionary of cost categories and amounts
            
        Returns:
            Formatted cost information string
        """
        total_cost = sum(costs.values())
        
        cost_info = "**💰 Cost Breakdown:**\n\n"
        
        for category, amount in costs.items():
            category_name = category.replace('_', ' ').title()
            cost_info += f"- **{category_name}**: ${amount:.4f}\n"
        
        cost_info += f"\n**Total Session Cost**: ${total_cost:.4f}\n\n"
        
        # Add cost comparison
        traditional_cost = total_cost * 10  # Assume 10x more expensive
        savings = traditional_cost - total_cost
        
        cost_info += "**💡 Cost Comparison:**\n"
        cost_info += f"- **S3 Vector Solution**: ${total_cost:.4f}\n"
        cost_info += f"- **Traditional Vector DB**: ~${traditional_cost:.4f}\n" 
        cost_info += f"- **Your Savings**: ${savings:.4f} (90% less!)\n"
        
        return cost_info
    
    @staticmethod
    def get_sample_queries_by_category(category: str) -> List[str]:
        """
        Get sample search queries for a specific category.
        
        Args:
            category: Content category
            
        Returns:
            List of sample query strings
        """
        queries_by_category = {
            "action": [
                "Find high-speed car chase scenes",
                "Show me urban action sequences",
                "Locate dramatic chase scenes with vehicles",
                "Search for fast-paced action with cars"
            ],
            "animation": [
                "Find animated characters on adventures",
                "Show me colorful cartoon scenes",
                "Search for comedy animation with characters",
                "Locate animated storytelling sequences"
            ],
            "adventure": [
                "Find outdoor adventure scenes",
                "Show me scenic nature footage",
                "Search for peaceful outdoor journeys",
                "Locate beautiful landscape sequences"
            ],
            "general": [
                "Find exciting action sequences",
                "Show me character-driven scenes", 
                "Search for beautiful outdoor footage",
                "Locate dramatic moments with emotion"
            ]
        }
        
        return queries_by_category.get(category, queries_by_category["general"])
    
    @staticmethod
    def validate_video_file(file_path: str) -> Tuple[bool, str]:
        """
        Validate video file for processing.
        
        Args:
            file_path: Path to video file
            
        Returns:
            Tuple of (is_valid, message)
        """
        if not file_path or not os.path.exists(file_path):
            return False, "Video file does not exist"
        
        try:
            # Check file size (limit to 100MB for demo)
            file_size = os.path.getsize(file_path)
            if file_size > 100 * 1024 * 1024:  # 100MB
                return False, f"Video file too large: {file_size / (1024*1024):.1f}MB (max: 100MB)"
            
            if file_size < 1024:  # 1KB minimum
                return False, "Video file too small (corrupted?)"
            
            # Try to open with OpenCV
            cap = cv2.VideoCapture(file_path)
            if not cap.isOpened():
                return False, "Cannot open video file - unsupported format?"
            
            # Check basic properties
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = frame_count / fps if fps > 0 else 0
            
            cap.release()
            
            if frame_count < 10:
                return False, "Video too short (needs at least 10 frames)"
            
            if duration > 600:  # 10 minutes max
                return False, f"Video too long: {duration:.1f}s (max: 600s)"
            
            return True, f"Valid video: {duration:.1f}s, {frame_count} frames"
            
        except Exception as e:
            return False, f"Video validation failed: {str(e)}"