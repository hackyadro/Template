import { EventEmitter } from 'events';
import getBeacons from './beacons.js';
import * as math from 'mathjs';


class DistanceEstimator {
  constructor(bufferSize = 20, measuredPower = -59, envFactor = 4) {
    this.bufferSize = bufferSize;
    this.measuredPower = measuredPower;
    this.envFactor = envFactor;
    this.buffers = {
      logModel: [],
      fspl: [],
      linear: []
    };
  }

  rssiToDistanceLog(rssi) {
    return Math.pow(10, (this.measuredPower - rssi) / (10 * this.envFactor));
  }

  rssiToDistanceFSPL(rssi, freqMHz = 2400) {
    return Math.pow(10, (27.55 - (20 * Math.log10(freqMHz)) + Math.abs(rssi)) / 20.0);
  }

  rssiToDistanceLinear(rssi) {
    return Math.max(0.1, (this.measuredPower - rssi) * 0.1);
  }

  addRSSI(rssi) {
    const d1 = this.rssiToDistanceLog(rssi);
    const d2 = this.rssiToDistanceFSPL(rssi);
    const d3 = this.rssiToDistanceLinear(rssi);

    this._addToBuffer(this.buffers.logModel, d1);
    this._addToBuffer(this.buffers.fspl, d2);
    this._addToBuffer(this.buffers.linear, d3);
  }

  _addToBuffer(buffer, value) {
    if (buffer.length >= this.bufferSize) buffer.shift();
    buffer.push(value);
  }

  getDistance() {
    const averages = [];
    for (const buf of Object.values(this.buffers)) {
      if (buf.length > 0) {
        const avg = buf.reduce((a, b) => a + b, 0) / buf.length;
        averages.push(avg);
      }
    }
    if (averages.length > 0) {
      return averages.reduce((a, b) => a + b, 0) / averages.length;
    }
    return null;
  }
}


class BeaconTracker extends EventEmitter {
  constructor(beacons, options = {}) {
    super();
    this.beacons = this.normalizeBeacons(beacons);
    this.bufferSize = options.bufferSize || 50;
    this.rssiBuffers = {};
    this.estimators = {};
    this.updateInterval = options.updateInterval || 1000;

    setInterval(() => this.processBuffers(), this.updateInterval);
  }

  normalizeBeacons(beaconsArray) {
    const beaconsObj = {};
    beaconsArray.forEach(beacon => {
      beaconsObj[beacon.name] = {
        x: beacon.x,
        y: beacon.y,
        measuredPower: beacon.measuredPower || -59,
        environmentalFactor: beacon.environmentalFactor || 3.0
      };
    });
    return beaconsObj;
  }

  addRssi(beaconName, rssi) {
    if (!this.rssiBuffers[beaconName]) this.rssiBuffers[beaconName] = [];
    this.rssiBuffers[beaconName].push(rssi);
    if (this.rssiBuffers[beaconName].length > this.bufferSize) this.rssiBuffers[beaconName].shift();

    if (!this.estimators[beaconName]) {
      const beacon = this.beacons[beaconName];
      this.estimators[beaconName] = new DistanceEstimator(
        this.bufferSize,
        beacon ? beacon.measuredPower : -59,
        beacon ? beacon.environmentalFactor : 2.0
      );
    }
    this.estimators[beaconName].addRSSI(rssi);
  }

  addRSSIData(rssiDataList) {
    rssiDataList.forEach(rssiData => {
      if (Array.isArray(rssiData) && rssiData.length === 2) {
        const beaconName = rssiData[0];
        const rssiValue = rssiData[1];
        this.addRssi(beaconName, rssiValue);
      }
    });
  }

  processBuffers() {
    const distances = {};
    const usedBeacons = [];

    for (const [beaconName, samples] of Object.entries(this.rssiBuffers)) {
      const beacon = this.beacons[beaconName];
      if (!beacon) continue;

      const estimator = this.estimators[beaconName];
      const distance = estimator ? estimator.getDistance() : null;
      if (distance == null) continue;

      distances[beaconName] = distance;
      usedBeacons.push({
        name: beaconName,
        rssi: samples[samples.length - 1],
        distance: distance,
        x: beacon.x,
        y: beacon.y
      });
    }


    if (Object.keys(distances).length >= 3) {
      const pos = this.trilaterate(distances);
      if (pos) this.emit('position', { position: pos, usedBeacons, timestamp: new Date().toISOString() });
      else console.log('Trilateration failed');
    } else {
      console.log(`Not enough beacons for trilateration: ${Object.keys(distances).length}/3`);
    }
  }

  trilaterate(distances) {
    const keys = Object.keys(distances);
    if (keys.length < 3) return null;

    const bestBeacons = keys
      .map(key => ({ key, distance: distances[key] }))
      .sort((a, b) => a.distance - b.distance)
      .slice(0, 3)
      .map(item => item.key);

    const A = [];
    const b = [];
    const refKey = bestBeacons[0];
    const refBeacon = this.beacons[refKey];
    const refDist = distances[refKey];

    for (let i = 1; i < bestBeacons.length; i++) {
      const key = bestBeacons[i];
      const beacon = this.beacons[key];
      const dist = distances[key];

      const dx = beacon.x - refBeacon.x;
      const dy = beacon.y - refBeacon.y;

      A.push([2 * dx, 2 * dy]);
      b.push(
        Math.pow(refDist, 2) - Math.pow(dist, 2) -
        Math.pow(refBeacon.x, 2) + Math.pow(beacon.x, 2) -
        Math.pow(refBeacon.y, 2) + Math.pow(beacon.y, 2)
      );
    }

    try {
      const AT = math.transpose(A);
      const ATA = math.multiply(AT, A);
      const ATb = math.multiply(AT, b);
      const sol = math.lusolve(ATA, ATb);

      const x = sol[0][0] + refBeacon.x;
      const y = sol[1][0] + refBeacon.y;
      return { x, y };
    } catch (error) {
      console.log('Trilateration error:', error.message);
      return null;
    }
  }

  getBufferStatus() {
    const status = {};
    for (const [beaconName, buffer] of Object.entries(this.rssiBuffers)) {
      const estimator = this.estimators[beaconName];
      status[beaconName] = {
        samples: buffer.length,
        lastRSSI: buffer.length > 0 ? buffer[buffer.length - 1] : null,
        estimatedDistance: estimator ? estimator.getDistance() : null
      };
    }
    return status;
  }
}

// === Фабрика трекера ===
async function createTracker(dirname, options = {}) {
  const beaconsArray = await getBeacons(dirname);
  const tracker = new BeaconTracker(beaconsArray, options);

  return tracker;
}

export { BeaconTracker, createTracker };
