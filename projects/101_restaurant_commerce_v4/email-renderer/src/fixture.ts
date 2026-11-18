import type { EmailProps } from "./contract";
export const fixture: EmailProps = {
  schema_version: "1",
  font_base_url: "http://localhost:3000/static/",
  template_id: "matte",
  content: {
    subject: "Una nota de tu negocio",
    title: "Algo que vale la pena compartir",
    body: "Este es contenido de demostración para revisar el diseño.\n\nLas ofertas y los productos reales requieren confirmación del negocio.",
    terms: "Ejemplo de diseño. No representa una oferta real.",
    cta_label: "Ver más",
    expiry: "30/11/2026",
    label: "DEMOSTRACIÓN · SIN ENVÍO REAL",
  },
  brand: {
    name: "Negocio de ejemplo",
    logo_url: null,
    accent: null,
    font: null,
  },
  media: null,
  personalization: {
    name: "María",
    ordering_url: "https://example.com/pedir",
    unsubscribe_url: "https://example.com/baja",
  },
};
