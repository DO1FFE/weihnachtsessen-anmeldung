document.addEventListener('DOMContentLoaded', function() {
  const zusatzfeld = document.getElementById('additional');
  const anzeige = document.getElementById('person-count');

  if (!zusatzfeld || !anzeige) {
    return;
  }

  function aktualisierePersonen() {
    const wert = parseInt(zusatzfeld.value || '0', 10);
    const personen = 1 + wert;
    anzeige.textContent = 'Anmeldung für ' + personen + ' Person' + (personen > 1 ? 'en' : '');
  }

  zusatzfeld.addEventListener('input', aktualisierePersonen);
  aktualisierePersonen();
});
