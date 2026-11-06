export const FOOTER_BONE = {id: 'footer.directory-watermark', version: '0.1.0', status: 'reconstructed-unapproved'} as const;

export const footerAnatomy = [
  ['transition', 'Banda de transición', 'surface'],
  ['assistants', 'Accesos de IA', 'surface'],
  ['identity', 'Identidad y propuesta', 'surface'],
  ['backers', 'Respaldos', 'surface'],
  ['directory', 'Directorio', 'surface'],
  ['group', 'Grupo de enlaces', 'surface'],
  ['group-title', 'Título de grupo', 'text'],
  ['item', 'Acción o elemento futuro', 'action'],
  ['watermark', 'Marca decorativa recortada', 'surface'],
  ['legal', 'Barra legal', 'surface'],
].map(([role, label, kind]) => ({
  id: 'footer.directory-watermark.' + role,
  role: role!, label: label!, kind: kind!,
  selector: '[data-footer-part="' + role + '"]',
  status: 'new',
  source: 'src/components/bones/footer/DirectoryFooter.astro',
}));

export const measurementOwners = {
  shared: '101-world-model/packages/component-preview/measure.js',
  sharedCommit: '6c0ed29940985bfb1789280c1972e47386775193',
  extension: 'src/bones/footer/measure.ts',
  actions: 'native HTML links/buttons; footer-specific state adapter',
};
