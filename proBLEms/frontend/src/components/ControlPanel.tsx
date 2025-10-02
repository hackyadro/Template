import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Play, Square, Save } from 'lucide-react';

interface ControlPanelProps {
  onStartSession: (frequency: number, beaconMapId: string) => void;
  onStopSession: () => void;
  onSavePath: (fileName: string) => void;
  isSessionActive: boolean;
  disabled?: boolean;
}

export const ControlPanel = ({
  onStartSession,
  onStopSession,
  onSavePath,
  isSessionActive,
  disabled = false
}: ControlPanelProps) => {
  const [frequency, setFrequency] = useState(5.0);
  const [beaconMapId, setBeaconMapId] = useState('office');
  const [fileName, setFileName] = useState('');

  const handleStart = () => {
    onStartSession(frequency, beaconMapId);
  };

  const handleSave = () => {
    const name = fileName || `track_${Date.now()}`;
    onSavePath(name);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Session Control</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="frequency">Frequency (Hz)</Label>
            <Input
              id="frequency"
              type="number"
              value={frequency}
              onChange={(e) => setFrequency(parseFloat(e.target.value))}
              min="0.1"
              max="10"
              step="0.1"
              disabled={isSessionActive || disabled}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="mapId">Map ID</Label>
            <Input
              id="mapId"
              type="text"
              value={beaconMapId}
              onChange={(e) => setBeaconMapId(e.target.value)}
              disabled={isSessionActive || disabled}
            />
          </div>
        </div>

        <div className="flex gap-2">
          <Button
            onClick={handleStart}
            disabled={isSessionActive || disabled}
            className="flex-1"
          >
            <Play className="w-4 h-4 mr-2" />
            Start Session
          </Button>
          <Button
            onClick={onStopSession}
            disabled={!isSessionActive || disabled}
            variant="secondary"
            className="flex-1"
          >
            <Square className="w-4 h-4 mr-2" />
            Stop Session
          </Button>
        </div>

        <div className="space-y-2">
          <Label htmlFor="fileName">File Name (optional)</Label>
          <div className="flex gap-2">
            <Input
              id="fileName"
              type="text"
              value={fileName}
              onChange={(e) => setFileName(e.target.value)}
              placeholder="track_001"
              disabled={isSessionActive || disabled}
            />
            <Button
              onClick={handleSave}
              disabled={isSessionActive || disabled}
              variant="default"
              className="bg-success hover:bg-success/90"
            >
              <Save className="w-4 h-4 mr-2" />
              Save
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
