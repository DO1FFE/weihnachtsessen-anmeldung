document.addEventListener('DOMContentLoaded', function() {
  function update() {
    const value = parseInt(document.getElementById('additional').value || '0');
    const count = 1 + value;
    document.getElementById('person-count').innerText =
      'Anmeldung für ' + count + ' Person' + (count > 1 ? 'en' : '');
  }
  const input = document.getElementById('additional');
  if (input) {
    input.addEventListener('input', update);
    update();
  }
});
