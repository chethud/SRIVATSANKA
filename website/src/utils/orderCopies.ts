import type { Enquiry } from '../api/client';

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
export async function downloadOrderCopy(enquiry: Enquiry, copyType: 'kitchen' | 'billing') {
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

export function printOrderCopy() {
  window.print();
}
