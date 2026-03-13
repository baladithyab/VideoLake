import React, { useRef, useEffect } from 'react';
import { Play, Pause, Volume2, VolumeX, Maximize, Repeat } from 'lucide-react';
import { Input } from '@/components/ui/input';

interface VideoPlayerProps {
  videoUrl: string;
  startTime?: number;
  endTime?: number;
  autoPlay?: boolean;
  loop?: boolean;
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({
  videoUrl,
  startTime = 0,
  endTime,
  autoPlay = false,
  loop: initialLoop = false,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = React.useState(false);
  const [currentTime, setCurrentTime] = React.useState(0);
  const [duration, setDuration] = React.useState(0);
  const [isMuted, setIsMuted] = React.useState(false);
  const [isLooping, setIsLooping] = React.useState(initialLoop);

  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.currentTime = startTime;
      if (autoPlay) {
        videoRef.current.play().catch(e => console.error("Autoplay failed:", e));
      }
    }
  }, [videoUrl, startTime, autoPlay]);

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
      if (endTime && videoRef.current.currentTime >= endTime) {
        if (isLooping) {
          videoRef.current.currentTime = startTime;
          videoRef.current.play().catch(e => console.error("Loop replay failed:", e));
        } else {
          videoRef.current.pause();
          setIsPlaying(false);
        }
      }
    }
  };

  const togglePlay = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const toggleMute = () => {
    if (videoRef.current) {
      videoRef.current.muted = !isMuted;
      setIsMuted(!isMuted);
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
    <div className="bg-black rounded-lg overflow-hidden shadow-lg">
      <video
        ref={videoRef}
        src={videoUrl}
        className="w-full aspect-video"
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={() => setDuration(videoRef.current?.duration || 0)}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
      />
      
      <div className="bg-gray-900 p-4 text-white">
        <div className="flex items-center justify-between mb-2">
          <div className="text-sm font-mono">
            {formatTime(currentTime)} / {formatTime(duration)}
          </div>
          {endTime && (
            <div className="text-xs text-gray-400">
              Segment: {formatTime(startTime)} - {formatTime(endTime)}
            </div>
          )}
        </div>
        
        <div className="flex items-center gap-4">
          <button onClick={togglePlay} className="hover:text-indigo-400 transition-colors">
            {isPlaying ? <Pause size={24} /> : <Play size={24} />}
          </button>
          
          <Input
            type="range"
            min="0"
            max={duration}
            value={currentTime}
            onChange={(e) => {
              const time = parseFloat(e.target.value);
              if (videoRef.current) videoRef.current.currentTime = time;
              setCurrentTime(time);
            }}
            className="flex-1 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
          />
          
          <button onClick={toggleMute} className="hover:text-indigo-400 transition-colors">
            {isMuted ? <VolumeX size={20} /> : <Volume2 size={20} />}
          </button>
          
          <button
            onClick={() => setIsLooping(!isLooping)}
            className={`hover:text-indigo-400 transition-colors ${isLooping ? 'text-indigo-400' : ''}`}
            title="Toggle Loop"
          >
            <Repeat size={20} />
          </button>

          <button onClick={toggleFullscreen} className="hover:text-indigo-400 transition-colors">
            <Maximize size={20} />
          </button>
        </div>
      </div>
    </div>
  );
};