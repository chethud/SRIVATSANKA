import type { Enquiry } from '../api/client';
import { buildTaxInvoiceWorkbook } from './taxInvoiceExcel';

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

/**
 * Download kitchen / order copy as Excel tax invoice
 * (layout matches Srivatsanka Sales Invoice / Casagrand format).
 */
export async function downloadOrderCopyExcel(enquiry: Enquiry, copyType: 'kitchen' | 'billing') {
  const wb = await buildTaxInvoiceWorkbook(enquiry, copyType);
  const buffer = await wb.xlsx.writeBuffer();
  const blob = new Blob([buffer], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  });
  const filename = `${sanitizeFilename(enquiry.customerName)}-${copyType}-tax-invoice.xlsx`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/** @deprecated use downloadOrderCopyPdf */
export async function downloadOrderCopy(enquiry: Enquiry, copyType: 'kitchen' | 'billing') {
  return downloadOrderCopyPdf(enquiry, copyType);
}

export function printOrderCopy() {
  window.print();
}
