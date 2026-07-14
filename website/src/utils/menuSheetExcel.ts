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

function formatMenuDate(iso: string): Date | string {
  const d = new Date(iso.includes('T') ? iso : `${iso}T00:00:00`);
  if (Number.isNaN(d.getTime())) return iso;
  return d;
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

  for (let i = 1; i <= colCount; i++) {
    ws.getColumn(i).width = i === 1 ? 28 : 34;
  }

  ws.mergeCells(1, 1, 1, colCount);
  ws.getRow(1).height = 22;
  const c1 = ws.getCell(1, 1);
  c1.value = clientTitle(enquiry);
  c1.font = bold;
  c1.fill = solidFill(FILL.header);
  c1.alignment = { vertical: 'middle', horizontal: 'left', wrapText: true };

  ws.mergeCells(2, 1, 2, colCount);
  ws.getRow(2).height = 20;
  const c2 = ws.getCell(2, 1);
  c2.value = enquiry.eventLocation || 'Venue TBD';
  c2.font = bold;
  c2.fill = solidFill(FILL.header);
  c2.alignment = { vertical: 'middle', horizontal: 'left' };

  ws.getRow(3).height = 18;
  sheetCols.forEach((col, i) => {
    const cell = ws.getCell(3, i + 1);
    const raw = col.column?.date || enquiry.eventDate || '';
    cell.value = raw ? formatMenuDate(raw) : '';
    if (cell.value instanceof Date) cell.numFmt = 'yyyy-mm-dd';
    cell.font = bold;
    cell.alignment = { horizontal: 'center', vertical: 'middle' };
  });

  const notes: string[] = [];
  if (extras.regionalStyle?.trim()) notes.push(`Style: ${extras.regionalStyle.trim()}`);
  if (extras.dietary.length) notes.push(extras.dietary.join(', '));
  let dataStart = 4;
  if (notes.length > 0) {
    ws.mergeCells(4, 1, 4, colCount);
    ws.getRow(4).height = 20;
    const noteCell = ws.getCell(4, 1);
    noteCell.value = notes.join(' — ');
    noteCell.font = { ...bold, color: { argb: 'FFFFFFFF' } };
    noteCell.fill = solidFill(FILL.note);
    noteCell.alignment = { vertical: 'middle', wrapText: true };
    dataStart = 5;
  }

  const sessionRow = dataStart;
  const paxRow = dataStart + 1;
  const amountRow = dataStart + 2;
  const dishStart = dataStart + 3;

  let maxDishes = 0;
  sheetCols.forEach((col, i) => {
    const c = i + 1;

    const sessionCell = ws.getCell(sessionRow, c);
    sessionCell.value = col.column?.sessionLabel || col.extraTitle || 'Extras';
    sessionCell.font = bold;
    sessionCell.fill = solidFill(col.column ? FILL.session : FILL.extra);
    sessionCell.alignment = { horizontal: 'center', vertical: 'middle', wrapText: true };
    sessionCell.border = border;

    const paxCell = ws.getCell(paxRow, c);
    if (col.column) {
      paxCell.value = formatPaxTimeLine(col.column) || (col.column.pax ? `${col.column.pax} Pax` : '');
    } else {
      paxCell.value = col.extraQty?.trim() || '';
    }
    paxCell.font = bold;
    paxCell.fill = solidFill(FILL.pax);
    paxCell.alignment = { horizontal: 'center', vertical: 'middle', wrapText: true };
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
    amountCell.alignment = { horizontal: 'center', vertical: 'middle' };
    amountCell.border = border;

    col.dishNames.forEach((name, di) => {
      const dishCell = ws.getCell(dishStart + di, c);
      dishCell.value = name;
      dishCell.font = normal;
      dishCell.alignment = { horizontal: 'left', vertical: 'middle', wrapText: true };
      dishCell.border = border;
    });
    maxDishes = Math.max(maxDishes, col.dishNames.length);
  });

  ws.getRow(sessionRow).height = 22;
  ws.getRow(paxRow).height = 20;
  ws.getRow(amountRow).height = 18;

  for (let c = 1; c <= colCount; c++) {
    ws.getCell(1, c).fill = solidFill(FILL.header);
    ws.getCell(1, c).border = border;
    ws.getCell(2, c).fill = solidFill(FILL.header);
    ws.getCell(2, c).border = border;
    ws.getCell(3, c).border = border;
  }

  for (let r = dishStart; r < dishStart + Math.max(maxDishes, 1); r++) {
    for (let c = 1; c <= colCount; c++) {
      const cell = ws.getCell(r, c);
      if (cell.value == null || cell.value === '') {
        cell.border = border;
      }
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
