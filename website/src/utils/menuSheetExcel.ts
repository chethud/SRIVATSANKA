import type { Workbook } from 'exceljs';
import type { Enquiry } from '../api/client';
import {
  activeOrderExtraItems,
  parseOrderNotes,
  type MenuColumn,
} from './orderNotes';
import {
  dishesForColumn,
  formatPaxTimeLine,
  resolveMenuColumns,
} from './orderMenuGrid';
import { PREFERENCE_CATEGORIES } from './mealSessions';

/** Colours from Nithin / Muralidharan wedding menu Excels */
const FILL = {
  header: 'FFB8CCE4',
  session: 'FFFFC000',
  pax: 'FFFFFF00',
  amount: 'FFFFFF66',
  note: 'FFFF0000',
  extra: 'FF92D050',
} as const;

function solidFill(argb: string) {
  return {
    type: 'pattern' as const,
    pattern: 'solid' as const,
    fgColor: { argb },
  };
}

function thinBorder() {
  const side = { style: 'thin' as const, color: { argb: 'FF000000' } };
  return { top: side, left: side, bottom: side, right: side };
}

const alignCenter = {
  horizontal: 'center' as const,
  vertical: 'middle' as const,
  wrapText: true,
};

const alignLeftMiddle = {
  horizontal: 'left' as const,
  vertical: 'middle' as const,
  wrapText: true,
};

/** Approximate Excel row height so wrapped text is not clipped. */
function wrappedRowHeight(text: string, charsPerLine: number, linePx = 15, min = 22): number {
  const lines = String(text || '')
    .split(/\n/)
    .reduce((sum, part) => sum + Math.max(1, Math.ceil(part.length / Math.max(charsPerLine, 1))), 0);
  return Math.max(min, lines * linePx + 6);
}

function formatMenuDate(iso: string): Date | string {
  const d = new Date(iso.includes('T') ? iso : `${iso}T00:00:00`);
  if (Number.isNaN(d.getTime())) return iso;
  return d;
}

/** Keep only short kitchen-useful notes; skip bot CRM callback/date chatter. */
function kitchenBannerNotes(regionalStyle: string | null | undefined, dietary: string[]): string[] {
  const notes: string[] = [];
  if (regionalStyle?.trim()) notes.push(`Style: ${regionalStyle.trim()}`);
  for (const item of dietary) {
    const t = item.trim();
    if (!t) continue;
    if (/callback|occasion date|scheduled|requested:/i.test(t)) continue;
    if (t.length > 120) continue;
    notes.push(t);
  }
  return notes;
}

function clientTitle(enquiry: Enquiry): string {
  const datePart = enquiry.eventDate
    ? (() => {
        const d = new Date(enquiry.eventDate);
        if (Number.isNaN(d.getTime())) return '';
        return ` ${d.toLocaleString('en-IN', { month: 'short', day: 'numeric', year: 'numeric' })}`;
      })()
    : '';
  const event = enquiry.eventType ? ` ${enquiry.eventType}` : '';
  return `Client : ${enquiry.customerName}${event}${datePart}`;
}

type SheetCol = {
  column: MenuColumn | null;
  dishNames: string[];
  extraTitle?: string;
  extraQty?: string;
  extraAmount?: number | null;
};

/**
 * Append a Menu sheet matching Nithin / Muralidharan wedding-menu Excels.
 */
