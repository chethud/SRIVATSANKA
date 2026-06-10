import { formatDate, type Enquiry } from '../api/client';
import { parseOrderNotes } from './orderNotes';
import {
  dishesForColumn,
  formatColumnAmount,
  formatPaxTimeLine,
  resolveMenuColumns,
} from './orderMenuGrid';
import { PREFERENCE_CATEGORIES } from './mealSessions';

function buildHtml(enquiry: Enquiry, copyType: 'kitchen' | 'billing') {
  const title = copyType === 'kitchen' ? 'Kitchen Copy' : 'Order Copy';
  const extras = parseOrderNotes(enquiry.notes);
  const menuItems = (enquiry.dishes ?? []).filter((d) => !PREFERENCE_CATEGORIES.has(d.category));
  const columns = resolveMenuColumns(extras, enquiry, menuItems);

  const columnHtml =
    columns.length === 0
      ? '<p style="color:#64748b;">No dishes</p>'
      : `
    <table style="width:100%;border-collapse:collapse;font-size:16px;margin-top:12px;">
      <tr style="background:#f8faf8;font-weight:bold;font-size:16px;">
        ${columns.map((c) => `<td style="border:1px solid #cbd5cb;padding:10px 12px;text-align:center;">${formatDate(c.date)}</td>`).join('')}
      </tr>
      <tr style="font-weight:bold;font-size:16px;">
        ${columns.map((c) => `<td style="border:1px solid #cbd5cb;padding:10px 12px;text-align:center;">${c.sessionLabel}</td>`).join('')}
      </tr>
      <tr style="background:#eef2ee;font-weight:bold;font-size:16px;">
        ${columns.map((c) => `<td style="border:1px solid #cbd5cb;padding:10px 12px;text-align:center;">${formatPaxTimeLine(c)}</td>`).join('')}
      </tr>
      ${copyType === 'billing' ? `<tr style="background:#faf8f5;font-weight:bold;font-size:16px;">
        ${columns.map((c) => `<td style="border:1px solid #cbd5cb;padding:10px 12px;text-align:center;">${formatColumnAmount(c.amount) || '—'}</td>`).join('')}
      </tr>` : ''}
      <tr>
        ${columns
          .map((col) => {
            const items = dishesForColumn(col, menuItems, extras);
            const list =
              items.length === 0
                ? '—'
                : `<ul style="margin:0;padding-left:0;list-style:none;">${items.map((l) => `<li style="font-size:22px;font-weight:600;line-height:1.45;padding:6px 0;">${l.dishName}${l.served ? ' ✓' : ''}</li>`).join('')}</ul>`;
            return `<td style="border:1px solid #cbd5cb;padding:12px 14px;vertical-align:top;font-size:22px;">${list}</td>`;
          })
          .join('')}
      </tr>
    </table>`;

  return `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${title}</title></head><body style="font-family:Verdana,Geneva,Tahoma,sans-serif;padding:24px;max-width:900px;margin:0 auto;font-size:17px;">
    <h1 style="color:#0b6b3a;font-size:22px;">SRIVATSANKA</h1>
    <h2 style="font-size:16px;color:#64748b;">${title}</h2>
    <p style="font-weight:bold;font-size:18px;">Client : ${enquiry.customerName}${enquiry.eventType ? ` · ${enquiry.eventType}` : ''}</p>
    <p style="font-weight:bold;font-size:18px;">${enquiry.eventLocation}</p>
    ${columnHtml}
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
