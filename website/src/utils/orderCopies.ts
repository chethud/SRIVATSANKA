import type { Enquiry } from '../api/client';
import { formatDate } from '../api/client';
import {
  activeOrderExtraItems,
  parseOrderNotes,
  sumExtraItemAmounts,
} from './orderNotes';
import {
  dishesForColumn,
  formatColumnAmount,
  formatPaxTimeLine,
  resolveMenuColumns,
  sumOrderCopyTotals,
} from './orderMenuGrid';
import { PREFERENCE_CATEGORIES } from './mealSessions';

function sanitizeFilename(name: string): string {
  return name.replace(/[^\w\s-]/g, '').replace(/\s+/g, '-').slice(0, 80) || 'order';
}

async function waitForImages(root: HTMLElement): Promise<void> {
  const images = Array.from(root.querySelectorAll('img'));
  if (images.length === 0) return;

  await Promise.all(
    images.map(
      (img) =>
        new Promise<void>((resolve) => {
          if (img.complete) resolve();
          else {
            img.addEventListener('load', () => resolve(), { once: true });
            img.addEventListener('error', () => resolve(), { once: true });
          }
        }),
    ),
  );
}

function buildCopyRows(enquiry: Enquiry, copyType: 'kitchen' | 'billing'): (string | number)[][] {
  const title = copyType === 'kitchen' ? 'Kitchen Copy' : 'Order Copy';
  const extras = parseOrderNotes(enquiry.notes);
  const menuItems = (enquiry.dishes ?? []).filter((d) => !PREFERENCE_CATEGORIES.has(d.category));
  const columns = resolveMenuColumns(extras, enquiry, menuItems);

  const rows: (string | number)[][] = [
    ['SRIVATSANKA'],
    [title],
    [],
    ['Client', enquiry.customerName],
    ['Event', enquiry.eventType || ''],
    ['Location', enquiry.eventLocation || ''],
    ['Event date', formatDate(enquiry.eventDate)],
    ['Phone', enquiry.phoneNumber || ''],
    ['Guests', enquiry.guestCount ?? ''],
  ];

  if (copyType === 'kitchen' && extras.regionalStyle?.trim()) {
    rows.push(['Regional style', extras.regionalStyle.trim()]);
  }

  rows.push([]);

  if (columns.length === 0) {
    rows.push(['No dishes on this order yet.']);
  } else {
    for (const col of columns) {
      const items = dishesForColumn(col, menuItems, extras);
      const paxLine = formatPaxTimeLine(col);
      rows.push(['Date', formatDate(col.date)]);
      rows.push(['Session', col.sessionLabel]);
      if (paxLine) rows.push(['Pax / time', paxLine]);
      rows.push(['#', 'Dish', ...(copyType === 'kitchen' ? ['Served'] : [])]);
      if (items.length === 0) {
        rows.push(['', '—']);
      } else {
        items.forEach((d, i) => {
          if (copyType === 'kitchen') {
            rows.push([i + 1, d.dishName, d.served ? 'Yes' : '']);
          } else {
            rows.push([i + 1, d.dishName]);
          }
        });
      }
      if (copyType === 'billing' && items.length > 0) {
        rows.push(['Session total', formatColumnAmount(col.amount) || '—']);
      }
      rows.push([]);
    }
  }

  if (copyType === 'billing' && extras.extrasEnabled) {
    const extrasItems = activeOrderExtraItems(extras.extraItems);
    if (extrasItems.length > 0) {
      rows.push(['Extras']);
      rows.push(['Item', 'Amount']);
      for (const item of extrasItems) {
        rows.push([item.title, item.amount ?? '']);
      }
      const extrasTotal = sumExtraItemAmounts(extras.extraItems);
      if (extrasTotal != null) rows.push(['Extras total', extrasTotal]);
      rows.push([]);
    }
  }

  if (copyType === 'billing') {
    const sessionTotal = sumOrderCopyTotals(columns);
    const extrasTotal = extras.extrasEnabled ? sumExtraItemAmounts(extras.extraItems) : null;
    const parts = [sessionTotal, extrasTotal].filter((a): a is number => a != null);
    if (parts.length > 0) {
      rows.push(['Overall total', parts.reduce((sum, amount) => sum + amount, 0)]);
    }
  }

  if (copyType === 'kitchen' && extras.venueMapLink?.trim()) {
    rows.push([]);
    rows.push(['Venue map', extras.venueMapLink.trim()]);
  }

  return rows;
}

/** Download the on-screen order copy as PDF (uses #order-copy-print from OrderCopyPage). */
export async function downloadOrderCopyPdf(enquiry: Enquiry, copyType: 'kitchen' | 'billing') {
  const element = document.getElementById('order-copy-print');
  if (!element) {
    throw new Error('Order copy is not ready. Please wait a moment and try again.');
  }

  await waitForImages(element);

  const filename = `${sanitizeFilename(enquiry.customerName)}-${copyType}-copy.pdf`;
  const html2pdf = (await import('html2pdf.js')).default;
  const width = element.offsetWidth || 680;

  await html2pdf()
    .set({
      margin: [8, 8, 8, 8],
      filename,
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: {
        scale: 2,
        width,
        windowWidth: width,
        useCORS: true,
        logging: false,
        backgroundColor: '#ffffff',
      },
      jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
    })
    .from(element)
    .save();
}

/** Download kitchen / order copy as an Excel (.xlsx) workbook. */
export async function downloadOrderCopyExcel(enquiry: Enquiry, copyType: 'kitchen' | 'billing') {
  const XLSX = await import('xlsx');
  const rows = buildCopyRows(enquiry, copyType);
  const sheet = XLSX.utils.aoa_to_sheet(rows);
  sheet['!cols'] = [{ wch: 18 }, { wch: 42 }, { wch: 12 }];
  const book = XLSX.utils.book_new();
  const sheetName = copyType === 'kitchen' ? 'Kitchen Copy' : 'Order Copy';
  XLSX.utils.book_append_sheet(book, sheet, sheetName);
  const filename = `${sanitizeFilename(enquiry.customerName)}-${copyType}-copy.xlsx`;
  XLSX.writeFile(book, filename);
}

/** @deprecated use downloadOrderCopyPdf */
export async function downloadOrderCopy(enquiry: Enquiry, copyType: 'kitchen' | 'billing') {
  return downloadOrderCopyPdf(enquiry, copyType);
}

export function printOrderCopy() {
  window.print();
}
