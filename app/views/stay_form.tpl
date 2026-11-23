% rebase('base', title=title, active=active, flash=flash)
<div class="head"><h1>{{title}}</h1></div>
% include('form_error', error=error, errors=errors)
<dl class="facts">
    <div><dt>Клієнт</dt><dd>{{stay['client_name']}}</dd></div>
    <div><dt>Паспорт</dt><dd>{{stay['passport_number']}}</dd></div>
</dl>
<form method="post" action="/stays/{{stay['stay_id']}}/edit" class="form" novalidate>
    <div class="grid">
    % include('select_field', name='room_number', label='Номер', value=raw.get('room_number', ''), errors=errors, required=True, options=[(r['room_number'], '%s · %s' % (r['room_number'], r['room_type'])) for r in rooms])
    % include('field', name='checkin_date', label='Дата заселення', value=raw.get('checkin_date', ''), errors=errors, type='date', required=True, attrs='max="%s"' % today())
    % include('field', name='checkout_date', label='Дата виселення', value=raw.get('checkout_date', ''), errors=errors, type='date', hint='Порожньо, якщо клієнт ще проживає', attrs='max="%s"' % today())
    </div>
    <p class="note">Місткість номера й неперетин періодів проживання клієнта перевіряють тригери бази даних.</p>
    <div class="form-actions">
        <button class="btn primary" type="submit">Зберегти</button>
        <a class="btn" href="/stays?scope=all">Скасувати</a>
    </div>
</form>
