% rebase('base', title=title, active=active, flash=flash)
<div class="head"><h1>Заселення клієнта</h1></div>
% include('form_error', error=error, errors=errors)
<form method="post" action="/stays/check-in" class="form" novalidate>
    <p class="note">Операцію виконує збережена процедура <code>check_in</code> в одній транзакції: якщо заселити не вдалося (номер заповнений, клієнт уже проживає в цей період), новий клієнт теж не зберігається.</p>
    <div class="grid">
    % include('field', name='passport_number', label='Паспорт', value=raw.get('passport_number', ''), errors=errors, required=True, hint='Серія й номер (ЕК123456) або 9 цифр ID-картки')
    % include('select_field', name='room_number', label='Номер', value=raw.get('room_number', ''), errors=errors, required=True, blank='— оберіть номер —', options=[(r['room_number'], '%s · %s · вільно %s з %s' % (r['room_number'], r['room_type'], r['free_places'], r['capacity'])) for r in rooms])
    % include('field', name='checkin_date', label='Дата заселення', value=raw.get('checkin_date', today()), errors=errors, type='date', required=True, attrs='max="%s"' % today())
    </div>
    <fieldset>
        <legend>Дані клієнта</legend>
        <p class="hint">Потрібні лише для нового клієнта. Якщо клієнт із таким паспортом уже є в базі, ці поля ігноруються.</p>
        <div class="grid">
        % include('field', name='last_name', label='Прізвище', value=raw.get('last_name', ''), errors=errors)
        % include('field', name='first_name', label='Імʼя', value=raw.get('first_name', ''), errors=errors)
        % include('field', name='patronymic', label='По батькові', value=raw.get('patronymic', ''), errors=errors)
        % include('field', name='city', label='Місто', value=raw.get('city', ''), errors=errors)
        </div>
    </fieldset>
    <div class="form-actions">
        <button class="btn primary" type="submit">Заселити</button>
        <a class="btn" href="/stays">Скасувати</a>
    </div>
</form>
