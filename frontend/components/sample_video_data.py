#!/usr/bin/env python3
"""
Sample Video Data Module

This module contains the sample video data provided by Google's sample video collection
and provides utilities for managing and selecting sample videos for processing.
"""

from typing import Dict, List, Any, Optional
import streamlit as st


class SampleVideoData:
    """Manages sample video data and selection functionality."""
    
    def __init__(self):
        """Initialize with the provided sample video data."""
        self.sample_videos = {
            "categories": [
                {
                    "name": "Movies",
                    "videos": [
                        {
                            "description": "Big Buck Bunny tells the story of a giant rabbit with a heart bigger than himself. When one sunny day three rodents rudely harass him, something snaps... and the rabbit ain't no bunny anymore! In the typical cartoon tradition he prepares the nasty rodents a comical revenge.\n\nLicensed under the Creative Commons Attribution license\nhttp://www.bigbuckbunny.org",
                            "sources": [
                                "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
                            ],
                            "subtitle": "By Blender Foundation",
                            "thumb": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/BigBuckBunny.jpg",
                            "title": "Big Buck Bunny"
                        },
                        {
                            "description": "The first Blender Open Movie from 2006",
                            "sources": [
                                "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4"
                            ],
                            "subtitle": "By Blender Foundation",
                            "thumb": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/ElephantsDream.jpg",
                            "title": "Elephant Dream"
                        },
                        {
                            "description": "HBO GO now works with Chromecast -- the easiest way to enjoy online video on your TV. For when you want to settle into your Iron Throne to watch the latest episodes. For $35.\nLearn how to use Chromecast with HBO GO and more at google.com/chromecast.",
                            "sources": [
                                "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
                            ],
                            "subtitle": "By Google",
                            "thumb": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/ForBiggerBlazes.jpg",
                            "title": "For Bigger Blazes"
                        },
                        {
                            "description": "Introducing Chromecast. The easiest way to enjoy online video and music on your TV—for when Batman's escapes aren't quite big enough. For $35. Learn how to use Chromecast with Google Play Movies and more at google.com/chromecast.",
                            "sources": [
                                "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4"
                            ],
                            "subtitle": "By Google",
                            "thumb": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/ForBiggerEscapes.jpg",
                            "title": "For Bigger Escape"
                        },
                        {
                            "description": "Introducing Chromecast. The easiest way to enjoy online video and music on your TV. For $35.  Find out more at google.com/chromecast.",
                            "sources": [
                                "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4"
                            ],
                            "subtitle": "By Google",
                            "thumb": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/ForBiggerFun.jpg",
                            "title": "For Bigger Fun"
                        },
                        {
                            "description": "Introducing Chromecast. The easiest way to enjoy online video and music on your TV—for the times that call for bigger joyrides. For $35. Learn how to use Chromecast with YouTube and more at google.com/chromecast.",
                            "sources": [
                                "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4"
                            ],
                            "subtitle": "By Google",
                            "thumb": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/ForBiggerJoyrides.jpg",
                            "title": "For Bigger Joyrides"
                        },
                        {
                            "description": "Introducing Chromecast. The easiest way to enjoy online video and music on your TV—for when you want to make Buster's big meltdowns even bigger. For $35. Learn how to use Chromecast with Netflix and more at google.com/chromecast.",
                            "sources": [
                                "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerMeltdowns.mp4"
                            ],
                            "subtitle": "By Google",
                            "thumb": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/ForBiggerMeltdowns.jpg",
                            "title": "For Bigger Meltdowns"
                        },
                        {
                            "description": "Sintel is an independently produced short film, initiated by the Blender Foundation as a means to further improve and validate the free/open source 3D creation suite Blender. With initial funding provided by 1000s of donations via the internet community, it has again proven to be a viable development model for both open 3D technology as for independent animation film.\nThis 15 minute film has been realized in the studio of the Amsterdam Blender Institute, by an international team of artists and developers. In addition to that, several crucial technical and creative targets have been realized online, by developers and artists and teams all over the world.\nwww.sintel.org",
                            "sources": [
                                "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/Sintel.mp4"
                            ],
                            "subtitle": "By Blender Foundation",
                            "thumb": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/Sintel.jpg",
                            "title": "Sintel"
                        },
                        {
                            "description": "Smoking Tire takes the all-new Subaru Outback to the highest point we can find in hopes our customer-appreciation Balloon Launch will get some free T-shirts into the hands of our viewers.",
                            "sources": [
                                "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/SubaruOutbackOnStreetAndDirt.mp4"
                            ],
                            "subtitle": "By Garage419",
                            "thumb": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/SubaruOutbackOnStreetAndDirt.jpg",
                            "title": "Subaru Outback On Street And Dirt"
                        },
                        {
                            "description": "Tears of Steel was realized with crowd-funding by users of the open source 3D creation tool Blender. Target was to improve and test a complete open and free pipeline for visual effects in film - and to make a compelling sci-fi film in Amsterdam, the Netherlands.  The film itself, and all raw material used for making it, have been released under the Creatieve Commons 3.0 Attribution license. Visit the tearsofsteel.org website to find out more about this, or to purchase the 4-DVD box with a lot of extras.  (CC) Blender Foundation - http://www.tearsofsteel.org",
                            "sources": [
                                "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4"
                            ],
                            "subtitle": "By Blender Foundation",
                            "thumb": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/TearsOfSteel.jpg",
                            "title": "Tears of Steel"
                        },
                        {
                            "description": "The Smoking Tire heads out to Adams Motorsports Park in Riverside, CA to test the most requested car of 2010, the Volkswagen GTI. Will it beat the Mazdaspeed3's standard-setting lap time? Watch and see...",
                            "sources": [
                                "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/VolkswagenGTIReview.mp4"
                            ],
                            "subtitle": "By Garage419",
                            "thumb": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/VolkswagenGTIReview.jpg",
                            "title": "Volkswagen GTI Review"
                        },
                        {
                            "description": "The Smoking Tire is going on the 2010 Bullrun Live Rally in a 2011 Shelby GT500, and posting a video from the road every single day! The only place to watch them is by subscribing to The Smoking Tire or watching at BlackMagicShine.com",
                            "sources": [
                                "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/WeAreGoingOnBullrun.mp4"
                            ],
                            "subtitle": "By Garage419",
                            "thumb": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/WeAreGoingOnBullrun.jpg",
                            "title": "We Are Going On Bullrun"
                        },
                        {
                            "description": "The Smoking Tire meets up with Chris and Jorge from CarsForAGrand.com to see just how far $1,000 can go when looking for a car.The Smoking Tire meets up with Chris and Jorge from CarsForAGrand.com to see just how far $1,000 can go when looking for a car.",
                            "sources": [
                                "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/WhatCarCanYouGetForAGrand.mp4"
                            ],
                            "subtitle": "By Garage419",
                            "thumb": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/WhatCarCanYouGetForAGrand.jpg",
                            "title": "What care can you get for a grand?"
                        }
                    ]
                }
            ]
        }
    
    def get_all_videos(self) -> List[Dict[str, Any]]:
        """Get all videos from all categories."""
        all_videos = []
        for category in self.sample_videos["categories"]:
            all_videos.extend(category["videos"])
        return all_videos
    
    def get_videos_by_category(self, category_name: str) -> List[Dict[str, Any]]:
        """Get videos from a specific category."""
        for category in self.sample_videos["categories"]:
            if category["name"] == category_name:
                return category["videos"]
        return []
    
    def get_video_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """Get a specific video by title."""
        for video in self.get_all_videos():
            if video["title"] == title:
                return video
        return None
    
    def get_video_titles(self) -> List[str]:
        """Get list of all video titles."""
        return [video["title"] for video in self.get_all_videos()]
    
    def get_video_info_for_display(self, video: Dict[str, Any]) -> Dict[str, str]:
        """Get formatted video information for display."""
        return {
            "title": video["title"],
            "subtitle": video["subtitle"],
            "description": video["description"][:200] + "..." if len(video["description"]) > 200 else video["description"],
            "source": video["sources"][0] if video["sources"] else "",
            "thumbnail": video["thumb"]
        }
    
    def render_video_card(self, video: Dict[str, Any], selected: bool = False) -> None:
        """Render a video card with thumbnail and details."""
        info = self.get_video_info_for_display(video)
        
        # Create a container for the video card
        with st.container():
            col1, col2 = st.columns([1, 3])
            
            with col1:
                # Display thumbnail if available
                if info["thumbnail"]:
                    try:
                        st.image(info["thumbnail"], width=150)
                    except:
                        st.write("🎬 Video Thumbnail")
                else:
                    st.write("🎬 Video Thumbnail")
            
            with col2:
                # Video title and subtitle
                st.write(f"**{info['title']}**")
                st.write(f"*{info['subtitle']}*")
                
                # Description
                st.write(info["description"])
                
                # Source URL (truncated for display)
                source_display = info["source"]
                if len(source_display) > 60:
                    source_display = source_display[:60] + "..."
                st.code(source_display)
    
    def render_compact_video_card(self, video: Dict[str, Any]) -> None:
        """Render a compact video card for selected videos preview."""
        info = self.get_video_info_for_display(video)
        
        col1, col2 = st.columns([1, 4])
        
        with col1:
            # Display small thumbnail if available
            if info["thumbnail"]:
                try:
                    st.image(info["thumbnail"], width=80)
                except:
                    st.write("🎬")
            else:
                st.write("🎬")
        
        with col2:
            # Video title and subtitle
            st.write(f"**{info['title']}**")
            st.write(f"*{info['subtitle']}*")
            
            # Truncated description
            description = info["description"]
            if len(description) > 100:
                description = description[:100] + "..."
            st.write(description)
    
    def render_multi_select_interface(self) -> List[Dict[str, Any]]:
        """Render clean multiselect interface for sample videos."""
        st.subheader("📹 Select Sample Videos")
        st.write("Choose one or more videos from the Google sample collection to process:")
        
        all_videos = self.get_all_videos()
        video_titles = [video["title"] for video in all_videos]
        
        # Create a clean multiselect dropdown
        selected_titles = st.multiselect(
            "Select videos to process:",
            options=video_titles,
            default=st.session_state.get('selected_sample_video_titles', []),
            help="Use the dropdown to select multiple videos for processing",
            key="sample_video_multiselect"
        )
        
        # Update session state
        st.session_state.selected_sample_video_titles = selected_titles
        
        # Quick selection buttons
        if len(video_titles) > 0:
            st.write("**Quick Selection Options:**")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("🎯 Select All", use_container_width=True):
                    st.session_state.selected_sample_video_titles = video_titles
                    st.rerun()
            
            with col2:
                blender_titles = [v["title"] for v in all_videos if "Blender" in v["subtitle"]]
                if st.button("🎬 Blender Films", use_container_width=True):
                    st.session_state.selected_sample_video_titles = blender_titles
                    st.rerun()
            
            with col3:
                chromecast_titles = [v["title"] for v in all_videos if "Chromecast" in v["description"]]
                if st.button("📺 Chromecast Ads", use_container_width=True):
                    st.session_state.selected_sample_video_titles = chromecast_titles
                    st.rerun()
            
            with col4:
                car_titles = [v["title"] for v in all_videos if "Garage419" in v["subtitle"]]
                if st.button("🚗 Car Reviews", use_container_width=True):
                    st.session_state.selected_sample_video_titles = car_titles
                    st.rerun()
            
            # Clear selection button
            if st.button("🗑️ Clear Selection"):
                st.session_state.selected_sample_video_titles = []
                st.rerun()
        
        # Show selected videos with preview cards
        if selected_titles:
            st.markdown("---")
            st.subheader("📋 Selected Videos Preview")
            
            selected_video_objects = []
            for title in selected_titles:
                video = self.get_video_by_title(title)
                if video:
                    selected_video_objects.append(video)
                    
                    # Show compact video card
                    with st.expander(f"📹 {video['title']}", expanded=False):
                        self.render_compact_video_card(video)
            
            # Selection summary
            if selected_video_objects:
                selection_info = self.get_selected_videos_info(selected_video_objects)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Videos Selected", selection_info["total_videos"])
                with col2:
                    st.metric("Est. Duration", f"{selection_info['estimated_duration_minutes']} min")
                with col3:
                    creators_text = ", ".join([f"{k} ({v})" for k, v in selection_info["creators"].items()])
                    st.write("**Creators:**")
                    st.write(creators_text)
            
            return selected_video_objects
        else:
            st.info("ℹ️ No videos selected. Use the dropdown above to choose videos for processing.")
            return []
    
    def get_selected_videos_info(self, selected_videos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get summary information about selected videos."""
        if not selected_videos:
            return {}
        
        total_videos = len(selected_videos)
        
        # Count by source/creator
        creators = {}
        for video in selected_videos:
            creator = video["subtitle"]
            creators[creator] = creators.get(creator, 0) + 1
        
        # Estimate total processing time (rough estimate based on typical video lengths)
        estimated_duration_minutes = total_videos * 5  # Assume 5 minutes average per video
        
        return {
            "total_videos": total_videos,
            "creators": creators,
            "estimated_duration_minutes": estimated_duration_minutes,
            "video_titles": [v["title"] for v in selected_videos],
            "video_sources": [v["sources"][0] for v in selected_videos if v["sources"]]
        }


# Global instance for easy access
sample_video_manager = SampleVideoData()