
// Ответ сервера: либо { data: { positions: [...] } }, либо просто массив
import type {Beacon} from "./beaconsParser.ts";

type ServerBeacon =
	| { Name?: string; X?: number | string; Y?: number | string }
	| { name?: string; x?: number | string; y?: number | string };

type ServerResponse =
	| { data?: { positions?: ServerBeacon[] } }
	| { positions?: ServerBeacon[] }
	| ServerBeacon[];

// Парсер числа c поддержкой запятой
const toNum = (v: unknown): number => {
	if (typeof v === 'number') return v;
	if (typeof v === 'string') {
		const s = v.trim().replace(',', '.');
		const n = Number(s);
		return Number.isFinite(n) ? n : NaN;
	}
	return NaN;
};

/** Привести ответ сервера к массиву Beacon[]. */
export const adaptBeacons = (resp: ServerResponse): Beacon[] => {
	const arr: unknown =
		Array.isArray(resp) ? resp :
			('positions' in (resp ?? {}) ? (resp as any).positions :
				'data' in (resp ?? {}) ? (resp as any).data?.positions : undefined);

	if (!Array.isArray(arr)) return [];

	const out: Beacon[] = [];
	for (const it of arr as ServerBeacon[]) {
		const id = (it as any).Name ?? (it as any).name ?? '';
		const x = toNum((it as any).X ?? (it as any).x);
		const y = toNum((it as any).Y ?? (it as any).y);
		if (typeof id === 'string' && id.trim() && Number.isFinite(x) && Number.isFinite(y)) {
			out.push({id: id.trim(), x, y});
		}
	}
	return out;
};

/** Опционально: сдвинуть минимум в (0,0). */
export const normalizeToOrigin = (beacons: Beacon[]) => {
	if (!beacons.length) return {beacons, offset: {x: 0, y: 0}};
	const minX = Math.min(...beacons.map(b => b.x));
	const minY = Math.min(...beacons.map(b => b.y));
	const off = {x: -minX, y: -minY};
	return {
		beacons: beacons.map(b => ({...b, x: b.x + off.x, y: b.y + off.y})),
		offset: off,
	};
};
