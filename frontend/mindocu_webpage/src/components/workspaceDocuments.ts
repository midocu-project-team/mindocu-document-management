import type { Segment } from './InnerSidebarLeft'

export type WorkspaceDocument = {
  id: string
  label: string
  pdfUrl: string
  segments: Segment[]
}

export const DEMO_WORKSPACE_DOCUMENTS: WorkspaceDocument[] = [
  {
    id: 'hauptakte',
    label: 'Hauptakte',
    pdfUrl: '/Demo_pdf.pdf',
    segments: [
      {
        title: 'Aktendeckel',
        date: '12.02.2026',
        range: '1',
        relevant: true,
        summary:
          'Dem Aktendeckel des Amtsgerichts Würzburg vom 12.02.2026 entnehmen wir, dass es um eine familienrechtliche Auseinandersetzung mit mehreren Beteiligten geht. Verfahrensart, Sachgebiet und Eingangsdatum sind hier zentral erfasst.',
      },
      {
        title: 'Antrag auf Umgangsänderung',
        date: '07.03.2026',
        range: '2-9',
        relevant: true,
        summary:
          'Der Antrag auf Umgangsänderung begründet die gewünschte Anpassung des Umgangsrechts mit Verweis auf die aktuelle Lebenssituation des Kindes. Die Parteien machen unterschiedliche Sichtweisen auf Alltagsorganisation und Betreuungsfähigkeit geltend.',
      },
      {
        title: 'Polizeibericht',
        date: '14.03.2026',
        range: '10-16',
        relevant: true,
        summary:
          'Der Polizeibericht dokumentiert den gemeldeten Vorfall, beteiligte Personen, Ort und Zeit sowie die polizeiliche Ersteinschätzung. Für die familienrechtliche Bewertung sind insbesondere die sachlichen Feststellungen vor Ort relevant.',
      },
      {
        title: 'Pflegebericht',
        date: '08.05.2026',
        range: '17-28',
        relevant: false,
        summary:
          'Der Pflegebericht beschreibt den Betreuungs- und Versorgungsbedarf, den Verlauf der Unterbringung sowie Rückmeldungen zu Stabilität, Schule und Tagesstruktur. Er liefert Anhaltspunkte für die weiteren gerichtlichen Entscheidungen.',
      },
    ],
  },
  {
    id: 'anlage-sachverhalt',
    label: 'Anlage Sachverhalt',
    pdfUrl: '/Demo_pdf2.pdf',
    segments: [
      {
        title: 'Sachverhaltsdarstellung',
        date: '18.02.2026',
        range: '1-4',
        relevant: true,
        summary:
          'Die Sachverhaltsdarstellung fasst den zeitlichen Ablauf der Streitigkeit zusammen und benennt die wesentlichen Ereignisse, die zum gegenwärtigen Verfahrensstand geführt haben.',
      },
      {
        title: 'Fotodokumentation',
        date: '19.02.2026',
        range: '5-9',
        relevant: false,
        summary:
          'Die Fotodokumentation ergänzt die schriftliche Schilderung um visuelle Belege zu Wohnsituation, Schäden oder relevanten Umständen, die im Verfahren strittig sind.',
      },
      {
        title: 'Zeugenaussage',
        date: '22.02.2026',
        range: '10-12',
        relevant: true,
        summary:
          'Die Zeugenaussage schildert Beobachtungen aus dem direkten Umfeld der Familie. Besonderes Gewicht haben Angaben zu Konfliktsituationen, Alltagsabläufen und dem Verhalten der Beteiligten.',
      },
    ],
  },
  {
    id: 'nebenakte-berichte',
    label: 'Nebenakte Berichte',
    pdfUrl: '/Demo_pdf3.pdf',
    segments: [
      {
        title: 'Jugendamtsbericht',
        date: '01.03.2026',
        range: '1-6',
        relevant: true,
        summary:
          'Der Jugendamtsbericht bewertet die Kindeswohlentwicklung, die Erziehungsfähigkeit der Sorgeberechtigten und den Unterstützungsbedarf aus Sicht der Jugendhilfe.',
      },
      {
        title: 'Schulbescheinigung',
        date: '04.03.2026',
        range: '7',
        relevant: false,
        summary:
          'Die Schulbescheinigung bestätigt Anwesenheit, Lernverhalten und besondere schulische Umstände des Kindes und dient als kurzer Beleg für die schulische Integration.',
      },
      {
        title: 'Arztbericht',
        date: '11.03.2026',
        range: '8-14',
        relevant: true,
        summary:
          'Der Arztbericht dokumentiert gesundheitliche Befunde, Behandlungsverlauf und medizinische Einschätzungen, die für Betreuung und Belastungsfähigkeit relevant sein können.',
      },
      {
        title: 'Therapieverlauf',
        date: '25.03.2026',
        range: '15-20',
        relevant: true,
        summary:
          'Der Therapieverlauf beschreibt Fortschritte, Rückschläge und therapeutische Empfehlungen. Er zeigt, welche Unterstützung bereits wirksam war und wo weiterer Bedarf besteht.',
      },
    ],
  },
]

export function createInitialSegmentsByDocument(): Record<string, Segment[]> {
  return Object.fromEntries(
    DEMO_WORKSPACE_DOCUMENTS.map((document) => [
      document.id,
      document.segments.map((segment) => ({ ...segment })),
    ]),
  )
}
