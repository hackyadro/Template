import getBeacons from './beacons.js';

function addRSSIData(beaconCoordinates, rssiDataList) {
    rssiDataList.forEach(rssiData => {
        if (Array.isArray(rssiData) && rssiData.length === 2) {
            const beaconName = rssiData[0];
            const rssiValue = rssiData[1]; 
            
            const beacon = beaconCoordinates.find(b => b.name === beaconName);
            if (beacon) {
                beacon.RSSI = rssiValue;
            }
        }
    });
    
    return beaconCoordinates;
}

function sortBeaconsByRSSI(beaconCoordinates) {
    return beaconCoordinates.sort((b, a) => {
        return a.RSSI - b.RSSI;
    });
}

function getTopThreeBeacons(sortedBeacons) {
    return sortedBeacons.slice(0, 3);
}

function rssiToDistance(rssi, measuredPower = -59, environmentalFactor = 4) {
    return Math.pow(10, (measuredPower - rssi) / (10 * environmentalFactor));
}

function calculateBeaconDistances(topThreeBeacons) {
    return topThreeBeacons.map(beacon => {
        return {
            ...beacon,
            distance: rssiToDistance(beacon.RSSI)
        };
    });
}

function trilaterateThreeCircles(circles) {
    if (circles.length < 3) {
        console.log("There are not enough circles for trilateration");
        return null;
    }

    const [c1, c2, c3] = circles.slice(0, 3);
    
    const A = c2.x - c1.x;
    const B = c2.y - c1.y;
    const C = c3.x - c1.x;
    const D = c3.y - c1.y;
    
    const r1_sq = c1.distance * c1.distance;
    const r2_sq = c2.distance * c2.distance;
    const r3_sq = c3.distance * c3.distance;
    
    const right1 = (r1_sq - r2_sq + c2.x*c2.x - c1.x*c1.x + c2.y*c2.y - c1.y*c1.y) / 2;
    const right2 = (r1_sq - r3_sq + c3.x*c3.x - c1.x*c1.x + c3.y*c3.y - c1.y*c1.y) / 2;
    
    const determinant = A * D - B * C;
    
    if (Math.abs(determinant) < 1e-10) {
        console.log("The circles are degenerate or parallel, and it is impossible to find a point of intersection");
        return null;
    }
    
    const x = (right1 * D - B * right2) / determinant;
    const y = (A * right2 - right1 * C) / determinant;
    
    const maxX = Math.max(c1.x, c2.x, c3.x) + Math.max(c1.distance, c2.distance, c3.distance);
    const minX = Math.min(c1.x, c2.x, c3.x) - Math.max(c1.distance, c2.distance, c3.distance);
    const maxY = Math.max(c1.y, c2.y, c3.y) + Math.max(c1.distance, c2.distance, c3.distance);
    const minY = Math.min(c1.y, c2.y, c3.y) - Math.max(c1.distance, c2.distance, c3.distance);
    
    if (x < minX || x > maxX || y < minY || y > maxY) {
        console.log("The found point goes beyond reasonable limits");
        return null;
    }
    
    return { x: x, y: y };
}


async function trilaterate(dirname, rssiData) {
    const beacons = await getBeacons(dirname);
    addRSSIData(beacons, rssiData);
    const sortedBeacons = sortBeaconsByRSSI(beacons);
    const topThreeBeacons = getTopThreeBeacons(sortedBeacons);
    
    const beaconsWithDistances = calculateBeaconDistances(topThreeBeacons);
    
    console.log("\nCircles for trilateration:");
    beaconsWithDistances.forEach((beacon, index) => {
        console.log(`Circle ${index + 1} (${beacon.name}):`);
        console.log(`  Center: (${beacon.x}, ${beacon.y})`);
        console.log(`  Raduis: ${beacon.distance.toFixed(2)} м`);
    });
    
    const estimatedPosition = trilaterateThreeCircles(beaconsWithDistances);
    
    if (estimatedPosition) {
        console.log(`\n Estimated location: (${estimatedPosition.x.toFixed(2)}, ${estimatedPosition.y.toFixed(2)})`);
    }
    
    console.log("\nAll the beacons:");
    sortedBeacons.forEach(beacon => {
        console.log(`${beacon.name}: X=${beacon.x}, Y=${beacon.y}, RSSI=${beacon.RSSI}`);
    });
    
    return {
        allBeacons: sortedBeacons,
        topThreeBeacons: topThreeBeacons,
        circles: beaconsWithDistances,
        estimatedPosition: estimatedPosition,
    };
}

// 1. Поставьте приемник на 1 метр от маячка
// 2. Измерьте RSSI 10-20 раз
// 3. Возьмите среднее

// function calibrateBeacon(beaconMac) {
//     const measurements = [-58, -59, -57, -60, -58, -59];
//     const averageRSSI = measurements.reduce((a, b) => a + b) / measurements.length;
    
//     beaconConfigs[beaconMac] = {
//         measuredPower: Math.round(averageRSSI), // ≈ -59
//         txPower: -4,
//         type: 'ESP32-BEACON'
//     };
    
//     return averageRSSI;
// }

const rssi = [
    ['beacon_1', -23],
    ['beacon_2', -45],
    ['beacon_3', -6]
]


trilaterate(".", rssi);