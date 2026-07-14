import type { Workbook } from 'exceljs';
import type { Enquiry } from '../api/client';
import {
  activeOrderExtraItems,
  parseOrderNotes,
  resolveStyleForDate,
} from './orderNotes';
import {
  dishesForColumn,
  formatPaxTimeLine,
  resolveMenuColumns,
  sortMenuColumns,
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

function kitchenBannerNotes(dietary: string[]): string[] {
  const notes: string[] = [];
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

type SessionBlock = {
  label: string;
  paxLine: string;
  amount: number | null;
  dishNames: string[];
  fillSession: string;
};

type DayColumn = {
  date: string;
  sessions: SessionBlock[];
};

/**
 * One Excel column per service day. Breakfast, coffee, lunch, dinner for that
 * day stack top-to-bottom in the same column (Nithin / Muralidharan style).
 */
function buildDayColumns(
  enquiry: Enquiry,
  copyType: 'kitchen' | 'billing',
): DayColumn[] {
  const extras = parseOrderNotes(enquiry.notes);
  const menuItems = (enquiry.dishes ?? []).filter((d) => !PREFERENCE_CATEGORIES.has(d.category));
  const columns = sortMenuColumns(resolveMenuColumns(extras, enquiry, menuItems));

  const byDate = new Map<string, SessionBlock[]>();

  for (const column of columns) {
    const date = (column.date || enquiry.eventDate || '').slice(0, 10);
    if (!date) continue;
    const list = byDate.get(date) ?? [];
    list.push({
      label: column.sessionLabel,
      paxLine: formatPaxTimeLine(column) || (column.pax ? `${column.pax} Pax` : ''),
      amount: typeof column.amount === 'number' ? column.amount : null,
      dishNames: dishesForColumn(column, menuItems, extras).map((d) =>
        copyType === 'kitchen' && d.served ? `${d.dishName} ✓` : d.dishName,
      ),
      fillSession: FILL.session,
    });
    byDate.set(date, list);
  }

  const dayColumns: DayColumn[] = [...byDate.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, sessions]) => ({ date, sessions }));

  // Extras are rendered below the day columns (not mixed into meal sessions).

  if (dayColumns.length === 0) {
    dayColumns.push({
      date: (enquiry.eventDate || new Date().toISOString()).slice(0, 10),
      sessions: [
        {
          label: enquiry.eventType || 'Event',
          paxLine: enquiry.guestCount ? `${enquiry.guestCount} Pax` : '',
          amount: null,
          dishNames: ['No dishes added yet'],
          fillSession: FILL.session,
        },
      ],
    });
  }

  return dayColumns;
}

function activeExtrasAsBlocks(enquiry: Enquiry): SessionBlock[] {
  const extras = parseOrderNotes(enquiry.notes);
  if (!extras.extrasEnabled) return [];
  return activeOrderExtraItems(extras.extraItems).map((item) => ({
    label: item.title,
    paxLine: item.quantity?.trim() || '',
    amount: typeof item.amount === 'number' ? item.amount : null,
    dishNames: item.description ? [item.description] : [],
    fillSession: FILL.extra,
  }));
}

