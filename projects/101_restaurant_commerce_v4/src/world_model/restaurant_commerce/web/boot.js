/* ES5 capability fallback: no checkout is enabled before the application starts. */
(function () {
  var ok = !!(window.fetch && window.Promise && window.URL && window.AbortController && window.Intl);
  window.CommerceSupported = ok;
  if (!ok) document.addEventListener('DOMContentLoaded', function () {
    var box = document.getElementById('bootNotice');
    if (box) box.textContent = 'Este navegador no permite pedir con seguridad. Usa un navegador actualizado o contacta directamente al restaurante. No se ha enviado ningún pedido.';
    var controls = document.querySelectorAll('button');
    for (var i=0;i<controls.length;i++) controls[i].disabled = true;
  });
})();
