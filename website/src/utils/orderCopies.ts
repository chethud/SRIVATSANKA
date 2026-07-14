import type { Enquiry } from '../api/client';
import { appendMenuSheet, buildMenuSheetWorkbook } from './menuSheetExcel';
import { buildTaxInvoiceWorkbook } from './taxInvoiceExcel';

function sanitizeFilename(name: string): string {
  return name.replace(/[^\w\s-]/g, '').replace(/\s+/g, '-').slice(0, 80) || 'order';
}

/**
 * Download Excel matching D:\excel references:
 * - Kitchen → wedding Menu sheet (Nithin / Muralidharan)
 * - Order copy → tax Invoice (Casagrand / RA) + Menu sheet
 */
export async function downloadOrderCopyExcel(enquiry: Enquiry, copyType: 'kitchen' | 'billing') {
  let wb;
  let filename: string;

  if (copyType === 'kitchen') {
    wb = await buildMenuSheetWorkbook(enquiry, 'kitchen');
    filename = `${sanitizeFilename(enquiry.customerName)}-kitchen-menu.xlsx`;
  } else {
    wb = await buildTaxInvoiceWorkbook(enquiry, 'billing');
    await appendMenuSheet(wb, enquiry, 'billing');
    filename = `${sanitizeFilename(enquiry.customerName)}-sales-invoice.xlsx`;
  }

  const buffer = await wb.xlsx.writeBuffer();
  const blob = new Blob([buffer], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function printOrderCopy() {
  window.print();
}
