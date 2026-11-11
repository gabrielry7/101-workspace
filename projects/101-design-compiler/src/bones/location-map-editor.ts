const color = (label: string, initial: string) => ({ label, initial, kind: 'color' } as const);
const toggle = (label: string, initial: boolean) => ({ label, initial, kind: 'checkbox' } as const);
const range = (label: string, initial: number, min: number, max: number, step: number) =>
  ({ label, initial, min, max, step, kind: 'range' } as const);
const choice = (label: string, initial: string, options: Record<string, string>) =>
  ({ label, initial, options, kind: 'select' } as const);

export const openFreeMapFields = {
  land: color('Fondo del mapa', '#f3e9dc'),
  vegetation: color('Vegetación', '#e2cfb8'),
  water: color('Agua', '#c6d7d4'),
  building: color('Edificios', '#e2cfb8'),
  buildingOutline: color('Borde de edificios', '#bea58f'),
  road: color('Calles y vías', '#fffdf8'),
  roadOutline: color('Borde de vías', '#bea58f'),
  roadText: color('Nombres de calles', '#3d302c'),
  roadHalo: color('Halo de nombres', '#fffdf8'),
  showVegetation: toggle('Mostrar vegetación', true),
  vegetationOpacity: range('Opacidad de vegetación (%)', 42, 0, 100, 1),
  showWater: toggle('Mostrar agua', true),
  waterOpacity: range('Opacidad del agua (%)', 100, 0, 100, 1),
  showBuildings: toggle('Mostrar edificios', true),
  buildingOpacity: range('Opacidad de edificios (%)', 100, 0, 100, 1),
  buildingMinZoom: range('Zoom mínimo de edificios', 13, 3, 18, 1),
  showMainRoads: toggle('Vías principales', true),
  showLocalRoads: toggle('Calles locales', true),
  showPaths: toggle('Caminos y senderos', true),
  roadOpacity: range('Opacidad de vías (%)', 100, 0, 100, 1),
  roadScale: range('Grosor de vías (%)', 100, 25, 250, 5),
  roadCasing: range('Grosor del borde de vías (px)', 1.5, 0, 6, 0.1),
  roadCap: choice('Terminación de líneas', 'round', { round: 'Redonda', butt: 'Recta', square: 'Cuadrada' }),
  roadJoin: choice('Unión de líneas', 'round', { round: 'Redonda', bevel: 'Biselada', miter: 'En ángulo' }),
  showRoadNames: toggle('Mostrar nombres de calles', true),
  roadTextOpacity: range('Opacidad de nombres (%)', 100, 0, 100, 1),
  roadFont: choice('Tipografía de nombres', 'sans', { sans: 'Familjen Grotesk', serif: 'Bodoni Moda' }),
  roadTextPlacement: choice('Posición de nombres', 'line', { line: 'A lo largo de la vía', 'line-center': 'En el centro de la vía' }),
  roadTextSize: range('Tamaño de nombres (px)', 13, 8, 26, 1),
  roadTextSpacing: range('Separación de nombres (px)', 260, 80, 500, 10),
  roadHaloWidth: range('Grosor del halo (px)', 1.2, 0, 4, 0.1),
  roadTextMinZoom: range('Zoom mínimo de nombres', 13, 3, 18, 1),
  bearing: range('Rotación (°)', 0, -180, 180, 1),
  pitch: range('Inclinación (°)', 0, 0, 60, 1),
  scrollZoom: toggle('Zoom con rueda o trackpad (Ctrl)', true),
  dragPan: toggle('Permitir arrastrar el mapa', true),
};

const previewFields = {
  showZoomButtons: toggle('Mostrar botones de zoom', true),
  pinDot: color('Color del punto del pin', '#bf0000'),
  pinDotSize: range('Diámetro del punto (px)', 14, 6, 24, 1),
  pinScale: range('Tamaño del pin (%)', 100, 60, 160, 5),
  pinStroke: range('Grosor del borde del pin (px)', 2.6, 0, 6, 0.1),
  showLogo: toggle('Mostrar logo en el pin', true),
  logoScale: range('Tamaño del logo (%)', 69, 30, 84, 1),
  labelPaper: color('Fondo de etiqueta del pin', '#ffffff'),
  labelInk: color('Texto de etiqueta del pin', '#222222'),
  labelLine: color('Borde de etiqueta del pin', '#bf0000'),
  labelSize: range('Tamaño de etiqueta del pin (px)', 14, 10, 24, 1),
  sectionCustom: toggle('Usar colores personalizados', false),
  sectionPaper: color('Fondo de sección', '#fffaf1'),
  sectionInk: color('Texto de sección', '#201c1b'),
  sectionLine: color('Borde de sección', '#d4b7a5'),
  sectionAccent: color('Título y acentos', '#bf0000'),
  sectionFont: choice('Tipografía', 'skin', { skin: 'Según la piel', familjen: 'Familjen Grotesk', georgia: 'Georgia', system: 'Sistema' }),
  titleScale: range('Tamaño del título (%)', 100, 75, 130, 5),
};