export async function appendMenuSheet(
  wb: Workbook,
  enquiry: Enquiry,
  copyType: 'kitchen' | 'billing',
) {
  const ws = wb.addWorksheet('Menu', {
    views: [{ showGridLines: true }],
  });

  const extras = parseOrderNotes(enquiry.notes);
  const menuItems = (enquiry.dishes ?? []).filter((d) => !PREFERENCE_CATEGORIES.has(d.category));
  const columns = resolveMenuColumns(extras, enquiry, menuItems);

  const sheetCols: SheetCol[] = columns.map((column) => ({
    column,
    dishNames: dishesForColumn(column, menuItems, extras).map((d) =>
      copyType === 'kitchen' && d.served ? `${d.dishName} ✓` : d.dishName,
    ),
  }));

  if (extras.extrasEnabled) {
    for (const item of activeOrderExtraItems(extras.extraItems)) {
      sheetCols.push({
        column: null,
        dishNames: item.description ? [item.description] : [],
        extraTitle: item.title,
        extraQty: item.quantity,
        extraAmount: item.amount ?? null,
      });
    }
  }

  if (sheetCols.length === 0) {
    sheetCols.push({
      column: {
        id: 'empty',
        date: enquiry.eventDate?.slice(0, 10) || new Date().toISOString().slice(0, 10),
        sessionLabel: enquiry.eventType || 'Event',
        baseSession: 'Lunch',
        pax: enquiry.guestCount ?? null,
        timeFrom: null,
        timeTo: null,
        amount: null,
      },
      dishNames: ['No dishes added yet'],
    });
  }

  const colCount = sheetCols.length;
  const border = thinBorder();
  const bold = { name: 'Calibri', size: 11, bold: true };
  const normal = { name: 'Calibri', size: 11 };
  const colWidth = 34;
  const totalCharsWide = Math.max(40, Math.floor(colWidth * colCount * 0.9));

  for (let i = 1; i <= colCount; i++) {
    ws.getColumn(i).width = colWidth;
  }

  // Row 1 — Client (centered, auto-height)
  ws.mergeCells(1, 1, 1, colCount);
  const clientText = clientTitle(enquiry);
  const c1 = ws.getCell(1, 1);
  c1.value = clientText;
  c1.font = bold;
  c1.fill = solidFill(FILL.header);
  c1.alignment = alignCenter;
  c1.border = border;
  ws.getRow(1).height = wrappedRowHeight(clientText, totalCharsWide, 16, 24);

  // Row 2 — Venue
  ws.mergeCells(2, 1, 2, colCount);
  const venueText = enquiry.eventLocation || 'Venue TBD';
  const c2 = ws.getCell(2, 1);
  c2.value = venueText;
  c2.font = bold;
  c2.fill = solidFill(FILL.header);
  c2.alignment = alignCenter;
  c2.border = border;
  ws.getRow(2).height = wrappedRowHeight(venueText, totalCharsWide, 15, 22);

  // Row 3 — Dates
  ws.getRow(3).height = 20;
  sheetCols.forEach((col, i) => {
    const cell = ws.getCell(3, i + 1);
    const raw = col.column?.date || enquiry.eventDate || '';
    cell.value = raw ? formatMenuDate(raw) : '';
    if (cell.value instanceof Date) cell.numFmt = 'yyyy-mm-dd';
    cell.font = bold;
    cell.alignment = alignCenter;
    cell.border = border;
  });

  const notes = kitchenBannerNotes(extras.regionalStyle, extras.dietary);
  let dataStart = 4;
  if (notes.length > 0) {
    ws.mergeCells(4, 1, 4, colCount);
    const noteText = notes.join(' — ');
    const noteCell = ws.getCell(4, 1);
    noteCell.value = noteText;
    noteCell.font = { ...bold, color: { argb: 'FFFFFFFF' } };
    noteCell.fill = solidFill(FILL.note);
    noteCell.alignment = alignCenter;
    noteCell.border = border;
    ws.getRow(4).height = wrappedRowHeight(noteText, totalCharsWide, 15, 28);
    dataStart = 5;
  }

  const sessionRow = dataStart;
  const paxRow = dataStart + 1;
  const amountRow = dataStart + 2;
  const dishStart = dataStart + 3;

  let maxDishes = 0;
  let maxSessionLen = 0;
  let maxPaxLen = 0;

  sheetCols.forEach((col, i) => {
    const c = i + 1;

    const sessionLabel = col.column?.sessionLabel || col.extraTitle || 'Extras';
    maxSessionLen = Math.max(maxSessionLen, sessionLabel.length);
    const sessionCell = ws.getCell(sessionRow, c);
    sessionCell.value = sessionLabel;
    sessionCell.font = bold;
    sessionCell.fill = solidFill(col.column ? FILL.session : FILL.extra);
    sessionCell.alignment = alignCenter;
    sessionCell.border = border;

    const paxText = col.column
      ? formatPaxTimeLine(col.column) || (col.column.pax ? `${col.column.pax} Pax` : '')
      : col.extraQty?.trim() || '';
    maxPaxLen = Math.max(maxPaxLen, paxText.length);
    const paxCell = ws.getCell(paxRow, c);
    paxCell.value = paxText;
    paxCell.font = bold;
    paxCell.fill = solidFill(FILL.pax);
    paxCell.alignment = alignCenter;
    paxCell.border = border;

    const amountCell = ws.getCell(amountRow, c);
    const amount = col.column ? col.column.amount : col.extraAmount;
    if (typeof amount === 'number' && amount > 0) {
      amountCell.value = amount;
      amountCell.numFmt = '#,##0';
    } else {
      amountCell.value = '';
    }
    amountCell.font = bold;
    amountCell.fill = solidFill(FILL.amount);
    amountCell.alignment = alignCenter;
    amountCell.border = border;

    col.dishNames.forEach((name, di) => {
      const dishCell = ws.getCell(dishStart + di, c);
      dishCell.value = name;
      dishCell.font = normal;
      dishCell.alignment = alignLeftMiddle;
      dishCell.border = border;
    });
    maxDishes = Math.max(maxDishes, col.dishNames.length);
  });

  const perColChars = Math.floor(colWidth * 0.9);
  ws.getRow(sessionRow).height = wrappedRowHeight('x'.repeat(maxSessionLen), perColChars, 14, 24);
  ws.getRow(paxRow).height = wrappedRowHeight('x'.repeat(maxPaxLen), perColChars, 14, 22);
  ws.getRow(amountRow).height = 20;

  // Paint merged header / note cells across the full width
  for (let c = 1; c <= colCount; c++) {
    ws.getCell(1, c).fill = solidFill(FILL.header);
    ws.getCell(1, c).alignment = alignCenter;
    ws.getCell(1, c).border = border;
    ws.getCell(2, c).fill = solidFill(FILL.header);
    ws.getCell(2, c).alignment = alignCenter;
    ws.getCell(2, c).border = border;
    if (notes.length > 0) {
      ws.getCell(4, c).fill = solidFill(FILL.note);
      ws.getCell(4, c).alignment = alignCenter;
      ws.getCell(4, c).border = border;
    }
  }

  for (let r = dishStart; r < dishStart + Math.max(maxDishes, 1); r++) {
    ws.getRow(r).height = 18;
    for (let c = 1; c <= colCount; c++) {
      const cell = ws.getCell(r, c);
      cell.alignment = alignLeftMiddle;
      cell.border = border;
    }
  }

  return ws;
}

/** Standalone Menu workbook (kitchen download). */
export async function buildMenuSheetWorkbook(enquiry: Enquiry, copyType: 'kitchen' | 'billing') {
  const ExcelJS = (await import('exceljs')).default;
  const wb = new ExcelJS.Workbook();
  wb.creator = 'SRIVATSANKA EVENTS';
  await appendMenuSheet(wb, enquiry, copyType);
  return wb;
}
