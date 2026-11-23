% rebase('base', title=title, active=active, flash=flash)
<div class="head"><h1>Графік прибирання: {{employee['full_name']}}</h1></div>
% include('form_error', error=error, errors=errors)
<form method="post" action="/employees/{{employee['employee_id']}}/schedule" class="form" novalidate>
    <p class="note">Вкажіть, який поверх службовець прибирає в кожен день тижня. Порожнє поле означає, що цього дня він не прибирає. Усі зміни виконуються в одній транзакції: якщо хоч один поверх вказано неправильно, графік не зміниться взагалі. Поверхи, які є в готелі: {{', '.join(str(f) for f in floors)}}.</p>
    <div class="grid">
    % for d in range(1, 8):
    % include('field', name='floor_%d' % d, label=WEEKDAYS[d - 1].capitalize(), value=raw.get('floor_%d' % d, ''), errors=errors, type='number', attrs='min="1" max="99" placeholder="—"')
    % end
    </div>
    <div class="form-actions">
        <button class="btn primary" type="submit">Зберегти графік</button>
        <a class="btn" href="/employees">Скасувати</a>
    </div>
</form>
