import jsPDF from 'jspdf';

declare module 'jspdf' {
  interface jsPDF {
    saveGraphicsState(): jsPDF;
    restoreGraphicsState(): jsPDF;
    setGlobalAlpha(alpha: number): jsPDF;
  }
}

interface SentinelPdfOptions {
  type: 'dmca' | 'blockchain' | 'asset';
  title: string;
  refId: string;
  assetName: string;
  txHash?: string;
  network?: string;
  status?: string;
  demoMode?: boolean;
  platform?: string;
  url?: string;
  similarity?: string;
  orgName?: string;
  date?: string;
  country?: string;
  jurisdiction?: string;
  legalEntityName?: string;
  legalAddress?: string;
  postalCode?: string;
  registrationId?: string;
  taxId?: string;
  noticeEmail?: string;
  contactPhone?: string;
}

type LegalJurisdiction = 'India' | 'United States' | 'United Kingdom' | 'European Union' | 'Canada' | 'Australia' | 'Singapore' | 'United Arab Emirates' | 'Global';

function normalizeJurisdiction(input?: string): LegalJurisdiction {
  const value = (input || '').trim().toLowerCase();
  if (!value) return 'Global';

  if (value.includes('india')) return 'India';
  if (value.includes('united states') || value === 'us' || value === 'usa' || value.includes('america')) return 'United States';
  if (value.includes('united kingdom') || value === 'uk' || value.includes('great britain') || value.includes('england')) return 'United Kingdom';
  if (value.includes('european union') || value === 'eu') return 'European Union';
  if (value.includes('canada')) return 'Canada';
  if (value.includes('australia')) return 'Australia';
  if (value.includes('singapore')) return 'Singapore';
  if (value.includes('united arab emirates') || value === 'uae' || value.includes('emirates')) return 'United Arab Emirates';
  return 'Global';
}

