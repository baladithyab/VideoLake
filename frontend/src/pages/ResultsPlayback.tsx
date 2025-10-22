import { useState, useRef, useEffect } from 'react';
import { Play, Pause, SkipBack, SkipForward, Volume2, VolumeX, Maximize } from 'lucide-react';

interface SearchResult {
  id: string;
  video_uri: string;
  score: number;
  start_time: number;
  end_time: number;
  metadata?: {
    title?: string;
    description?: string;
    thumbnail?: string;
  };
  vector_type: string;
}

export default function ResultsPlayback() {
  const [results, setResults] = useState<SearchResult[]>([]);
  const [selectedResult, setSelectedResult] = useState<SearchResult | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);

  // Load results from localStorage (set by QuerySearch page)
  useEffect(() => {
    const storedResults = localStorage.getItem('searchResults');
    if (storedResults) {
      try {
        const parsed = JSON.parse(storedResults);
        setResults(parsed.results || []);
        if (parsed.results && parsed.results.length > 0) {
          setSelectedResult(parsed.results[0]);
        }
      } catch (error) {
        console.error('Failed to parse search results:', error);
      }
    }
  }, []);

  // Video event handlers
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleTimeUpdate = () => setCurrentTime(video.currentTime);
    const handleDurationChange = () => setDuration(video.duration);
    const handleEnded = () => setIsPlaying(false);

    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('durationchange', handleDurationChange);
    video.addEventListener('ended', handleEnded);

    return () => {
      video.removeEventListener('timeupdate', handleTimeUpdate);
      video.removeEventListener('durationchange', handleDurationChange);
      video.removeEventListener('ended', handleEnded);
    };
  }, []);

  // Update video source when selected result changes
  useEffect(() => {
    if (selectedResult && videoRef.current) {
      const video = videoRef.current;
      // For demo purposes, using a placeholder video URL
      // In production, this would be the actual S3 signed URL
      video.src = selectedResult.video_uri || '';
      if (selectedResult.start_time) {
        video.currentTime = selectedResult.start_time;
      }
    }
  }, [selectedResult]);

  const togglePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value);
    setCurrentTime(time);
    if (videoRef.current) {
      videoRef.current.currentTime = time;
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const vol = parseFloat(e.target.value);
    setVolume(vol);
    if (videoRef.current) {
      videoRef.current.volume = vol;
    }
    setIsMuted(vol === 0);
  };

  const toggleMute = () => {
    if (videoRef.current) {
      videoRef.current.muted = !isMuted;
      setIsMuted(!isMuted);
    }
  };

  const skipBackward = () => {
    if (videoRef.current) {
      videoRef.current.currentTime = Math.max(0, currentTime - 10);
    }
  };

  const skipForward = () => {
    if (videoRef.current) {
      videoRef.current.currentTime = Math.min(duration, currentTime + 10);
    }
  };

  const toggleFullscreen = () => {
    if (videoRef.current) {
      if (document.fullscreenElement) {
        document.exitFullscreen();
      } else {
        videoRef.current.requestFullscreen();
      }
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Results & Playback</h1>
        <p className="mt-2 text-sm text-gray-600">
          View search results and play video segments
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Video Player */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-black rounded-lg overflow-hidden">
            <video
              ref={videoRef}
              className="w-full aspect-video"
              poster={selectedResult?.metadata?.thumbnail}
            >
              Your browser does not support the video tag.
            </video>
          </div>

          {/* Video Controls */}
          <div className="bg-white shadow rounded-lg p-4 space-y-3">
            {/* Progress Bar */}
            <div className="space-y-1">
              <input
                type="range"
                min="0"
                max={duration || 0}
                value={currentTime}
                onChange={handleSeek}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
              />
              <div className="flex justify-between text-xs text-gray-500">
                <span>{formatTime(currentTime)}</span>
                <span>{formatTime(duration)}</span>
              </div>
            </div>

            {/* Control Buttons */}
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <button
                  onClick={skipBackward}
                  className="p-2 hover:bg-gray-100 rounded-full"
                >
                  <SkipBack className="h-5 w-5" />
                </button>
                <button
                  onClick={togglePlayPause}
                  className="p-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-full"
                >
                  {isPlaying ? <Pause className="h-6 w-6" /> : <Play className="h-6 w-6" />}
                </button>
                <button
                  onClick={skipForward}
                  className="p-2 hover:bg-gray-100 rounded-full"
                >
                  <SkipForward className="h-5 w-5" />
                </button>
              </div>

              <div className="flex items-center space-x-2">
                <button onClick={toggleMute} className="p-2 hover:bg-gray-100 rounded-full">
                  {isMuted ? <VolumeX className="h-5 w-5" /> : <Volume2 className="h-5 w-5" />}
                </button>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={isMuted ? 0 : volume}
                  onChange={handleVolumeChange}
                  className="w-20 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
                <button onClick={toggleFullscreen} className="p-2 hover:bg-gray-100 rounded-full">
                  <Maximize className="h-5 w-5" />
                </button>
              </div>
            </div>

            {/* Segment Info */}
            {selectedResult && (
              <div className="pt-3 border-t border-gray-200">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-medium text-gray-900">
                      {selectedResult.metadata?.title || 'Video Segment'}
                    </h3>
                    <p className="text-sm text-gray-500 mt-1">
                      Segment: {formatTime(selectedResult.start_time)} - {formatTime(selectedResult.end_time)}
                    </p>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-medium text-indigo-600">
                      Similarity: {(selectedResult.score * 100).toFixed(1)}%
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {selectedResult.vector_type}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Results List */}
        <div className="lg:col-span-1">
          <div className="bg-white shadow rounded-lg p-4">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              Search Results ({results.length})
            </h3>
            <div className="space-y-2 max-h-[600px] overflow-y-auto">
              {results.length > 0 ? (
                results.map((result, index) => (
                  <button
                    key={result.id || index}
                    onClick={() => setSelectedResult(result)}
                    className={`w-full text-left p-3 rounded-lg border transition-colors ${
                      selectedResult?.id === result.id
                        ? 'border-indigo-500 bg-indigo-50'
                        : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-900">
                          Result {index + 1}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                          {formatTime(result.start_time)} - {formatTime(result.end_time)}
                        </p>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-semibold text-indigo-600">
                          {(result.score * 100).toFixed(1)}%
                        </div>
                        <div className="text-xs text-gray-400 mt-1">
                          {result.vector_type}
                        </div>
                      </div>
                    </div>
                    {result.metadata?.description && (
                      <p className="text-xs text-gray-600 mt-2 line-clamp-2">
                        {result.metadata.description}
                      </p>
                    )}
                  </button>
                ))
              ) : (
                <div className="text-center py-8">
                  <p className="text-sm text-gray-500">No search results</p>
                  <p className="text-xs text-gray-400 mt-1">
                    Run a search from the Query & Search page
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

