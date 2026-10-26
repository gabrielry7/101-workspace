// Presentation-only public labels for the current B3 renderer. The frozen rich-experience contract keeps its own labels and routes.
export const publicLabels:Record<string,string>={home:'Inicio',collection:'Menú',request:'Reservas',story:'Sobre el restaurante',visit:'Ubicación',faq:'Preguntas',journal:'Noticias',reviews:'Opiniones',contact:'Contacto',credits:'Créditos',selection:'Pedidos (retirado)'};
export const publicLabel=(kind:string)=>publicLabels[kind]??kind;
// Visitor-facing navigation order. "selection" is intentionally absent: it is a retired legacy URL, not a flow.
export const navKinds=['collection','request','story','visit','faq','journal','reviews','contact'] as const;
export const pageHeads:Record<string,{h:string;p?:string}>={
 collection:{h:'Menú',p:'Cuarenta platos de ejemplo en ocho categorías. Elige uno para ver sus ingredientes y datos.'},
 request:{h:'Reserva tu mesa',p:'Elige día, personas y ocasión. Es una demostración: no se envía nada ni se confirma ninguna mesa.'},
 story:{h:'Sobre el restaurante',p:'Quiénes somos y cómo entendemos una buena comida.'},
 visit:{h:'Ubicación',p:'Cómo llegar, horarios y servicios. El punto del mapa es un ejemplo, no una sede real.'},
 faq:{h:'Preguntas frecuentes',p:'Respuestas breves antes de venir.'},
 journal:{h:'Noticias',p:'Novedades y relatos de muestra del restaurante ficticio.'},
 reviews:{h:'Opiniones',p:'Opiniones de muestra, con personajes y textos ficticios.'},
 contact:{h:'Contacto',p:'Escríbenos o encuentra la vía que prefieras. Canales de ejemplo.'},
 credits:{h:'Créditos',p:'Las imágenes y el vídeo son ilustrativos. No representan una empresa, sus instalaciones o sus productos reales.'},
 selection:{h:'Esta página ya no está en uso',p:'La selección de platos fue una prueba de demostración y se ha retirado. Consulta el menú o reserva una mesa.'}
};