function legalNoticeTemplate(jurisdiction: LegalJurisdiction) {
  switch (jurisdiction) {
    case 'India':
      return {
        headerLabel: 'LEGAL INFRINGEMENT NOTICE (INDIA)',
        sectionTitle: 'Legal Takedown Notice (India)',
        body: `Without prejudice to all rights and remedies, this notice is issued under the Copyright Act, 1957 (including Sections 51, 55 and 63), the Information Technology Act, 2000, and the Information Technology (Intermediary Guidelines and Digital Media Ethics Code) Rules, 2021, as applicable in India. The rights holder identified above asserts exclusive rights in the referenced asset, supported by the blockchain transaction hash and timestamped registration particulars set out in this document.\n\nYou are hereby called upon to remove and disable access to the infringing material, and to cease all further hosting, streaming, reproduction, communication to the public, or distribution of the same upon receipt of this notice. You are further required to preserve relevant logs, metadata, and uploader records, and to provide written confirmation of compliance within 36 hours of receipt.\n\nFailure to comply may result in appropriate civil and criminal proceedings before courts and competent authorities in India, including claims for injunctive relief, damages, costs, and other statutory remedies.`,
      };
    case 'United States':
      return {
        headerLabel: 'COPYRIGHT TAKEDOWN NOTICE (US)',
        sectionTitle: 'Copyright Takedown Notice (United States)',
        body: `This notice is submitted under the United States Copyright Act, including the Digital Millennium Copyright Act, 17 U.S.C. § 512. The rights holder identified in this document represents that it owns or controls exclusive rights in the referenced asset, supported by blockchain timestamp and transaction evidence recorded herein.\n\nYou are required to expeditiously remove or disable access to the identified infringing material and to cease further hosting, publication, distribution, or transmission. You are requested to preserve relevant logs, account records, and technical metadata and to provide written confirmation of compliance within 48 hours of receipt.\n\nAny non-compliance may give rise to further legal action, including injunctive and monetary relief in the appropriate jurisdiction.`,
      };
    case 'United Kingdom':
      return {
        headerLabel: 'COPYRIGHT INFRINGEMENT NOTICE (UK)',
        sectionTitle: 'Copyright Notice (United Kingdom)',
        body: `This notice is issued under the Copyright, Designs and Patents Act 1988 and other applicable laws of England and Wales, Scotland, or Northern Ireland, as relevant. The rights holder identified herein claims ownership and control of the referenced protected asset, corroborated by blockchain registration evidence included in this notice.\n\nYou are required to remove or disable access to the infringing material without delay and to refrain from further communication to the public, copying, sharing, or distribution of the same. Please preserve relevant logs and account details and provide written confirmation of compliance within 48 hours.\n\nFailure to comply may result in civil proceedings, including injunctions, damages, account of profits, and costs.`,
      };
    case 'European Union':
      return {
        headerLabel: 'COPYRIGHT NOTICE (EU)',
        sectionTitle: 'Copyright and Platform Notice (European Union)',
        body: `This notice is issued pursuant to applicable EU and Member State copyright frameworks, including Directive 2001/29/EC (InfoSoc Directive), Directive (EU) 2019/790 (DSM Directive), and related national implementing laws. The rights holder identified herein asserts exclusive rights in the referenced content, supported by blockchain-based evidentiary records.\n\nYou are required to act expeditiously to remove or disable access to the identified infringing content and to prevent further unauthorized making available, reproduction, or distribution. You are requested to preserve uploader records, logs, and associated metadata and provide written confirmation within 48 hours.\n\nNon-compliance may lead to civil enforcement proceedings and related remedies available under applicable EU and national laws.`,
      };
    case 'Canada':
      return {
        headerLabel: 'COPYRIGHT NOTICE (CANADA)',
        sectionTitle: 'Copyright Notice (Canada)',
        body: `This notice is issued under the Copyright Act (R.S.C., 1985, c. C-42) and applicable provincial and federal legal frameworks. The rights holder identified in this notice asserts ownership and control of the referenced asset, supported by blockchain timestamp and transaction evidence.\n\nYou are required to remove or disable access to the infringing content and to cease further hosting, sharing, communication, or distribution of such content. You are requested to preserve all relevant logs and account identifiers and provide written confirmation of compliance within 48 hours.\n\nFailure to comply may result in legal proceedings and all available remedies under Canadian law.`,
      };
    case 'Australia':
      return {
        headerLabel: 'COPYRIGHT NOTICE (AUSTRALIA)',
        sectionTitle: 'Copyright Notice (Australia)',
        body: `This notice is issued under the Copyright Act 1968 (Cth) and other applicable Commonwealth and State laws. The rights holder named herein asserts ownership and exclusive rights in the referenced material, supported by blockchain registration and timestamped transaction evidence.\n\nYou are required to promptly remove or disable access to the infringing content and cease any further reproduction, communication, hosting, sharing, or distribution. Please preserve relevant records and metadata and confirm compliance in writing within 48 hours.\n\nFailure to comply may result in legal proceedings, including claims for injunctive relief, damages, and costs.`,
      };
    case 'Singapore':
      return {
        headerLabel: 'COPYRIGHT NOTICE (SINGAPORE)',
        sectionTitle: 'Copyright Notice (Singapore)',
        body: `This notice is issued under the Copyright Act 2021 and related laws of Singapore. The rights holder identified herein asserts ownership and exclusive rights in the referenced asset, supported by blockchain-based registration evidence set out in this document.\n\nYou are required to remove or disable access to the infringing material without delay and to cease all further hosting, reproduction, communication, or distribution. You are requested to preserve relevant records, uploader details, and technical metadata and provide written confirmation within 48 hours.\n\nNon-compliance may result in civil and, where applicable, criminal enforcement measures under Singapore law.`,
      };
    case 'United Arab Emirates':
      return {
        headerLabel: 'COPYRIGHT NOTICE (UAE)',
        sectionTitle: 'Copyright Notice (United Arab Emirates)',
        body: `This notice is issued under applicable United Arab Emirates intellectual property and cyber laws, including Federal Decree-Law No. 38 of 2021 on Copyright and Neighboring Rights, as amended from time to time. The rights holder identified herein asserts exclusive rights in the referenced asset, supported by blockchain transaction and timestamp evidence.\n\nYou are required to remove and disable access to the infringing material immediately and to cease all further hosting, publication, sharing, or distribution. You are requested to retain relevant logs and account information and provide written confirmation of compliance within 48 hours.\n\nFailure to comply may result in legal and regulatory action before the competent authorities and courts in the UAE.`,
      };
    default:
      return {
        headerLabel: 'GLOBAL LEGAL INFRINGEMENT NOTICE',
        sectionTitle: 'Global Copyright and Infringement Notice',
        body: `Without prejudice to all rights and remedies, this notice is issued under applicable copyright, intermediary liability, and digital communications laws in relevant jurisdictions. The rights holder identified herein asserts ownership and control of exclusive rights in the referenced asset, as substantiated by the blockchain transaction hash and timestamped registration records set out in this document.\n\nYou are required to promptly remove or disable access to the infringing material and to cease all further hosting, communication, publication, sharing, or distribution of the same. You are requested to preserve relevant logs, account identifiers, and technical metadata and provide written confirmation of compliance within 48 hours of receipt.\n\nFailure to comply may result in civil and/or criminal proceedings and related injunctive, monetary, and statutory remedies in the competent jurisdiction(s).`,
      };
  }
}

