import { useState, useRef, useEffect } from 'react';
import { Track } from '@/api/types';
import { X, Heart } from 'lucide-react';

interface SwipeCardProps {
  track: Track;
  onSwipeLeft: () => void;
  onSwipeRight: () => void;
  onPlayPreview?: (url: string | null) => void;
}

export const SwipeCard = ({ track, onSwipeLeft, onSwipeRight, onPlayPreview }: SwipeCardProps) => {
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [rotation, setRotation] = useState(0);
  const cardRef = useRef<HTMLDivElement>(null);
  const startPos = useRef({ x: 0, y: 0 });

  useEffect(() => {
    // Play preview when card is shown
    if (onPlayPreview) {
      onPlayPreview(track.previewUrl);
    }

    return () => {
      // Stop on unmount
      if (onPlayPreview) {
        onPlayPreview(null);
      }
    };
  }, [track.id, onPlayPreview]);

  const handleStart = (clientX: number, clientY: number) => {
    setIsDragging(true);
    startPos.current = { x: clientX - position.x, y: clientY - position.y };
  };

  const handleMove = (clientX: number, clientY: number) => {
    if (!isDragging) return;

    const x = clientX - startPos.current.x;
    const y = clientY - startPos.current.y;
    const rot = x / 20;

    setPosition({ x, y });
    setRotation(rot);
  };

  const handleEnd = () => {
    if (!isDragging) return;
    setIsDragging(false);

    const threshold = 100;

    if (Math.abs(position.x) > threshold) {
      // Trigger swipe
      if (position.x > 0) {
        onSwipeRight();
      } else {
        onSwipeLeft();
      }
    } else {
      // Snap back
      setPosition({ x: 0, y: 0 });
      setRotation(0);
    }
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    handleStart(e.clientX, e.clientY);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    handleMove(e.clientX, e.clientY);
  };

  const handleTouchStart = (e: React.TouchEvent) => {
    const touch = e.touches[0];
    handleStart(touch.clientX, touch.clientY);
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    const touch = e.touches[0];
    handleMove(touch.clientX, touch.clientY);
  };

  return (
    <div
      ref={cardRef}
      className="absolute inset-0 flex items-center justify-center"
      onMouseMove={handleMouseMove}
      onMouseUp={handleEnd}
      onMouseLeave={handleEnd}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleEnd}
    >
      <div
        className="relative w-full max-w-md h-[600px] touch-none cursor-grab active:cursor-grabbing"
        style={{
          transform: `translate(${position.x}px, ${position.y}px) rotate(${rotation}deg)`,
          transition: isDragging ? 'none' : 'all 0.3s ease-out',
        }}
        onMouseDown={handleMouseDown}
        onTouchStart={handleTouchStart}
      >
        {/* Feedback indicators */}
        <div
          className="absolute top-8 right-8 z-10 rounded-full border-4 border-destructive p-4 transition-opacity"
          style={{ opacity: position.x < -50 ? Math.min(Math.abs(position.x) / 100, 1) : 0 }}
        >
          <X className="w-12 h-12 text-destructive" />
        </div>
        <div
          className="absolute top-8 left-8 z-10 rounded-full border-4 border-primary p-4 transition-opacity"
          style={{ opacity: position.x > 50 ? Math.min(position.x / 100, 1) : 0 }}
        >
          <Heart className="w-12 h-12 text-primary" fill="currentColor" />
        </div>

        {/* Card */}
        <div className="w-full h-full bg-card rounded-3xl shadow-card overflow-hidden">
          <div className="relative h-3/4">
            <img
              src={track.artworkUrl}
              alt={`${track.title} by ${track.artist}`}
              className="w-full h-full object-cover"
              draggable={false}
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent" />
          </div>

          <div className="p-6 space-y-3">
            <div>
              <h2 className="text-2xl font-bold text-foreground truncate">{track.title}</h2>
              <p className="text-lg text-muted-foreground truncate">{track.artist}</p>
            </div>

            {track.reasons && track.reasons.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {track.reasons.slice(0, 2).map((reason, idx) => (
                  <span
                    key={idx}
                    className="px-3 py-1 bg-secondary text-secondary-foreground text-sm rounded-full truncate max-w-full"
                  >
                    {reason}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
