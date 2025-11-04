#!/usr/bin/env python3
"""
S3Vector Stress Test Runner
Processes videos from datasets through Bedrock Marengo 2.7 embeddings
"""

import argparse
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from datasets import load_dataset
import boto3

# Import your services
from src.services.comprehensive_video_processing_service import (
    ComprehensiveVideoProcessingService,
    ProcessingConfig,
    VectorType,
    StoragePattern
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StressTestConfig:
    """Stress test configuration"""
    def __init__(self,
                 dataset_id: str,
                 max_videos: int = 100,
                 s3_bucket: str = None,
                 vector_index_arn: str = None,
                 results_file: str = "stress_test_results.json"):
        self.dataset_id = dataset_id
        self.max_videos = max_videos
        self.s3_bucket = s3_bucket
        self.vector_index_arn = vector_index_arn
        self.results_file = results_file


class StressTestRunner:
    """Run stress tests on datasets"""
    
    def __init__(self, config: StressTestConfig):
        self.config = config
        self.processing_service = ComprehensiveVideoProcessingService()
        self.results = {
            'config': {
                'dataset_id': config.dataset_id,
                'max_videos': config.max_videos,
                'started_at': datetime.now().isoformat()
            },
            'videos': [],
            'summary': {}
        }
    
    def run_stress_test(self):
        """Run stress test on dataset"""
        logger.info(f"Starting stress test on {self.config.dataset_id}")
        logger.info(f"Target: {self.config.max_videos} videos")
        
        dataset = load_dataset(self.config.dataset_id, streaming=True, split="train")
        
        successful = 0
        failed = 0
        total_time_ms = 0
        total_segments = 0
        
        for i, example in enumerate(dataset):
            if i >= self.config.max_videos:
                break
            
            # Get video URL
            video_url = None
            for field in ['url', 'video_url', 'link']:
                if field in example and example[field]:
                    video_url = example[field]
                    break
            
            if not video_url:
                logger.warning(f"[{i}] No URL found")
                failed += 1
                continue
            
            try:
                logger.info(f"[{i}/{self.config.max_videos}] Processing: {video_url[:60]}")
                
                # Process through S3Vector
                result = self.processing_service.process_video_from_url(
                    video_url=video_url,
                    target_indexes={
                        VectorType.VISUAL_TEXT: self.config.vector_index_arn,
                        VectorType.VISUAL_IMAGE: self.config.vector_index_arn,
                        VectorType.AUDIO: self.config.vector_index_arn
                    } if self.config.vector_index_arn else None
                )
                
                video_result = {
                    'index': i,
                    'job_id': result.job_id,
                    'status': result.status,
                    'processing_time_ms': result.processing_time_ms,
                    'total_segments': result.total_segments,
                    'estimated_cost_usd': result.estimated_cost_usd,
                    'error': result.error_message
                }
                
                self.results['videos'].append(video_result)
                
                if result.is_successful:
                    successful += 1
                    total_time_ms += result.processing_time_ms or 0
                    total_segments += result.total_segments
                    logger.info(f"  SUCCESS: {result.total_segments} segments, {result.processing_time_ms}ms")
                else:
                    failed += 1
                    logger.error(f"  FAILED: {result.error_message}")
                
            except Exception as e:
                logger.error(f"[{i}] Error: {e}")
                failed += 1
                self.results['videos'].append({
                    'index': i,
                    'status': 'exception',
                    'error': str(e)
                })
        
        # Save results
        self.results['summary'] = {
            'successful': successful,
            'failed': failed,
            'total': successful + failed,
            'success_rate': successful / (successful + failed) if (successful + failed) > 0 else 0,
            'total_processing_time_ms': total_time_ms,
            'avg_processing_time_ms': total_time_ms / successful if successful > 0 else 0,
            'total_segments': total_segments,
            'avg_segments_per_video': total_segments / successful if successful > 0 else 0,
            'completed_at': datetime.now().isoformat()
        }
        
        self.save_results()
        return self.results
    
    def save_results(self):
        """Save results to file"""
        results_path = Path(self.config.results_file)
        with open(results_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"Results saved to {results_path}")


def main():
    parser = argparse.ArgumentParser(description="Run stress tests on video datasets")
    parser.add_argument("--dataset-id", required=True, help="HuggingFace dataset ID")
    parser.add_argument("--max-videos", type=int, default=100, help="Maximum videos to process")
    parser.add_argument("--s3-bucket", help="S3 bucket for video storage")
    parser.add_argument("--vector-index-arn", help="S3Vector index ARN")
    parser.add_argument("--results-file", default="stress_test_results.json", help="Results output file")
    
    args = parser.parse_args()
    
    config = StressTestConfig(
        dataset_id=args.dataset_id,
        max_videos=args.max_videos,
        s3_bucket=args.s3_bucket,
        vector_index_arn=args.vector_index_arn,
        results_file=args.results_file
    )
    
    runner = StressTestRunner(config)
    results = runner.run_stress_test()
    
    # Print summary
    summary = results['summary']
    print("\n" + "="*60)
    print("STRESS TEST SUMMARY")
    print("="*60)
    print(f"Successful: {summary['successful']}/{summary['total']}")
    print(f"Success Rate: {summary['success_rate']*100:.1f}%")
    print(f"Total Processing Time: {summary['total_processing_time_ms']/1000:.1f}s")
    print(f"Avg Processing Time: {summary['avg_processing_time_ms']:.0f}ms")
    print(f"Total Segments: {summary['total_segments']}")
    print(f"Avg Segments/Video: {summary['avg_segments_per_video']:.1f}")
    print("="*60)


if __name__ == "__main__":
    main()
