import { formatCurrency, formatDate, type Enquiry } from '../api/client';

function buildHtml(enquiry: Enquiry, copyType: 'kitchen' | 'billing') {
  const lines = (enquiry.dishes ?? []).map((d) => {
    const lineTotal = (d.unitPrice ?? 0) * (d.quantity || 1);
    return { ...d, lineTotal };
  });
  const subtotal = lines.reduce((s, l) => s + l.lineTotal, 0);
  const total = subtotal * enquiry.guestCount;
  const title = copyType === 'kitchen' ? 'Kitchen Copy' : 'Billing Copy';

  const rows = lines
    .map(
      (l) => `
      <tr>
        <td style="padding:8px 0;border-bottom:1px solid #e5e7eb;">
          ${l.dishName} ×${l.quantity}
          ${l.served ? '<span style="color:#15803d;font-size:12px;"> ✓ served</span>' : ''}
          ${l.customizations ? `<br><span style="color:#6b7280;font-size:12px;">${l.customizations}</span>` : ''}
        </td>
        ${
          copyType === 'billing'
            ? `<td style="text-align:right;padding:8px 0;border-bottom:1px solid #e5e7eb;">${formatCurrency(l.lineTotal)}</td>`
            : ''
        }
      </tr>`,
    )
    .join('');

  const billingFooter =
    copyType === 'billing'
      ? `
      <tr><td style="padding-top:12px;color:#6b7280;">Per guest</td><td style="text-align:right;">${formatCurrency(subtotal)}</td></tr>
      <tr><td style="padding-top:8px;font-weight:bold;">Total (${enquiry.guestCount} guests)</td>
          <td style="text-align:right;font-weight:bold;">${formatCurrency(total)}</td></tr>`
      : '';

  return `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>SRIVATSANKA ${title} - ${enquiry.customerName}</title>
<style>body{font-family:system-ui,sans-serif;max-width:640px;margin:40px auto;padding:24px;color:#1a3324;}
.brand{text-align:center;margin-bottom:24px;background:#fff;border:2px solid #006837;padding:24px;border-radius:12px;}
.brand img{height:96px;} .copy-title{color:#8cc63f;margin-top:12px;font-weight:600;}
table{width:100%;border-collapse:collapse;margin-top:16px;} th{border-color:#006837;}</style></head>
<body>
  <div class="brand">
    <img src="/logo.png" alt="SRIVATSANKA" />
    <p class="copy-title">${title}</p>
  </div>
  <p><strong>${enquiry.customerName}</strong><br>
  ${enquiry.eventType} · ${formatDate(enquiry.eventDate)} · ${enquiry.guestCount} guests<br>
  ${enquiry.eventLocation}</p>
  <table>
    <thead><tr>
      <th style="text-align:left;padding-bottom:8px;border-bottom:2px solid #006837;">Dish</th>
      ${copyType === 'billing' ? '<th style="text-align:right;padding-bottom:8px;border-bottom:2px solid #006837;">Amount</th>' : ''}
    </tr></thead>
    <tbody>${rows || '<tr><td colspan="2">No dishes on this order yet.</td></tr>'}</tbody>
    ${copyType === 'billing' ? `<tfoot>${billingFooter}</tfoot>` : ''}
  </table>
  ${copyType === 'kitchen' ? '<p style="font-size:12px;color:#6b7280;margin-top:24px;">Kitchen copy — no pricing.</p>' : ''}
</body></html>`;
}

export function downloadOrderCopy(enquiry: Enquiry, copyType: 'kitchen' | 'billing') {
  const html = buildHtml(enquiry, copyType);
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  const slug = enquiry.customerName.replace(/\s+/g, '-').slice(0, 30);
  a.href = url;
  a.download = `srivatsanka-${copyType}-${slug}.html`;
  a.click();
  URL.revokeObjectURL(url);
}