/**
 * Append a Menu sheet matching Nithin / Muralidharan wedding-menu Excels:
 * one column per day; all sessions that day stack in that column.
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
  const dayColumns = buildDayColumns(enquiry, copyType);
  const colCount = dayColumns.length;
  const border = thinBorder();
  const bold = { name: 'Calibri', size: 11, bold: true };
  const normal = { name: 'Calibri', size: 11 };
  const colWidth = 34;
  const totalCharsWide = Math.max(40, Math.floor(colWidth * colCount * 0.9));
  const perColChars = Math.floor(colWidth * 0.9);

  for (let i = 1; i <= colCount; i++) {
    ws.getColumn(i).width = colWidth;
  }

  // Row 1 — Client
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

  // Row 3 — one date per column
  ws.getRow(3).height = 20;
  dayColumns.forEach((day, i) => {
    const cell = ws.getCell(3, i + 1);
    cell.value = formatMenuDate(day.date);
    if (cell.value instanceof Date) cell.numFmt = 'yyyy-mm-dd';
    cell.font = bold;
    cell.alignment = alignCenter;
    cell.border = border;
  });

  // Row 4 — per-day cuisine style under each date (Kerala / Tamil Nadu / …)
  const hasDayStyles = dayColumns.some((day) => resolveStyleForDate(extras, day.date));
  let nextRow = 4;
  if (hasDayStyles) {
    ws.getRow(4).height = 20;
    dayColumns.forEach((day, i) => {
      const cell = ws.getCell(4, i + 1);
      const style = resolveStyleForDate(extras, day.date) || '';
      cell.value = style;
      cell.font = bold;
      cell.fill = solidFill(FILL.extra);
      cell.alignment = alignCenter;
      cell.border = border;
    });
    nextRow = 5;
  }

  const notes = kitchenBannerNotes(extras.dietary);
  let cursorStart = nextRow;
  if (notes.length > 0) {
    ws.mergeCells(nextRow, 1, nextRow, colCount);
    const noteText = notes.join(' — ');
    const noteCell = ws.getCell(nextRow, 1);
    noteCell.value = noteText;
    noteCell.font = { ...bold, color: { argb: 'FFFFFFFF' } };
    noteCell.fill = solidFill(FILL.note);
    noteCell.alignment = alignCenter;
    noteCell.border = border;
    ws.getRow(nextRow).height = wrappedRowHeight(noteText, totalCharsWide, 15, 28);
    cursorStart = nextRow + 1;
  }

  // Track max row used so we can border-fill empty cells evenly
  let maxRowUsed = cursorStart;

  dayColumns.forEach((day, i) => {
    const col = i + 1;
    let row = cursorStart;

    day.sessions.forEach((session, sessionIndex) => {
      if (sessionIndex > 0) {
        // Blank spacer between sessions in the same day column
        const spacer = ws.getCell(row, col);
        spacer.border = border;
        row += 1;
      }

      const sessionCell = ws.getCell(row, col);
      sessionCell.value = session.label;
      sessionCell.font = bold;
      sessionCell.fill = solidFill(session.fillSession);
      sessionCell.alignment = alignCenter;
      sessionCell.border = border;
      ws.getRow(row).height = Math.max(
        ws.getRow(row).height || 0,
        wrappedRowHeight(session.label, perColChars, 14, 22),
      );
      row += 1;

      const paxCell = ws.getCell(row, col);
      paxCell.value = session.paxLine;
      paxCell.font = bold;
      paxCell.fill = solidFill(FILL.pax);
      paxCell.alignment = alignCenter;
      paxCell.border = border;
      ws.getRow(row).height = Math.max(
        ws.getRow(row).height || 0,
        wrappedRowHeight(session.paxLine || ' ', perColChars, 14, 20),
      );
      row += 1;

      // Amounts only on order/billing copy — kitchen sees menu + pax only
      if (copyType !== 'kitchen') {
        const amountCell = ws.getCell(row, col);
        if (typeof session.amount === 'number' && session.amount > 0) {
          amountCell.value = session.amount;
          amountCell.numFmt = '#,##0';
        } else {
          amountCell.value = '';
        }
        amountCell.font = bold;
        amountCell.fill = solidFill(FILL.amount);
        amountCell.alignment = alignCenter;
        amountCell.border = border;
        ws.getRow(row).height = Math.max(ws.getRow(row).height || 0, 18);
        row += 1;
      }

      for (const name of session.dishNames) {
        const dishCell = ws.getCell(row, col);
        dishCell.value = name;
        dishCell.font = normal;
        dishCell.alignment = alignLeftMiddle;
        dishCell.border = border;
        ws.getRow(row).height = Math.max(ws.getRow(row).height || 0, 18);
        row += 1;
      }
    });

    maxRowUsed = Math.max(maxRowUsed, row - 1);
  });

  // Extras section below all day columns (Nithin / Muralidharan footer list style)
  const extraBlocks = activeExtrasAsBlocks(enquiry);
  if (extraBlocks.length > 0) {
    let row = maxRowUsed + 2;

    ws.mergeCells(row, 1, row, colCount);
    const extrasHead = ws.getCell(row, 1);
    extrasHead.value = 'Extras';
    extrasHead.font = bold;
    extrasHead.fill = solidFill(FILL.extra);
    extrasHead.alignment = alignCenter;
    extrasHead.border = border;
    for (let c = 1; c <= colCount; c++) {
      ws.getCell(row, c).fill = solidFill(FILL.extra);
      ws.getCell(row, c).border = border;
    }
    ws.getRow(row).height = 22;
    row += 1;

    for (const session of extraBlocks) {
      // Title spanning full width
      ws.mergeCells(row, 1, row, colCount);
      const titleCell = ws.getCell(row, 1);
      titleCell.value = session.label;
      titleCell.font = bold;
      titleCell.fill = solidFill(FILL.extra);
      titleCell.alignment = alignLeftMiddle;
      titleCell.border = border;
      for (let c = 1; c <= colCount; c++) {
        ws.getCell(row, c).fill = solidFill(FILL.extra);
        ws.getCell(row, c).border = border;
      }
      ws.getRow(row).height = wrappedRowHeight(session.label, totalCharsWide, 14, 20);
      row += 1;

      if (session.paxLine) {
        ws.mergeCells(row, 1, row, colCount);
        const qtyCell = ws.getCell(row, 1);
        qtyCell.value = session.paxLine;
        qtyCell.font = bold;
        qtyCell.fill = solidFill(FILL.pax);
        qtyCell.alignment = alignLeftMiddle;
        qtyCell.border = border;
        for (let c = 1; c <= colCount; c++) {
          ws.getCell(row, c).fill = solidFill(FILL.pax);
          ws.getCell(row, c).border = border;
        }
        ws.getRow(row).height = 18;
        row += 1;
      }

      if (copyType !== 'kitchen' && typeof session.amount === 'number' && session.amount > 0) {
        ws.mergeCells(row, 1, row, colCount);
        const amountCell = ws.getCell(row, 1);
        amountCell.value = session.amount;
        amountCell.numFmt = '#,##0';
        amountCell.font = bold;
        amountCell.fill = solidFill(FILL.amount);
        amountCell.alignment = alignLeftMiddle;
        amountCell.border = border;
        for (let c = 1; c <= colCount; c++) {
          ws.getCell(row, c).fill = solidFill(FILL.amount);
          ws.getCell(row, c).border = border;
        }
        ws.getRow(row).height = 18;
        row += 1;
      }

      for (const name of session.dishNames) {
        ws.mergeCells(row, 1, row, colCount);
        const dishCell = ws.getCell(row, 1);
        dishCell.value = name;
        dishCell.font = normal;
        dishCell.alignment = alignLeftMiddle;
        dishCell.border = border;
        for (let c = 1; c <= colCount; c++) {
          ws.getCell(row, c).border = border;
        }
        ws.getRow(row).height = 18;
        row += 1;
      }

      row += 1; // spacer between extras
    }

    maxRowUsed = row - 1;
  }

  // Header / note fills across merge width
  for (let c = 1; c <= colCount; c++) {
    ws.getCell(1, c).fill = solidFill(FILL.header);
    ws.getCell(1, c).alignment = alignCenter;
    ws.getCell(1, c).border = border;
    ws.getCell(2, c).fill = solidFill(FILL.header);
    ws.getCell(2, c).alignment = alignCenter;
    ws.getCell(2, c).border = border;
  }

  // Light borders on empty cells so day columns align to the same height
  for (let r = cursorStart; r <= maxRowUsed; r++) {
    for (let c = 1; c <= colCount; c++) {
      const cell = ws.getCell(r, c);
      if (!cell.border) cell.border = border;
      if (cell.value == null || cell.value === '') {
        if (!cell.alignment) cell.alignment = alignLeftMiddle;
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