function setAlphaIfSupported(doc: jsPDF, alpha: number) {
  const maybeDoc = doc as jsPDF & { setGlobalAlpha?: (value: number) => jsPDF };
  if (typeof maybeDoc.setGlobalAlpha === 'function') {
    maybeDoc.setGlobalAlpha(alpha);
  }
}

const PDF_THEME = {
  pageBg: [248, 251, 255] as const,
  surface: [255, 255, 255] as const,
  border: [197, 214, 233] as const,
  accent: [18, 99, 170] as const,
  accentSoft: [228, 239, 252] as const,
  text: [20, 35, 56] as const,
  muted: [89, 113, 142] as const,
  watermark: [223, 232, 244] as const,
};

function drawBrandMark(doc: jsPDF, x: number, y: number, size: number, watermark = false) {
  const inset = size * 0.09;
  const dotR = size * 0.045;

  if (watermark) {
    doc.setFillColor(240, 245, 251);
    doc.setDrawColor(214, 225, 239);
  } else {
    doc.setFillColor(PDF_THEME.surface[0], PDF_THEME.surface[1], PDF_THEME.surface[2]);
    doc.setDrawColor(PDF_THEME.accent[0], PDF_THEME.accent[1], PDF_THEME.accent[2]);
  }
  doc.setLineWidth(0.42);
  doc.roundedRect(x, y, size, size, 2.3, 2.3, 'FD');

  if (watermark) {
    doc.setDrawColor(222, 232, 244);
  } else {
    doc.setDrawColor(170, 194, 222);
  }
  doc.setLineWidth(0.28);
  doc.roundedRect(x + inset, y + inset, size - inset * 2, size - inset * 2, 1.8, 1.8, 'S');

  doc.setTextColor(PDF_THEME.text[0], PDF_THEME.text[1], PDF_THEME.text[2]);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(size * 0.64);
  doc.text('S', x + size * 0.5, y + size * 0.69, { align: 'center' });

  if (watermark) {
    doc.setFillColor(205, 219, 236);
  } else {
    doc.setFillColor(PDF_THEME.accent[0], PDF_THEME.accent[1], PDF_THEME.accent[2]);
  }
  doc.circle(x + size * 0.77, y + size * 0.2, dotR, 'F');
}

function drawWatermark(doc: jsPDF) {
  const pageW = doc.internal.pageSize.getWidth();
  const pageH = doc.internal.pageSize.getHeight();

  const logoSize = 26;
  const centerX = pageW / 2;
  const centerY = pageH / 2;

  drawBrandMark(doc, centerX - logoSize / 2, centerY - 22, logoSize, true);

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(16);
  doc.setTextColor(PDF_THEME.watermark[0], PDF_THEME.watermark[1], PDF_THEME.watermark[2]);
  doc.text('SENTINEL', centerX, centerY + 10, { align: 'center' });

  // Reset text color for body content
  doc.setTextColor(PDF_THEME.text[0], PDF_THEME.text[1], PDF_THEME.text[2]);
}

function drawHeader(doc: jsPDF, type: string, legalLabel?: string) {
  const pageW = doc.internal.pageSize.getWidth();

  // Header bar
  doc.setFillColor(242, 247, 253);
  doc.rect(0, 0, pageW, 24, 'F');

  // Brand emblem
  drawBrandMark(doc, 10, 4.2, 14.5);

  // SENTINEL wordmark
  doc.setFontSize(12.5);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(PDF_THEME.text[0], PDF_THEME.text[1], PDF_THEME.text[2]);
  doc.text('SENTINEL', 27, 14.2);

  // Document type label on right
  doc.setFontSize(6.7);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(PDF_THEME.accent[0], PDF_THEME.accent[1], PDF_THEME.accent[2]);
  const typeLabel = type === 'dmca'
    ? legalLabel || 'GLOBAL LEGAL INFRINGEMENT NOTICE'
    : type === 'blockchain'
    ? 'BLOCKCHAIN PROOF CERTIFICATE'
    : 'ASSET PROTECTION CERTIFICATE';
  doc.text(typeLabel, pageW - 10, 14.2, { align: 'right' });

  // Accent line under header
  doc.setDrawColor(PDF_THEME.border[0], PDF_THEME.border[1], PDF_THEME.border[2]);
  doc.setLineWidth(0.35);
  doc.line(0, 24, pageW, 24);
}

