% rebase('base', title=title, active=active, flash=flash)
<div class="head"><h1>{{title}}</h1></div>
% include('form_error', error=error, errors=errors)
<form method="post" action="{{action}}" class="form" novalidate>
    <div class="grid">
    % include('field', name='room_number', label='Номер кімнати', value=raw.get('room_number', ''), errors=errors, type='number', required=True, hint='Наприклад, 204: перша цифра — поверх', attrs='min="101" max="9999"')
    % include('field', name='floor', label='Поверх', value=raw.get('floor', ''), errors=errors, type='number', required=True, attrs='min="1" max="99"')
    % include('field', name='phone', label='Телефон', value=raw.get('phone', ''), errors=errors, type='tel', required=True, hint='Формат +380441234567')
    % include('select_field', name='room_type_id', label='Тип номера', value=raw.get('room_type_id', ''), errors=errors, required=True, blank='— оберіть тип —', options=[(t['room_type_id'], '%s · %s місць · %s' % (t['name'], t['capacity'], fmt_money(t['price_per_day']))) for t in types])
    </div>
    <div class="form-actions">
        <button class="btn primary" type="submit">Зберегти</button>
        <a class="btn" href="/rooms">Скасувати</a>
    </div>
</form>
