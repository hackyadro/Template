// Типы из вашей карты
export type Beacon = { id: string; x: number; y: number };

export type ParseError = { line: number; msg: string; raw: string };
export type ParseResult = {
	beacons: Beacon[];
	errors: ParseError[];
	bbox: { minX: number; maxX: number; minY: number; maxY: number } | null;
};

export type ParseOptions = {
	delimiter?: string;         // по умолчанию ';'
	decimal?: 'auto' | 'dot' | 'comma'; // автодетект запятой или точки
	headerCaseInsensitive?: boolean;    // по умолчанию true
};

/** Разбить строку с учётом кавычек (CSV-подобно) */
const splitWithQuotes = (line: string, delim: string): string[] => {
	const out: string[] = [];
	let cur = '';
	let inQuotes = false;

	for (let i = 0; i < line.length; i++) {
		const ch = line[i];

		if (ch === '"') {
			// двойные кавычки внутри поля -> одна кавычка
			if (inQuotes && line[i + 1] === '"') { cur += '"'; i++; continue; }
			inQuotes = !inQuotes;
			continue;
		}

		if (!inQuotes && ch === delim) { out.push(cur); cur = ''; continue; }
		cur += ch;
	}
	out.push(cur);
	return out;
};

const stripBOM = (s: string): string => (s.charCodeAt(0) === 0xFEFF ? s.slice(1) : s);

/** Нормализовать число: поддержка запятой как десятичного разделителя */
const parseNumber = (raw: string, mode: NonNullable<ParseOptions['decimal']>): number => {
	const t = raw.trim();
	if (!t) return NaN;
	if (mode === 'comma' || (mode === 'auto' && t.includes(',') && !t.includes('.'))) {
		return Number(t.replace(',', '.'));
	}
	return Number(t);
};

export const parseBeaconsCsv = (text: string, opts: ParseOptions = {}): ParseResult => {
	const delimiter = (opts.delimiter ?? ';');
	const decMode: NonNullable<ParseOptions['decimal']> = opts.decimal ?? 'auto';
	const hdrCI = opts.headerCaseInsensitive ?? true;

	const src = stripBOM(text);
	const lines = src.split(/\r?\n/);

	let headerIdx = -1;
	let cols: string[] = [];
	const errors: ParseError[] = [];
	const beacons: Beacon[] = [];

	// найти первую непустую строку как заголовок
	for (let i = 0; i < lines.length; i++) {
		const raw = lines[i]?.trim();
		if (!raw || raw.startsWith('#')) continue;
		cols = splitWithQuotes(raw, delimiter).map(s => s.trim());
		headerIdx = i;
		break;
	}
	if (headerIdx === -1) return { beacons, errors: [{ line: 0, msg: 'Файл пуст', raw: '' }], bbox: null };

	// ожидания по заголовкам
	const expect = ['Name', 'X', 'Y'];
	const norm = (s: string) => (hdrCI ? s.toLowerCase() : s);
	const colsNorm = cols.map(norm);

	const idxName = colsNorm.indexOf(norm('Name'));
	const idxX    = colsNorm.indexOf(norm('X'));
	const idxY    = colsNorm.indexOf(norm('Y'));

	if (idxName < 0 || idxX < 0 || idxY < 0) {
		errors.push({ line: headerIdx + 1, msg: `Нет требуемых столбцов: ${expect.join(', ')}`, raw: lines[headerIdx] ?? 'unk' });
		return { beacons, errors, bbox: null };
	}

	// строки данных
	for (let i = headerIdx + 1; i < lines.length; i++) {
		const raw = lines[i];
		if (!raw || /^\s*$/.test(raw) || raw.trim().startsWith('#')) continue;

		const cells = splitWithQuotes(raw, delimiter).map(s => s.trim());
		// допускаем лишние столбцы, берём нужные по индексам
		const name = (cells[idxName] ?? '').replace(/^"|"$/g, '').trim();
		const xStr = (cells[idxX] ?? '');
		const yStr = (cells[idxY] ?? '');

		const x = parseNumber(xStr, decMode);
		const y = parseNumber(yStr, decMode);

		if (!name) {
			errors.push({ line: i + 1, msg: 'Пустое имя маяка', raw });
			continue;
		}
		if (!isFinite(x) || !isFinite(y)) {
			errors.push({ line: i + 1, msg: `Некорректные координаты: X="${xStr}" Y="${yStr}"`, raw });
			continue;
		}

		beacons.push({ id: name, x, y });
	}

	const bbox = beacons.length
		? {
			minX: Math.min(...beacons.map(b => b.x)),
			maxX: Math.max(...beacons.map(b => b.x)),
			minY: Math.min(...beacons.map(b => b.y)),
			maxY: Math.max(...beacons.map(b => b.y)),
		}
		: null;

	return { beacons, errors, bbox };
};

/** Опционально: сдвинуть все координаты так, чтобы минимум стал (0,0) */
export const normalizeToOrigin = (beacons: Beacon[]) => {
	if (!beacons.length) return { beacons, offset: { x: 0, y: 0 } };
	const minX = Math.min(...beacons.map(b => b.x));
	const minY = Math.min(...beacons.map(b => b.y));
	const off = { x: -minX, y: -minY };
	return {
		beacons: beacons.map(b => ({ ...b, x: b.x + off.x, y: b.y + off.y })),
		offset: off,
	};
};