function drawFooter(doc: jsPDF, demoMode = false) {
  const pageW = doc.internal.pageSize.getWidth();
  const pageH = doc.internal.pageSize.getHeight();

  doc.setDrawColor(PDF_THEME.border[0], PDF_THEME.border[1], PDF_THEME.border[2]);
  doc.setLineWidth(0.3);
  doc.line(10, pageH - 14, pageW - 10, pageH - 14);

  doc.setFontSize(6.4);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(PDF_THEME.muted[0], PDF_THEME.muted[1], PDF_THEME.muted[2]);

  doc.text(
    'SENTINEL Digital Asset Protection Systems · Google Solution Challenge 2026 · Polygon Amoy Testnet',
    pageW / 2,
    pageH - 9.2,
    { align: 'center' }
  );
  doc.text(
    `Generated: ${new Date().toISOString()} · Issued electronically by SENTINEL for evidentiary and compliance use.`,
    pageW / 2,
    pageH - 5,
    { align: 'center' }
  );

  if (demoMode) {
    doc.setFontSize(6.6);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(180, 83, 9);
    doc.text(
      'This certificate was generated in DEMO MODE and is not an on-chain legal record.',
      pageW / 2,
      pageH - 1.5,
      { align: 'center' }
    );
  }
}

function drawSectionLine(doc: jsPDF, y: number) {
  const pageW = doc.internal.pageSize.getWidth();
  doc.setDrawColor(PDF_THEME.border[0], PDF_THEME.border[1], PDF_THEME.border[2]);
  doc.setLineWidth(0.2);
  doc.line(10, y, pageW - 10, y);
}

function kvWrapped(doc: jsPDF, label: string, value: string, x: number, y: number, maxWidth: number): number {
  doc.setFontSize(7.2);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(PDF_THEME.muted[0], PDF_THEME.muted[1], PDF_THEME.muted[2]);
  doc.text(label.toUpperCase(), x, y);

  doc.setFontSize(8.3);
  doc.setFont(label.toLowerCase().includes('tx hash') ? 'courier' : 'helvetica', 'normal');
  doc.setTextColor(PDF_THEME.text[0], PDF_THEME.text[1], PDF_THEME.text[2]);
  const valueLines = doc.splitTextToSize(value, maxWidth);
  doc.text(valueLines, x + 45, y);

  const linesHeight = valueLines.length * 3.8;
  return y + Math.max(6.8, linesHeight + 1.3);
}

function drawTitleBlock(doc: jsPDF, title: string, y: number): number {
  const pageW = doc.internal.pageSize.getWidth();

  doc.setFillColor(PDF_THEME.accentSoft[0], PDF_THEME.accentSoft[1], PDF_THEME.accentSoft[2]);
  doc.roundedRect(10, y, pageW - 20, 16, 2, 2, 'F');
  doc.setDrawColor(PDF_THEME.border[0], PDF_THEME.border[1], PDF_THEME.border[2]);
  doc.setLineWidth(0.3);
  doc.roundedRect(10, y, pageW - 20, 16, 2, 2, 'S');

  doc.setFontSize(6.8);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(PDF_THEME.muted[0], PDF_THEME.muted[1], PDF_THEME.muted[2]);
  doc.text('DOCUMENT CLASS', 16, y + 5.2);

  doc.setFontSize(10);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(PDF_THEME.text[0], PDF_THEME.text[1], PDF_THEME.text[2]);
  const titleLines = doc.splitTextToSize(title, pageW - 32);
  doc.text(titleLines, 16, y + 10.7);

  return y + 21;
}

function drawSectionTitle(doc: jsPDF, title: string, y: number): number {
  doc.setFontSize(8.9);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(PDF_THEME.text[0], PDF_THEME.text[1], PDF_THEME.text[2]);
  doc.text(title, 10, y);
  y += 3.8;
  drawSectionLine(doc, y);
  return y + 5.8;
}

function sanitizeFilenamePart(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9-]/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 40);
}

