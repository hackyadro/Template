import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { Position } from '@/types';
import { Activity, MapPin, Target } from 'lucide-react';

interface StatusPanelProps {
  sessionStatus: string;
  currentPosition?: Position;
  pointsCount: number;
  beaconsCount: number;
}

export const StatusPanel = ({
  sessionStatus,
  currentPosition,
  pointsCount,
  beaconsCount
}: StatusPanelProps) => {
  const getStatusBadgeVariant = () => {
    switch (sessionStatus) {
      case 'started':
        return 'default';
      case 'stopped':
        return 'secondary';
      case 'error':
        return 'destructive';
      default:
        return 'outline';
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Session Status</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm font-medium">Status:</span>
          </div>
          <Badge variant={getStatusBadgeVariant()}>
            {sessionStatus}
          </Badge>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MapPin className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm font-medium">Position:</span>
          </div>
          <span className="text-sm font-mono">
            {currentPosition 
              ? `X: ${currentPosition.x.toFixed(2)}, Y: ${currentPosition.y.toFixed(2)}`
              : 'Unknown'
            }
          </span>
        </div>

        {currentPosition?.accuracy && (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Target className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm font-medium">Accuracy:</span>
            </div>
            <span className="text-sm font-mono">
              {currentPosition.accuracy.toFixed(2)}m
            </span>
          </div>
        )}

        <div className="pt-3 border-t border-border space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Points recorded:</span>
            <span className="font-mono font-medium">{pointsCount}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Active beacons:</span>
            <span className="font-mono font-medium">{beaconsCount}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
