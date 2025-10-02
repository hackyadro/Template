import { MapCanvas } from '@/components/MapCanvas';
import { ControlPanel } from '@/components/ControlPanel';
import { StatusPanel } from '@/components/StatusPanel';
import { usePositioning } from '@/hooks/usePositioning';
import { Radio } from 'lucide-react';

const Index = () => {
  const {
    beacons,
    positions,
    currentPosition,
    sessionStatus,
    isSessionActive,
    isLoading,
    startSession,
    stopSession,
    savePath
  } = usePositioning();

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        {/* Header */}
        <header className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-primary/10 rounded-lg">
              <Radio className="w-8 h-8 text-primary" />
            </div>
            <div>
              <h1 className="text-4xl font-bold text-foreground">
                Indoor Positioning System
              </h1>
              <p className="text-muted-foreground">
                Real-time beacon-based location tracking and visualization
              </p>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Left Column - Controls and Status */}
          <div className="space-y-6">
            <ControlPanel
              onStartSession={startSession}
              onStopSession={stopSession}
              onSavePath={savePath}
              isSessionActive={isSessionActive}
              disabled={isLoading}
            />
            
            <StatusPanel
              sessionStatus={sessionStatus}
              currentPosition={currentPosition}
              pointsCount={positions.length}
              beaconsCount={beacons.length}
            />
          </div>

          {/* Right Column - Map Visualization */}
          <div className="lg:col-span-2">
            <div className="bg-card border border-border rounded-lg p-6 shadow-sm">
              <h2 className="text-xl font-semibold mb-4">Map View</h2>
              <div className="flex justify-center">
                <MapCanvas
                  beacons={beacons}
                  positions={positions}
                  currentPosition={currentPosition}
                  width={800}
                  height={600}
                />
              </div>
              
              {/* Legend */}
              <div className="mt-4 flex gap-6 justify-center text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded-full bg-beacon"></div>
                  <span className="text-muted-foreground">Beacons</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded-full bg-position"></div>
                  <span className="text-muted-foreground">Current Position</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-path"></div>
                  <span className="text-muted-foreground">Path</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer Info */}
        <footer className="mt-8 text-center text-sm text-muted-foreground">
          <p>Configure API endpoint in src/api/rest-client.ts</p>
        </footer>
      </div>
    </div>
  );
};

export default Index;
