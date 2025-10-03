export type Beacon = { id: string; x: number; y: number };
export type Point  = { x: number; y: number };
export type Room   = { w: number; h: number };

/** Текущие данные по маяку, прилетают с сервера */
export type BeaconData = {
	rssi?: number;   // dBm, выводим в подписи
	dist?: number;   // м, используем ТОЛЬКО для круга
};

export type RingOptions = {
	color?: string;          // цвет круга
	fillOpacity?: number;    // непрозрачность заливки
	strokeOpacity?: number;  // непрозрачность обводки
	min?: number;            // нижний предел радиуса (м), опционально
	max?: number;            // верхний предел радиуса (м), опционально
};
