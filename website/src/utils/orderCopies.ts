import { formatDate, type Enquiry, type EnquiryDish } from '../api/client';
import { parseOrderNotes } from './orderNotes';
import {
  dishesForColumn,
  formatColumnAmount,
  formatPaxTimeLine,
  resolveMenuColumns,
} from './orderMenuGrid';
import { PREFERENCE_CATEGORIES } from './mealSessions';

function buildSessionHtml(
  col: ReturnType<typeof resolveMenuColumns>[number],
  copyType: 'kitchen' | 'billing',
  extras: ReturnType<typeof parseOrderNotes>,
  menuItems: EnquiryDish[],
) {
  const dishItems = dishesForColumn(col, menuItems, extras);
  const list =
    dishItems.length === 0
      ? '<p style="color:#64748b;text-align:center;">—</p>'
      : `<ul style="margin:0;padding:0;list-style:none;">${dishItems
          .map(
            (l) =>
              `<li style="font-size:22px;font-weight:600;line-height:1.45;padding:6px 0;">${l.dishName}${l.served ? ' ✓' : ''}</li>`,
          )
          .join('')}</ul>`;
  const amountRow =
    copyType === 'billing' && dishItems.length > 0
      ? `<div style="border-top:1px solid #cbd5cb;background:#faf8f5;padding:10px 12px;text-align:center;font-weight:bold;font-size:16px;">${formatColumnAmount(col.amount) || '—'}</div>`
      : '';

  return `
    <div style="border:1px solid #cbd5cb;margin-bottom:20px;overflow:hidden;">
      <div style="background:#f8faf8;font-weight:bold;font-size:16px;padding:10px 12px;text-align:center;border-bottom:1px solid #cbd5cb;">${formatDate(col.date)}</div>
      <div style="font-weight:bold;font-size:16px;padding:10px 12px;text-align:center;border-bottom:1px solid #cbd5cb;">${col.sessionLabel}</div>
      <div style="background:#eef2ee;font-weight:bold;font-size:16px;padding:10px 12px;text-align:center;border-bottom:1px solid #cbd5cb;">${formatPaxTimeLine(col)}</div>
      <div style="padding:12px 14px;">${list}</div>
      ${amountRow}
    </div>`;
}

function buildHtml(enquiry: Enquiry, copyType: 'kitchen' | 'billing') {
  const title = copyType === 'kitchen' ? 'Kitchen Copy' : 'Order Copy';
  const extras = parseOrderNotes(enquiry.notes);
  const menuItems = (enquiry.dishes ?? []).filter((d) => !PREFERENCE_CATEGORIES.has(d.category));
  const columns = resolveMenuColumns(extras, enquiry, menuItems);

  const columnHtml =
    columns.length === 0
      ? '<p style="color:#64748b;">No dishes</p>'
      : columns.map((col) => buildSessionHtml(col, copyType, extras, menuItems)).join('');

  return `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${title}</title></head><body style="font-family:Verdana,Geneva,Tahoma,sans-serif;padding:24px;max-width:720px;margin:0 auto;font-size:17px;">
    <h1 style="color:#0b6b3a;font-size:22px;">SRIVATSANKA</h1>
    <h2 style="font-size:16px;color:#64748b;">${title}</h2>
    <p style="font-weight:bold;font-size:18px;">Client : ${enquiry.customerName}${enquiry.eventType ? ` · ${enquiry.eventType}` : ''}</p>
    <p style="font-weight:bold;font-size:18px;">${enquiry.eventLocation}</p>
    <div style="margin-top:12px;">${columnHtml}</div>
  </body></html>`;
}

export function downloadOrderCopy(enquiry: Enquiry, copyType: 'kitchen' | 'billing') {
  const html = buildHtml(enquiry, copyType);
  const blob = new Blob([html], { type: 'text/html' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${enquiry.customerName.replace(/\s+/g, '-')}-${copyType}-copy.html`;
  a.click();
  URL.revokeObjectURL(url);
}

export function printOrderCopy() {
  window.print();
}
