import {
  formatEventDateRangeLabel,
  formatMenuExcelDateText,
  normalizeDateOnly,
  todayDateOnlyLocal,
} from './dateOnly';
import type { Workbook, Worksheet } from 'exceljs';
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
import { isKitchenSpecification, kitchenSpecificationNotes } from './kitchenSpecs';
import { normalizeMapUrl, qrCodeDataUrl } from './qrCode';

/** Colours from Nithin / Muralidharan wedding menu Excels */
const FILL = {
  header: 'FFB8CCE4',
  session: 'FFFFC000',
  pax: 'FFFFFF00',
  amount: 'FFFFFF66',
  note: 'FFFF0000',
  counter: 'FF92D050',
  subtotal: 'FFFFFF00',
} as const;

const FONT_RED = 'FFFF0000';

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

function clientTitle(enquiry: Enquiry, dayDates: string[]): string {
  const datePart = dayDates.length > 0
    ? ` ${formatEventDateRangeLabel(dayDates)}`
    : enquiry.eventDate
      ? ` ${formatEventDateRangeLabel([enquiry.eventDate])}`
      : '';
  const event = enquiry.eventType ? ` ${enquiry.eventType}` : '';
  return `Client : ${enquiry.customerName}${event}${datePart}`;
}

/** Green fill for counter / course sub-headers (Welcome Drink, Main Course, …). */
function isCounterSubHeader(label: string): boolean {
  return /\b(counter|welcome drink|main course|dosa counter|chat|chaat|juice counter)\b/i.test(label);
}

