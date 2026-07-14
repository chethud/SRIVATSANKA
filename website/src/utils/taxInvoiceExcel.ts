import type { Enquiry } from '../api/client';
import {
  INVOICE_COMPANY,
  formatInvoiceDate,
  numberToIndianWords,
  shortInvoiceNo,
} from './invoiceCompany';
import {
  activeOrderExtraItems,
  parseOrderNotes,
  sumExtraItemAmounts,
} from './orderNotes';
import {
  dishesForColumn,
  formatPaxTimeLine,
  resolveMenuColumns,
  sumOrderCopyTotals,
} from './orderMenuGrid';
import { PREFERENCE_CATEGORIES } from './mealSessions';

type LineItem = {
  description: string;
  hsn: string | number;
  qty: number | string;
  unitRate: number | string;
  amount: number;
};

function thinBorder() {
  const side = { style: 'thin' as const, color: { argb: 'FF000000' } };
  return { top: side, left: side, bottom: side, right: side };
}

function buildInvoiceLines(enquiry: Enquiry, copyType: 'kitchen' | 'billing'): LineItem[] {
  const extras = parseOrderNotes(enquiry.notes);
  const menuItems = (enquiry.dishes ?? []).filter((d) => !PREFERENCE_CATEGORIES.has(d.category));
  const columns = resolveMenuColumns(extras, enquiry, menuItems);
  const lines: LineItem[] = [];

  for (const col of columns) {
    const items = dishesForColumn(col, menuItems, extras);
    const dishNames = items.map((d) => d.dishName).filter(Boolean);
    const paxLine = formatPaxTimeLine(col);
    const guestLabel = enquiry.eventType ? ` for ${enquiry.eventType}` : '';
    const descParts = [
      `${col.sessionLabel}${guestLabel}`.trim(),
      formatInvoiceDate(col.date),
      paxLine || null,
      copyType === 'kitchen' && dishNames.length > 0 ? dishNames.join(', ') : null,
    ].filter(Boolean);

    const amount = typeof col.amount === 'number' ? col.amount : 0;
    const qty = col.pax != null && col.pax > 0 ? col.pax : dishNames.length || 'NA';
    let unitRate: number | string = '';
    if (typeof qty === 'number' && qty > 0 && amount > 0) {
      unitRate = Math.round((amount / qty) * 100) / 100;
    } else if (amount > 0) {
      unitRate = amount;
    }

    lines.push({
      description: descParts.join('\n'),
      hsn: INVOICE_COMPANY.hsnSac,
      qty,
      unitRate: unitRate === '' ? 'NA' : unitRate,
      amount,
    });
  }

  if (copyType === 'billing' && extras.extrasEnabled) {
    for (const item of activeOrderExtraItems(extras.extraItems)) {
      const amount = typeof item.amount === 'number' ? item.amount : 0;
      lines.push({
        description: item.title + (item.description ? `\n${item.description}` : ''),
        hsn: INVOICE_COMPANY.hsnSac,
        qty: item.quantity?.trim() || 'NA',
        unitRate: amount || 'NA',
        amount,
      });
    }
  }

  if (lines.length === 0) {
    lines.push({
      description: `${enquiry.eventType || 'Event'} — ${enquiry.customerName}`,
      hsn: INVOICE_COMPANY.hsnSac,
      qty: enquiry.guestCount || 'NA',
      unitRate: 'NA',
      amount: 0,
    });
  }

  return lines;
}

function billingAddressBlock(enquiry: Enquiry): string {
  const extras = parseOrderNotes(enquiry.notes);
  const parts = [
    enquiry.customerName,
    enquiry.eventLocation,
    enquiry.phoneNumber ? `Phone : ${enquiry.phoneNumber}` : null,
    enquiry.eventType ? `Event : ${enquiry.eventType}` : null,
    enquiry.eventDate ? `Event Date : ${formatInvoiceDate(enquiry.eventDate)}` : null,
    enquiry.guestCount ? `Guests : ${enquiry.guestCount}` : null,
    extras.venueMapLink ? `Map : ${extras.venueMapLink}` : null,
  ].filter(Boolean);
  return parts.join('\n');
}