export const locationEditorFields = { ...openFreeMapFields, ...previewFields };
type Field = (typeof locationEditorFields)[keyof typeof locationEditorFields];
type Values<T extends Record<string, Field>> = { [Key in keyof T]: T[Key]['initial'] };
export type OpenFreeMapOptions = Values<typeof openFreeMapFields>;
export type LocationEditorOptions = Values<typeof locationEditorFields>;

export const locationEditorGroups = [
  { title: 'Colores del mapa', open: true, fields: [
    'land', 'vegetation', 'water', 'building', 'buildingOutline', 'road', 'roadOutline', 'roadText', 'roadHalo',
  ] },
  { title: 'Capas y estilos', fields: [
    'showVegetation', 'vegetationOpacity', 'showWater', 'waterOpacity', 'showBuildings', 'buildingOpacity',
    'buildingMinZoom', 'showMainRoads', 'showLocalRoads', 'showPaths', 'roadOpacity', 'roadScale', 'roadCasing',
    'roadCap', 'roadJoin', 'showRoadNames', 'roadTextOpacity', 'roadFont', 'roadTextPlacement', 'roadTextSize',
    'roadTextSpacing', 'roadHaloWidth', 'roadTextMinZoom',
  ] },
  { title: 'Cámara e interacción', fields: ['bearing', 'pitch', 'scrollZoom', 'dragPan', 'showZoomButtons'], recenter: true },
  { title: 'Pin, logo y etiqueta', fields: [
    'pinDot', 'pinDotSize', 'pinScale', 'pinStroke', 'showLogo', 'logoScale', 'labelPaper', 'labelInk', 'labelLine', 'labelSize',
  ] },
  { title: 'Colores y tipografía de la sección', fields: [
    'sectionCustom', 'sectionPaper', 'sectionInk', 'sectionLine', 'sectionAccent', 'sectionFont', 'titleScale',
  ] },
] satisfies { title: string; open?: boolean; fields: (keyof LocationEditorOptions)[]; recenter?: boolean }[];

function defaults<T extends Record<string, Field>>(fields: T): Values<T> {
  return Object.fromEntries(Object.entries(fields).map(([key, field]) => [key, field.initial])) as Values<T>;
}

function validate<T extends Record<string, Field>>(fields: T, value: unknown): Values<T> {
  if (!value || typeof value !== 'object' || Array.isArray(value)
    || Object.keys(value).length !== Object.keys(fields).length) throw Error('INVALID_LOCATION_EDITOR');
  const input = value as Record<string, unknown>;
  for (const [key, field] of Object.entries(fields)) {
    const setting = input[key];
    let valid;
    switch (field.kind) {
      case 'color': valid = typeof setting === 'string' && /^#[a-f0-9]{6}$/i.test(setting); break;
      case 'checkbox': valid = typeof setting === 'boolean'; break;
      case 'range': valid = typeof setting === 'number' && setting >= field.min && setting <= field.max; break;
      case 'select': valid = typeof setting === 'string' && Object.hasOwn(field.options, setting); break;
    }
    if (!Object.hasOwn(input, key) || !valid) throw Error('INVALID_LOCATION_EDITOR_FIELD:' + key);
  }
  return { ...input } as Values<T>;
}

type MapColors = Pick<OpenFreeMapOptions, 'land' | 'water' | 'building' | 'road' | 'roadOutline'>;
export function openFreeMapDefaults(colors: MapColors): OpenFreeMapOptions {
  return { ...defaults(openFreeMapFields), land: colors.land, water: colors.water, building: colors.building,
    road: colors.road, roadOutline: colors.roadOutline, vegetation: colors.building,
    buildingOutline: colors.roadOutline, roadHalo: colors.road };
}

export function locationEditorDefaults(colors: MapColors & { pin: string }): LocationEditorOptions {
  return { ...openFreeMapDefaults(colors), ...defaults(previewFields), pinDot: colors.pin };
}

export const parseLocationEditor = (value: unknown) => validate(locationEditorFields, value);
export const parseOpenFreeMapOptions = (value: unknown) => validate(openFreeMapFields, value);
export function mapEditorOptions(value: LocationEditorOptions): OpenFreeMapOptions {
  return Object.fromEntries(Object.keys(openFreeMapFields).map(key =>
    [key, value[key as keyof OpenFreeMapOptions]])) as OpenFreeMapOptions;
}
