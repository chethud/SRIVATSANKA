/** Company tax-invoice details matching Srivatsanka sales invoice template. */
export const INVOICE_COMPANY = {
  legalName: 'Srivatsanka Events and Services Pvt Ltd',
  fssai: '1121933001082',
  address:
    'No:58, 4th Cross, 4th Main, Near APS College, N R Colony, Bengaluru-560019',
  email: 'srivatsankas@gmail.com',
  gstin: '29AAZCS3400N1ZM',
  cin: 'U93090KA2017PTC107116',
  pan: 'AAZCS3400N',
  bankName: 'Kotak Mahindra Bank',
  bankAccount: '4412031591',
  bankIfsc: 'KKBK0008066',
  bankAccountName: 'Srivatsanka Events and Services Pvt Ltd',
  cgstRate: 0.025,
  sgstRate: 0.025,
};

export function numberToIndianWords(amount: number): string {
  const n = Math.round(Math.abs(amount));
  if (n === 0) return 'Zero Rupees only';

  const ones = [
    '', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine',
    'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen',
    'Seventeen', 'Eighteen', 'Nineteen',
  ];
  const tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety'];

  const twoDigits = (num: number): string => {
    if (num < 20) return ones[num];
    const t = Math.floor(num / 10);
    const o = num % 10;
    return `${tens[t]}${o ? ` ${ones[o]}` : ''}`.trim();
  };

  const threeDigits = (num: number): string => {
    const h = Math.floor(num / 100);
    const r = num % 100;
    if (h && r) return `${ones[h]} Hundred ${twoDigits(r)}`;
    if (h) return `${ones[h]} Hundred`;
    return twoDigits(r);
  };

  const crore = Math.floor(n / 10000000);
  const lakh = Math.floor((n % 10000000) / 100000);
  const thousand = Math.floor((n % 100000) / 1000);
  const rest = n % 1000;

  const parts: string[] = [];
  if (crore) parts.push(`${threeDigits(crore)} Crore`);
  if (lakh) parts.push(`${threeDigits(lakh)} Lakh`);
  if (thousand) parts.push(`${threeDigits(thousand)} Thousand`);
  if (rest) parts.push(threeDigits(rest));
  return `${parts.join(' ').replace(/\s+/g, ' ').trim()} Rupees only`;
}

export { formatInvoiceDateOnly as formatInvoiceDate } from './dateOnly';

export function shortInvoiceNo(enquiryId: string): string {
  const suffix = enquiryId.replace(/[^a-zA-Z0-9]/g, '').slice(-6).toUpperCase() || '0001';
  const year = new Date().getFullYear();
  const yy = String(year).slice(-2);
  const prev = String(year - 1).slice(-2);
  return `SES/${prev}-${yy}/${suffix}`;
}