/** Build a tax-invoice Excel workbook matching the Casagrand sales-invoice layout. */
export async function buildTaxInvoiceWorkbook(enquiry: Enquiry, copyType: 'kitchen' | 'billing') {
  const ExcelJS = (await import('exceljs')).default;
  const wb = new ExcelJS.Workbook();
  wb.creator = INVOICE_COMPANY.legalName;
  const ws = wb.addWorksheet(copyType === 'kitchen' ? 'Kitchen Invoice' : 'IN', {
    views: [{ showGridLines: false }],
  });

  // Column widths match Casagrand / RA Hospitalities sales invoices
  ws.columns = [
    { key: 'a', width: 15.66 },
    { key: 'b', width: 13.1 },
    { key: 'c', width: 21.89 },
    { key: 'd', width: 11 },
    { key: 'e', width: 5.22 },
    { key: 'f', width: 7.33 },
    { key: 'g', width: 3.78 },
    { key: 'h', width: 17.11 },
  ];

  const border = thinBorder();
  const center = { vertical: 'middle' as const, horizontal: 'center' as const, wrapText: true };
  const left = { vertical: 'middle' as const, horizontal: 'left' as const, wrapText: true };

  const merge = (range: string) => ws.mergeCells(range);
  const styleRange = (startRow: number, endRow: number, startCol: number, endCol: number) => {
    for (let r = startRow; r <= endRow; r++) {
      for (let c = startCol; c <= endCol; c++) {
        const cell = ws.getCell(r, c);
        cell.border = border;
      }
    }
  };

  // Row 2 — Original (logo sits in A2:A4 on paper invoices)
  merge('A2:A4');
  ws.getCell('H2').value = 'Original';
  ws.getCell('H2').alignment = { horizontal: 'right' };
  ws.getCell('H2').font = { bold: true, size: 11 };

  // Row 3 — Company name
  merge('B3:H3');
  ws.getRow(3).height = 55.5;
  ws.getCell('B3').value = INVOICE_COMPANY.legalName;
  ws.getCell('B3').font = { name: 'Calibri', size: 20, bold: true };
  ws.getCell('B3').alignment = center;

  // Row 4 — FSSAI / address / email
  merge('B4:H4');
  ws.getRow(4).height = 45.75;
  ws.getCell('B4').value =
    `FSSAI  Lic No:${INVOICE_COMPANY.fssai}\n${INVOICE_COMPANY.address}\nEmail Id :${INVOICE_COMPANY.email}`;
  ws.getCell('B4').font = { size: 10, bold: true };
  ws.getCell('B4').alignment = { ...left, wrapText: true };

  // Row 5 — TAX INVOICE
  merge('A5:H5');
  ws.getRow(5).height = 23.25;
  ws.getCell('A5').value = 'TAX INVOICE  ';
  ws.getCell('A5').font = { name: 'Calibri', size: 16, bold: true };
  ws.getCell('A5').alignment = center;

  // Row 6 — Billing Address label
  merge('A6:H6');
  ws.getCell('A6').value = 'Billing Address:';
  ws.getCell('A6').font = { bold: true, size: 11 };

  // Row 7 — Customer block
  merge('A7:H7');
  ws.getRow(7).height = 110;
  ws.getCell('A7').value = billingAddressBlock(enquiry);
  ws.getCell('A7').font = { bold: true, size: 11 };
  ws.getCell('A7').alignment = left;

  // Rows 8–11 — meta
  ws.getCell('A8').value = `INVOICE NO : ${shortInvoiceNo(enquiry.id)}`;
  merge('E8:H8');
  ws.getCell('E8').value = `GSTIN NO : ${INVOICE_COMPANY.gstin}`;

  ws.getCell('A9').value = `DATE : ${formatInvoiceDate(enquiry.eventDate || new Date().toISOString())}`;
  merge('E9:H9');
  ws.getCell('E9').value = `CIN No : ${INVOICE_COMPANY.cin}`;

  merge('A10:C10');
  ws.getCell('A10').value = 'Mode of Transport: NA';
  merge('E10:H10');
  ws.getCell('E10').value = `PAN No: ${INVOICE_COMPANY.pan}`;

  ws.getCell('A11').value = 'Vehicle No';
  merge('E11:H11');
  ws.getCell('E11').value = '';

  for (const addr of ['A8', 'A9', 'A10', 'A11', 'E8', 'E9', 'E10', 'E11']) {
    ws.getCell(addr).font = { bold: true, size: 11 };
  }

  // Header row 12
  merge('B12:C12');
  merge('F12:G12');
  ws.getCell('A12').value = 'S. NO.';
  ws.getCell('B12').value = 'Part Description';
  ws.getCell('D12').value = 'HSN/SAC';
  ws.getCell('E12').value = 'QTY';
  ws.getCell('F12').value = 'Unit Rate';
  ws.getCell('H12').value = 'Amount ';
  for (const col of [1, 2, 4, 5, 6, 8]) {
    const cell = ws.getCell(12, col);
    cell.font = { bold: true, size: 11 };
    cell.alignment = center;
  }

  const lines = buildInvoiceLines(enquiry, copyType);
  const firstDataRow = 13;
  lines.forEach((line, i) => {
    const r = firstDataRow + i;
    merge(`B${r}:C${r}`);
    merge(`F${r}:G${r}`);
    ws.getRow(r).height = Math.max(18, 14 + line.description.split('\n').length * 12);
    ws.getCell(`A${r}`).value = i + 1;
    ws.getCell(`B${r}`).value = line.description;
    ws.getCell(`D${r}`).value = line.hsn;
    ws.getCell(`E${r}`).value = line.qty;
    ws.getCell(`F${r}`).value = line.unitRate;
    ws.getCell(`H${r}`).value = line.amount;
    ws.getCell(`A${r}`).alignment = center;
    ws.getCell(`B${r}`).alignment = left;
    ws.getCell(`D${r}`).alignment = center;
    ws.getCell(`E${r}`).alignment = center;
    ws.getCell(`F${r}`).alignment = center;
    ws.getCell(`H${r}`).alignment = { horizontal: 'right', vertical: 'middle' };
    ws.getCell(`H${r}`).numFmt = '#,##0.00';
  });

  const lastDataRow = firstDataRow + Math.max(lines.length, 1) - 1;
  const subRow = lastDataRow + 1;
  const cgstRow = subRow + 1;
  const sgstRow = cgstRow + 1;
  const roundRow = sgstRow + 1;
  const totalRow = roundRow + 1;
  const wordsRow = totalRow + 1;
  const bankRow = wordsRow + 1;
  const signRow = bankRow + 2;

  let subTotal = lines.reduce((s, l) => s + (Number(l.amount) || 0), 0);
  if (subTotal === 0) {
    const extras = parseOrderNotes(enquiry.notes);
    const columns = resolveMenuColumns(
      extras,
      enquiry,
      (enquiry.dishes ?? []).filter((d) => !PREFERENCE_CATEGORIES.has(d.category)),
    );
    const sessionTotal = sumOrderCopyTotals(columns);
    const extrasTotal = extras.extrasEnabled ? sumExtraItemAmounts(extras.extraItems) : null;
    const parts = [sessionTotal, extrasTotal].filter((a): a is number => a != null);
    if (parts.length > 0) subTotal = parts.reduce((s, a) => s + a, 0);
  }

  const cgst = Math.round(subTotal * INVOICE_COMPANY.cgstRate * 100) / 100;
  const sgst = Math.round(subTotal * INVOICE_COMPANY.sgstRate * 100) / 100;
  const grand = Math.round((subTotal + cgst + sgst) * 100) / 100;

  merge(`B${subRow}:C${subRow}`);
  merge(`D${subRow}:G${subRow}`);
  ws.getCell(`B${subRow}`).value = 'Sub Total';
  ws.getCell(`H${subRow}`).value = subTotal;
  ws.getCell(`H${subRow}`).numFmt = '#,##0.00';

  merge(`B${cgstRow}:C${cgstRow}`);
  merge(`D${cgstRow}:G${cgstRow}`);
  ws.getCell(`B${cgstRow}`).value = 'CGST 2.5%';
  ws.getCell(`D${cgstRow}`).value = cgst;
  ws.getCell(`H${cgstRow}`).value = cgst;
  ws.getCell(`D${cgstRow}`).numFmt = '#,##0.00';
  ws.getCell(`H${cgstRow}`).numFmt = '#,##0.00';

  merge(`B${sgstRow}:C${sgstRow}`);
  merge(`D${sgstRow}:G${sgstRow}`);
  ws.getCell(`B${sgstRow}`).value = 'SGST 2.5%';
  ws.getCell(`D${sgstRow}`).value = sgst;
  ws.getCell(`H${sgstRow}`).value = sgst;
  ws.getCell(`D${sgstRow}`).numFmt = '#,##0.00';
  ws.getCell(`H${sgstRow}`).numFmt = '#,##0.00';

  merge(`B${roundRow}:C${roundRow}`);
  merge(`D${roundRow}:G${roundRow}`);
  ws.getCell(`D${roundRow}`).value = 'Round Off';
  ws.getCell(`H${roundRow}`).value = 0;

  merge(`A${totalRow}:G${totalRow}`);
  ws.getCell(`A${totalRow}`).value = ' Total';
  ws.getCell(`A${totalRow}`).font = { bold: true, size: 12 };
  ws.getCell(`H${totalRow}`).value = grand;
  ws.getCell(`H${totalRow}`).font = { bold: true, size: 12 };
  ws.getCell(`H${totalRow}`).numFmt = '#,##0.00';

  merge(`A${wordsRow}:H${wordsRow}`);
  ws.getRow(wordsRow).height = 22;
  ws.getCell(`A${wordsRow}`).value = `Amount In Word :${numberToIndianWords(grand)}`;
  ws.getCell(`A${wordsRow}`).font = { bold: true, size: 11 };

  merge(`A${bankRow}:H${bankRow + 1}`);
  ws.getRow(bankRow).height = 22;
  ws.getRow(bankRow + 1).height = 36;
  ws.getCell(`A${bankRow}`).value =
    `Bank Transfer Details: ${INVOICE_COMPANY.bankAccountName}\nA/c No: ${INVOICE_COMPANY.bankAccount}\nIFSC Code: ${INVOICE_COMPANY.bankIfsc}\n${INVOICE_COMPANY.bankName}`;
  ws.getCell(`A${bankRow}`).font = { bold: true, size: 11 };
  ws.getCell(`A${bankRow}`).alignment = left;

  merge(`A${signRow}:D${signRow + 1}`);
  merge(`E${signRow}:H${signRow + 1}`);
  ws.getRow(signRow).height = 18;
  ws.getRow(signRow + 1).height = 40;
  ws.getCell(`A${signRow}`).value = 'Received                                                                  Customer Signature';
  ws.getCell(`E${signRow}`).value = '                                                                           Authorised Signatory';
  ws.getCell(`A${signRow}`).font = { bold: true, size: 11 };
  ws.getCell(`E${signRow}`).font = { bold: true, size: 11 };

  // Borders around main grid
  styleRange(3, 11, 1, 8);
  styleRange(12, lastDataRow, 1, 8);
  styleRange(subRow, totalRow, 1, 8);
  styleRange(wordsRow, wordsRow, 1, 8);
  styleRange(bankRow, bankRow + 1, 1, 8);
  styleRange(signRow, signRow + 1, 1, 8);

  for (const r of [subRow, cgstRow, sgstRow, roundRow, totalRow]) {
    ws.getCell(`B${r}`).font = { bold: true, size: 11 };
  }

  if (subTotal === 0) {
    const noteRow = signRow + 3;
    merge(`A${noteRow}:H${noteRow}`);
    ws.getCell(`A${noteRow}`).value =
      'Note: Add session amounts on the order page to populate Unit Rate / Amount and GST totals.';
    ws.getCell(`A${noteRow}`).font = { italic: true, size: 10, color: { argb: 'FF666666' } };
  }

  return wb;
}