type SessionBlock = {
  label: string;
  /** Buffet / Plantain leaf / Thali — printed on kitchen + order copies */
  servingStyle: string;
  paxLine: string;
  amount: number | null;
  dishNames: string[];
  fillSession: string;
  /** Extra / ritual titles that print in red (Garlands, …) */
  titleIsSpec: boolean;
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
  copyType: 'kitchen' | 'billing' | 'ours',
  amountScale = 1,
): DayColumn[] {
  const extras = parseOrderNotes(enquiry.notes);
  const menuItems = (enquiry.dishes ?? []).filter((d) => !PREFERENCE_CATEGORIES.has(d.category));
  const columns = sortMenuColumns(resolveMenuColumns(extras, enquiry, menuItems));

  const byDate = new Map<string, SessionBlock[]>();

  for (const column of columns) {
    const date = normalizeDateOnly(column.date || enquiry.eventDate);
    if (!date) continue;
    const list = byDate.get(date) ?? [];
    const label = column.sessionLabel;
    const rawAmount = typeof column.amount === 'number' ? column.amount : null;
    list.push({
      label,
      servingStyle: column.servingStyle?.trim() || '',
      paxLine: formatPaxTimeLine(column) || (column.pax ? `${column.pax} Pax` : ''),
      amount:
        rawAmount != null ? Math.round(rawAmount * amountScale * 100) / 100 : null,
      dishNames: dishesForColumn(column, menuItems, extras, columns).map((d) =>
        copyType === 'kitchen' && d.served ? `${d.dishName} ✓` : d.dishName,
      ),
      fillSession: isCounterSubHeader(label) ? FILL.counter : FILL.session,
      titleIsSpec: false,
    });
    byDate.set(date, list);
  }

  const dayColumns: DayColumn[] = [...byDate.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, sessions]) => ({ date, sessions }));

  if (dayColumns.length === 0) {
    dayColumns.push({
      date: normalizeDateOnly(enquiry.eventDate) || todayDateOnlyLocal(),
      sessions: [
        {
          label: enquiry.eventType || 'Event',
          servingStyle: '',
          paxLine: enquiry.guestCount ? `${enquiry.guestCount} Pax` : '',
          amount: null,
          dishNames: ['No dishes added yet'],
          fillSession: FILL.session,
          titleIsSpec: false,
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
    servingStyle: '',
    paxLine: item.quantity?.trim() || '',
    amount: typeof item.amount === 'number' ? item.amount : null,
    dishNames: item.description
      ? item.description
          .split('\n')
          .map((line) => line.trim())
          .filter(Boolean)
      : [],
    // Same orange session chrome as meal blocks in Excel downloads
    fillSession: FILL.session,
    titleIsSpec: isKitchenSpecification(item.title) || isKitchenSpecification(item.description || ''),
  }));
}

function paintMergedRow(
  ws: Worksheet,
  row: number,
  colCount: number,
  value: string,
  opts: {
    fill?: string;
    font?: { name?: string; size?: number; bold?: boolean; color?: { argb: string } };
    align?: typeof alignCenter | typeof alignLeftMiddle;
    height?: number;
  },
) {
  const border = thinBorder();
  ws.mergeCells(row, 1, row, colCount);
  const cell = ws.getCell(row, 1);
  cell.value = value;
  cell.font = opts.font ?? { name: 'Calibri', size: 11, bold: true };
  if (opts.fill) cell.fill = solidFill(opts.fill);
  cell.alignment = opts.align ?? alignCenter;
  cell.border = border;
  for (let c = 1; c <= colCount; c++) {
    const side = ws.getCell(row, c);
    if (opts.fill) side.fill = solidFill(opts.fill);
    side.border = border;
    side.alignment = opts.align ?? alignCenter;
  }
  if (opts.height) ws.getRow(row).height = opts.height;
}

/**
 * Append a Menu sheet matching Nithin / Muralidharan wedding-menu Excels:
 * one column per day; all sessions that day stack in that column.
 */
export async function appendMenuSheet(
  wb: Workbook,
  enquiry: Enquiry,
  copyType: 'kitchen' | 'billing' | 'ours',
  opts?: { amountScale?: number },
) {
  const amountScale = opts?.amountScale ?? (copyType === 'ours' ? 0.5 : 1);
  const ws = wb.addWorksheet('Menu', {
    views: [{ state: 'frozen', ySplit: 3, showGridLines: true }],
  });

  const extras = parseOrderNotes(enquiry.notes);
  const dayColumns = buildDayColumns(enquiry, copyType, amountScale);
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

  // Row 1 — Client (light blue)
  const title = clientTitle(enquiry, dayColumns.map((d) => d.date));
  paintMergedRow(ws, 1, colCount, title, {
    fill: FILL.header,
    font: bold,
    height: wrappedRowHeight(title, totalCharsWide, 16, 24),
  });

  // Row 2 — Venue (light blue)
  const venueText = enquiry.eventLocation || 'Venue TBD';
  paintMergedRow(ws, 2, colCount, venueText, {
    fill: FILL.header,
    font: bold,
    height: wrappedRowHeight(venueText, totalCharsWide, 15, 22),
  });

  // Row 3 — one date per column
  ws.getRow(3).height = 22;
  dayColumns.forEach((day, i) => {
    const cell = ws.getCell(3, i + 1);
    cell.value = formatMenuExcelDateText(day.date);
    cell.font = bold;
    cell.alignment = alignCenter;
    cell.border = border;
  });

  // Row 4 — per-day cuisine style (green)
  const hasDayStyles = dayColumns.some((day) => resolveStyleForDate(extras, day.date));
  let nextRow = 4;
  if (hasDayStyles) {
    ws.getRow(4).height = 20;
    dayColumns.forEach((day, i) => {
      const cell = ws.getCell(4, i + 1);
      const style = resolveStyleForDate(extras, day.date) || '';
      cell.value = style;
      cell.font = bold;
      cell.fill = solidFill(FILL.counter);
      cell.alignment = alignCenter;
      cell.border = border;
    });
    nextRow = 5;
  }

  // Specifications / dietary — red banner (allergy) like Muralidharan sheet
  const notes = kitchenSpecificationNotes(extras.dietary);
  let cursorStart = nextRow;
  if (notes.length > 0) {
    const noteText = notes.join(' — ');
    paintMergedRow(ws, nextRow, colCount, noteText, {
      fill: FILL.note,
      font: { name: 'Calibri', size: 12, bold: true, color: { argb: 'FF000000' } },
      height: wrappedRowHeight(noteText, totalCharsWide, 15, 28),
    });
    cursorStart = nextRow + 1;
  }

  let maxRowUsed = cursorStart;

  dayColumns.forEach((day, i) => {
    const col = i + 1;
    let row = cursorStart;

    day.sessions.forEach((session, sessionIndex) => {
      if (sessionIndex > 0) {
        const spacer = ws.getCell(row, col);
        spacer.border = border;
        row += 1;
      }

      // Session header — orange (or green for counters)
      const sessionCell = ws.getCell(row, col);
      sessionCell.value = session.label;
      sessionCell.font = isKitchenSpecification(session.label)
        ? { ...bold, color: { argb: FONT_RED } }
        : bold;
      sessionCell.fill = solidFill(session.fillSession);
      sessionCell.alignment = alignCenter;
      sessionCell.border = border;
      ws.getRow(row).height = Math.max(
        ws.getRow(row).height || 0,
        wrappedRowHeight(session.label, perColChars, 14, 22),
      );
      row += 1;

      // Serving style (Buffet / Plantain leaf / Thali) — kitchen + order copies
      if (session.servingStyle) {
        const styleCell = ws.getCell(row, col);
        styleCell.value = session.servingStyle;
        styleCell.font = bold;
        styleCell.fill = solidFill(FILL.pax);
        styleCell.alignment = alignCenter;
        styleCell.border = border;
        ws.getRow(row).height = Math.max(ws.getRow(row).height || 0, 20);
        row += 1;
      }

      // Pax / time — bright yellow
      if (session.paxLine) {
        const paxCell = ws.getCell(row, col);
        paxCell.value = session.paxLine;
        paxCell.font = bold;
        paxCell.fill = solidFill(FILL.pax);
        paxCell.alignment = alignCenter;
        paxCell.border = border;
        ws.getRow(row).height = Math.max(
          ws.getRow(row).height || 0,
          wrappedRowHeight(session.paxLine, perColChars, 14, 20),
        );
        row += 1;
      }

      // Amounts only on order/billing copy
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
        dishCell.font = isKitchenSpecification(name)
          ? { ...bold, color: { argb: FONT_RED } }
          : normal;
        dishCell.alignment = alignLeftMiddle;
        dishCell.border = border;
        ws.getRow(row).height = Math.max(ws.getRow(row).height || 0, 18);
        row += 1;
      }
    });

    maxRowUsed = Math.max(maxRowUsed, row - 1);
  });

  // Sub Total bar (yellow) then extras — matches reference footer break
  const extraBlocks = activeExtrasAsBlocks(enquiry);
  if (extraBlocks.length > 0) {
    let row = maxRowUsed + 2;

    paintMergedRow(ws, row, colCount, 'Sub Total', {
      fill: FILL.subtotal,
      font: bold,
      height: 22,
    });
    row += 1;

    for (const session of extraBlocks) {
      // Blue band (same as day-date header) so extras match meal color chrome in Excel
      paintMergedRow(ws, row, colCount, 'Extras', {
        fill: FILL.header,
        font: bold,
        height: 20,
      });
      row += 1;

      const titleIsRed = session.titleIsSpec || isKitchenSpecification(session.label);
      paintMergedRow(ws, row, colCount, session.label, {
        fill: titleIsRed ? undefined : session.fillSession,
        font: titleIsRed
          ? { name: 'Calibri', size: 11, bold: true, color: { argb: FONT_RED } }
          : bold,
        height: wrappedRowHeight(session.label, totalCharsWide, 14, 22),
      });
      row += 1;

      if (session.paxLine) {
        paintMergedRow(ws, row, colCount, session.paxLine, {
          fill: FILL.pax,
          font: bold,
          height: 20,
        });
        row += 1;
      }

      if (copyType !== 'kitchen' && typeof session.amount === 'number' && session.amount > 0) {
        ws.mergeCells(row, 1, row, colCount);
        const amountCell = ws.getCell(row, 1);
        amountCell.value = session.amount;
        amountCell.numFmt = '#,##0';
        amountCell.font = bold;
        amountCell.fill = solidFill(FILL.amount);
        amountCell.alignment = alignCenter;
        amountCell.border = border;
        for (let c = 1; c <= colCount; c++) {
          ws.getCell(row, c).fill = solidFill(FILL.amount);
          ws.getCell(row, c).border = border;
          ws.getCell(row, c).alignment = alignCenter;
        }
        ws.getRow(row).height = 18;
        row += 1;
      }

      for (const name of session.dishNames) {
        const lineIsSpec = isKitchenSpecification(name);
        paintMergedRow(ws, row, colCount, name, {
          font: lineIsSpec
            ? { name: 'Calibri', size: 11, bold: true, color: { argb: FONT_RED } }
            : normal,
          align: alignLeftMiddle,
          height: 18,
        });
        row += 1;
      }

      row += 1;
    }

    maxRowUsed = row - 1;
  }

  // Kitchen only: venue QR at the very bottom (after menu + extras)
  if (copyType === 'kitchen') {
    maxRowUsed = await appendVenueMapQr(wb, ws, extras.venueMapLink, maxRowUsed, colCount, totalCharsWide);
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

/** Place venue QR + link below everything else on the kitchen Menu sheet. */
async function appendVenueMapQr(
  wb: Workbook,
  ws: Worksheet,
  mapLink: string | null | undefined,
  maxRowUsed: number,
  colCount: number,
  totalCharsWide: number,
): Promise<number> {
  const mapUrl = normalizeMapUrl(mapLink ?? '');
  if (!mapUrl) return maxRowUsed;

  const border = thinBorder();
  const bold = { name: 'Calibri', size: 11, bold: true };
  let row = maxRowUsed + 2;

  paintMergedRow(ws, row, colCount, 'Venue — scan for directions', {
    fill: FILL.header,
    font: bold,
    height: 22,
  });
  row += 1;

  const dataUrl = await qrCodeDataUrl(mapUrl, 200);
  const base64 = dataUrl.replace(/^data:image\/png;base64,/, '');
  if (!base64) return row - 1;

  const imageId = wb.addImage({ base64, extension: 'png' });
  const qrSize = 150;
  const colWidthPx = Math.floor(34 * 7 + 5);
  const totalWidthPx = colWidthPx * colCount;
  const xPad = Math.max(0, (totalWidthPx - qrSize) / 2);
  let tlCol = 0;
  let remaining = xPad;
  for (let i = 0; i < colCount; i += 1) {
    if (remaining <= colWidthPx) {
      tlCol = i + remaining / colWidthPx;
      break;
    }
    remaining -= colWidthPx;
  }

  const qrRowSpan = 9;
  ws.addImage(imageId, {
    tl: { col: tlCol, row: row - 1 },
    ext: { width: qrSize, height: qrSize },
    editAs: 'oneCell',
  });

  for (let r = 0; r < qrRowSpan; r += 1) {
    ws.getRow(row + r).height = 18;
    for (let c = 1; c <= colCount; c += 1) {
      ws.getCell(row + r, c).border = border;
    }
  }
  row += qrRowSpan;

  paintMergedRow(ws, row, colCount, mapUrl, {
    font: { name: 'Calibri', size: 9 },
    align: alignCenter,
    height: wrappedRowHeight(mapUrl, totalCharsWide, 12, 18),
  });

  return row;
}

/** Standalone Menu workbook (kitchen download). */
export async function buildMenuSheetWorkbook(enquiry: Enquiry, copyType: 'kitchen' | 'billing') {
  const ExcelJS = (await import('exceljs')).default;
  const wb = new ExcelJS.Workbook();
  wb.creator = 'Srivatsanka Events and Services';
  await appendMenuSheet(wb, enquiry, copyType);
  return wb;
}
