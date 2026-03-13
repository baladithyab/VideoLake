import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Clock, Search, Share2, Download } from 'lucide-react';
import { VideoPlayer } from '../VideoPlayer';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { toast } from 'react-hot-toast';

interface VideoMatch {
  startTime: number;
  endTime: number;
  score: number;
  query: string;
  transcript?: string;
}

interface VideoDetails {
  id: string;
  title: string;
  s3Uri: string;
  duration: number;
  matches: VideoMatch[];
  thumbnailUrl?: string;
}

export const VideoDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [videoDetails, setVideoDetails] = useState<VideoDetails | null>(null);
  const [currentMatch, setCurrentMatch] = useState<VideoMatch | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchVideoDetails = async () => {
      setIsLoading(true);
      try {
        // TODO: Replace with actual API call - api.getVideoDetails(id)
        // This endpoint should return: { id, title, s3Uri, duration, matches[], thumbnailUrl }
        // Each match should include: { startTime, endTime, score, query, transcript }

        // Temporary mock data for development
        await new Promise(resolve => setTimeout(resolve, 500));
        const mockDetails: VideoDetails = {
          id: id || 'unknown',
          title: `Video ${id}`,
          s3Uri: `s3://video-bucket/videos/${id}.mp4`,
          duration: 204,
          matches: [
            {
              startTime: 45,
              endTime: 72,
              score: 0.97,
              query: "person running on beach",
              transcript: "...as she runs along the shoreline, the waves crash nearby..."
            },
            {
              startTime: 154,
              endTime: 178,
              score: 0.95,
              query: "person running on beach",
              transcript: "...jogging through the sand with the ocean in the background..."
            }
          ],
          thumbnailUrl: undefined
        };

        setVideoDetails(mockDetails);
        if (mockDetails.matches.length > 0) {
          setCurrentMatch(mockDetails.matches[0]);
        }
      } catch (error) {
        console.error('Failed to fetch video details:', error);
        toast.error('Failed to load video details');
      } finally {
        setIsLoading(false);
      }
    };

    if (id) {
      fetchVideoDetails();
    }
  }, [id]);

  const handleBack = () => {
    navigate('/demo/search');
  };

  const handleMatchClick = (match: VideoMatch) => {
    setCurrentMatch(match);
  };

  const handleShare = () => {
    const url = window.location.href;
    navigator.clipboard.writeText(url);
    toast.success('Link copied to clipboard');
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}m ${secs}s`;
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (!videoDetails) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-gray-500">Video not found</p>
            <Button onClick={handleBack} className="mt-4">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Search
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <Button variant="ghost" onClick={handleBack}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Results
            </Button>
            <div className="flex items-center space-x-2">
              <Button variant="outline" size="sm" onClick={handleShare}>
                <Share2 className="h-4 w-4 mr-2" />
                Share
              </Button>
              <Button variant="outline" size="sm" disabled>
                <Download className="h-4 w-4 mr-2" />
                Download
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Video Player */}
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardContent className="p-0">
                <VideoPlayer
                  videoUrl={videoDetails.s3Uri}
                  startTime={currentMatch?.startTime}
                  endTime={currentMatch?.endTime}
                  autoPlay={true}
                />
              </CardContent>
            </Card>

            {/* Current Match Details */}
            {currentMatch && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Match Details</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Match Score:</span>
                      <Badge variant="default" className="bg-green-500 text-lg px-3 py-1">
                        {(currentMatch.score * 100).toFixed(1)}%
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Segment:</span>
                      <span className="font-medium text-gray-900">
                        {formatTime(currentMatch.startTime)} - {formatTime(currentMatch.endTime)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Duration:</span>
                      <span className="font-medium text-gray-900">
                        {formatDuration(currentMatch.endTime - currentMatch.startTime)}
                      </span>
                    </div>
                    <div>
                      <span className="text-sm text-gray-600 block mb-2">Search Query:</span>
                      <div className="flex items-center space-x-2 bg-gray-50 p-3 rounded-lg">
                        <Search className="h-4 w-4 text-gray-400" />
                        <span className="font-medium text-gray-900">{currentMatch.query}</span>
                      </div>
                    </div>
                    {currentMatch.transcript && (
                      <div>
                        <span className="text-sm text-gray-600 block mb-2">Transcript:</span>
                        <div className="bg-gray-50 p-3 rounded-lg">
                          <p className="text-sm text-gray-900 italic">"{currentMatch.transcript}"</p>
                        </div>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Video Info */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Video Information</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div>
                    <span className="text-sm text-gray-600">Title:</span>
                    <p className="font-medium text-gray-900">{videoDetails.title}</p>
                  </div>
                  <div>
                    <span className="text-sm text-gray-600">Duration:</span>
                    <p className="font-medium text-gray-900">{formatTime(videoDetails.duration)}</p>
                  </div>
                  <div>
                    <span className="text-sm text-gray-600">Source:</span>
                    <p className="text-xs text-gray-500 font-mono break-all">{videoDetails.s3Uri}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Sidebar - Timeline & Matches */}
          <div className="space-y-6">
            {/* Timeline */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Timeline</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {videoDetails.matches.map((match, index) => {
                    const isActive = currentMatch === match;
                    const progressPercent = (match.startTime / videoDetails.duration) * 100;

                    return (
                      <button
                        key={index}
                        onClick={() => handleMatchClick(match)}
                        className={`w-full text-left p-3 rounded-lg border-2 transition-all ${
                          isActive
                            ? 'border-indigo-500 bg-indigo-50'
                            : 'border-gray-200 hover:border-gray-300 bg-white'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium text-gray-900">
                            Match {index + 1}
                          </span>
                          <Badge
                            variant={isActive ? 'default' : 'secondary'}
                            className={isActive ? 'bg-green-500' : ''}
                          >
                            {(match.score * 100).toFixed(0)}%
                          </Badge>
                        </div>
                        <div className="flex items-center space-x-2 text-xs text-gray-600 mb-2">
                          <Clock className="h-3 w-3" />
                          <span>
                            {formatTime(match.startTime)} - {formatTime(match.endTime)}
                          </span>
                        </div>
                        {/* Progress bar */}
                        <div className="w-full bg-gray-200 rounded-full h-1.5 mb-2">
                          <div
                            className="bg-indigo-600 h-1.5 rounded-full"
                            style={{ width: `${progressPercent}%` }}
                          />
                        </div>
                        {match.transcript && (
                          <p className="text-xs text-gray-500 line-clamp-2 italic">
                            "{match.transcript}"
                          </p>
                        )}
                      </button>
                    );
                  })}
                </div>
              </CardContent>
            </Card>

            {/* Similar Moments (placeholder) */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Similar Moments</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center py-8 text-gray-500 text-sm">
                  <Search className="h-8 w-8 mx-auto mb-2 text-gray-400" />
                  <p>Similar video segments will appear here</p>
                  <p className="text-xs mt-1">Based on visual and semantic similarity</p>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};