function savePdfForDevice(doc: jsPDF, filename: string): void {
  const blob = doc.output('blob');
  const url = URL.createObjectURL(blob);
  const ua = navigator.userAgent || '';
  const isIOSLike =
    /iPad|iPhone|iPod/i.test(ua) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);

  if (isIOSLike) {
    const opened = window.open(url, '_blank');
    if (!opened) {
      window.location.href = url;
    }
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
    return;
  }

  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);

  setTimeout(() => URL.revokeObjectURL(url), 2_000);
}

export function downloadSentinelPdf(opts: SentinelPdfOptions): void {
  const doc = new jsPDF({ unit: 'mm', format: 'a4', orientation: 'portrait' });
  const pageW = doc.internal.pageSize.getWidth();
  const pageH = doc.internal.pageSize.getHeight();
  const valueWidth = pageW - 65;
  const jurisdiction = normalizeJurisdiction(opts.jurisdiction || opts.country);
  const legalTemplate = legalNoticeTemplate(jurisdiction);
  const contentTop = 30;
  const contentBottom = pageH - 18;

  const issuerDetails: Array<[string, string | undefined]> = [
    ['Country / Jurisdiction', opts.country || opts.jurisdiction],
    ['Legal Entity', opts.legalEntityName || opts.orgName],
    ['Registered Address', opts.legalAddress],
    ['Postal / ZIP Code', opts.postalCode],
    ['Registration ID', opts.registrationId],
    ['Tax ID', opts.taxId],
    ['Notice Email', opts.noticeEmail],
    ['Official Contact', opts.contactPhone],
  ];

  const applyPageBranding = () => {
    doc.setFillColor(PDF_THEME.pageBg[0], PDF_THEME.pageBg[1], PDF_THEME.pageBg[2]);
    doc.rect(0, 0, pageW, pageH, 'F');
    drawWatermark(doc);
    drawHeader(doc, opts.type, legalTemplate.headerLabel);
  };

  let y = contentTop;

  const startNewPage = () => {
    doc.addPage();
    applyPageBranding();
    y = contentTop;
  };

  const ensureSpace = (neededHeight: number) => {
    if (y + neededHeight > contentBottom) {
      startNewPage();
    }
  };

  const drawSectionTitleSafe = (title: string) => {
    ensureSpace(10);
    y = drawSectionTitle(doc, title, y);
  };

  const kvSafe = (label: string, value: string) => {
    doc.setFontSize(9);
    doc.setFont(label.toLowerCase().includes('tx hash') ? 'courier' : 'helvetica', 'normal');
    const valueLines = doc.splitTextToSize(value, valueWidth);
    const needed = Math.max(7, valueLines.length * 3.8 + 1.5) + 1;
    ensureSpace(needed);
    y = kvWrapped(doc, label, value, 10, y, valueWidth);
  };

  const drawParagraphWithPaging = (text: string, x: number, width: number, lineHeight = 4.2) => {
    const lines = doc.splitTextToSize(text, width) as string[];
    let index = 0;

    while (index < lines.length) {
      ensureSpace(lineHeight * 2);
      const availableLines = Math.max(1, Math.floor((contentBottom - y) / lineHeight));
      const chunk = lines.slice(index, index + availableLines);
      doc.text(chunk, x, y);
      y += chunk.length * lineHeight;
      index += chunk.length;
      if (index < lines.length) {
        startNewPage();
      }
    }
    y += 2;
  };

  applyPageBranding();

  // Reference badge
  ensureSpace(14);
  doc.setFillColor(244, 249, 255);
  doc.roundedRect(10, y, pageW - 20, 10, 2, 2, 'F');
  doc.setDrawColor(PDF_THEME.border[0], PDF_THEME.border[1], PDF_THEME.border[2]);
  doc.setLineWidth(0.3);
  doc.roundedRect(10, y, pageW - 20, 10, 2, 2, 'S');
  doc.setFontSize(7);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(PDF_THEME.accent[0], PDF_THEME.accent[1], PDF_THEME.accent[2]);
  doc.text(`Reference: ${opts.refId}`, 14, y + 6.4);
  doc.setTextColor(PDF_THEME.muted[0], PDF_THEME.muted[1], PDF_THEME.muted[2]);
  doc.text(
    `Issued: ${opts.date || new Date().toLocaleDateString('en-GB', { day: '2-digit', month: 'long', year: 'numeric' })}`,
    pageW - 14,
    y + 6.4,
    { align: 'right' }
  );
  y += 14;

  ensureSpace(30);
  y = drawTitleBlock(doc, opts.title, y - 2);

  // Asset info section
  drawSectionTitleSafe('Asset Information');

  kvSafe('Asset Name', opts.assetName);
  if (opts.orgName) kvSafe('Rights Holder', opts.orgName);
  if (opts.country) kvSafe('Country / Jurisdiction', opts.country);
  if (opts.txHash) kvSafe('TX Hash', opts.txHash);
  if (opts.platform) kvSafe('Platform', opts.platform);
  if (opts.url) kvSafe('Infringing URL', opts.url);
  if (opts.similarity) kvSafe('Similarity Match', opts.similarity);
  y += 4;

  // Blockchain proof section
  if (opts.txHash) {
    y += 1;
    drawSectionTitleSafe('Blockchain Proof');

    kvSafe('Network', opts.network || 'Polygon Amoy (Simulated)');
    kvSafe('Explorer', 'https://amoy.polygonscan.com/tx/' + opts.txHash);
    kvSafe('Status', opts.status || 'CONFIRMED (DEMO)');
    kvSafe('Protocol', 'SentinelAssetRegistry.sol v2.4');
    y += 2;
  }

  // Issuing entity / compliance section
  const hasIssuerDetails = issuerDetails.some(([, value]) => Boolean(value && value.trim()));
  if (hasIssuerDetails) {
    y += 1;
    drawSectionTitleSafe('Issuing Entity & Compliance Contact');
    issuerDetails.forEach(([label, value]) => {
      if (value && value.trim()) {
        kvSafe(label, value.trim());
      }
    });
    y += 2;
  }

  // Type-specific body
  if (opts.type === 'dmca') {
    const legalLines = doc.splitTextToSize(legalTemplate.body, pageW - 20) as string[];
    const legalEstimatedHeight = legalLines.length * 4.2 + 22;
    if (y + legalEstimatedHeight > contentBottom) {
      // Keep compliance/details on one page and move legal letter to next page.
      startNewPage();
    }

    y += 1;
    drawSectionTitleSafe(legalTemplate.sectionTitle);

    doc.setFontSize(8.3);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(PDF_THEME.text[0], PDF_THEME.text[1], PDF_THEME.text[2]);
    drawParagraphWithPaging(legalTemplate.body, 10, pageW - 20);
    y += 2;

    // CONFIRMED stamp
    ensureSpace(20);
    doc.setFillColor(16, 185, 129);
    setAlphaIfSupported(doc, 0.15);
    doc.roundedRect(pageW - 65, y - 2, 54, 14, 3, 3, 'F');
    setAlphaIfSupported(doc, 1);
    doc.setDrawColor(16, 185, 129);
    doc.setLineWidth(0.5);
    doc.roundedRect(pageW - 65, y - 2, 54, 14, 3, 3, 'S');
    doc.setFontSize(8);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(16, 185, 129);
    doc.text('SENTINEL VERIFIED', pageW - 38, y + 6.9, { align: 'center' });
  }

  if (opts.type === 'blockchain') {
    y += 1;
    drawSectionTitleSafe('Certificate of Provenance');

    doc.setFontSize(8.3);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(PDF_THEME.text[0], PDF_THEME.text[1], PDF_THEME.text[2]);
    const certText = `This certificate confirms that the above-referenced digital asset has been registered on the Polygon blockchain network via the SENTINEL SentinelAssetRegistry smart contract. The cryptographic hash recorded in the transaction constitutes an immutable, timestamped proof of original ownership that can be independently verified by any party using the Polygonscan explorer link provided above.\n\nThis document is machine-verifiable and legally admissible as evidence of intellectual property ownership in jurisdictions that recognize electronic evidence.`;
    drawParagraphWithPaging(certText, 10, pageW - 20);
  }

  // Footer on every page
  const totalPages = doc.getNumberOfPages();
  for (let page = 1; page <= totalPages; page++) {
    doc.setPage(page);
    drawFooter(doc, Boolean(opts.demoMode));
  }

  // Save
  const dateStr = new Date().toISOString().split('T')[0];
  const assetSlug = sanitizeFilenamePart(opts.assetName || 'asset');
  const refSlug = sanitizeFilenamePart(opts.refId || 'ref');
  const filename = `SENTINEL-${opts.type.toUpperCase()}-${assetSlug}-${refSlug}-${dateStr}.pdf`;

  savePdfForDevice(doc, filename);
}
