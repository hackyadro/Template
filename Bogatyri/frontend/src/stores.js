import { writable, derived } from 'svelte/store';

export const currentPosition = writable({ x: 0, y: 0 });

export const route = writable([]);

export const beacons = writable([]);

export const systemStatus = writable({
    isRecording: false,
    frequency: 1,
    isConnected: false
});

export const realTimePath = writable([]);

export const lastPosition = derived(
    realTimePath,
    $path => $path[$path.length - 1] || { x: 0, y: 0 }
);
