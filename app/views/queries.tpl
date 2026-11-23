% rebase('base', title=title, active=active, flash=flash)
% errors = result['errors']
<div class="head"><h1>Запити з варіанта завдання</h1></div>
<form method="get" action="/queries" class="form compact" novalidate>
    <div class="grid four">
    % include('field', name='room', label='Номер кімнати (запит 1)', value=params['room'], errors=errors, attrs='inputmode="numeric"')
    % include('field', name='city', label='Місто (запит 2)', value=params['city'], errors=errors)
    % include('field', name='passport', label='Паспорт клієнта (запит 3)', value=params['passport'], errors=errors)
    % include('field', name='weekday', label='День тижня 1–7 (запит 3)', value=params['weekday'], errors=errors, attrs='inputmode="numeric"')
    </div>
    <div class="form-actions"><button class="btn primary" type="submit">Виконати запити</button></div>
</form>

<section class="panel">
    <div class="panel-head"><h2>1. Клієнти, які проживають у номері {{params['room']}}</h2></div>
    % if 'q1' not in result:
    <p class="empty">Виправте номер кімнати.</p>
    % elif result['q1']:
    <div class="table-wrap"><table>
        <thead><tr><th>Клієнт</th><th>Паспорт</th><th>Місто</th><th>Заселено</th></tr></thead>
        <tbody>
        % for row in result['q1']:
        <tr><td>{{row['client'].full_name}}</td><td>{{row['client'].passport_number}}</td><td>{{row['client'].city}}</td><td>{{fmt_date(row['checkin_date'])}}</td></tr>
        % end
        </tbody>
    </table></div>
    % else:
    <p class="empty">У номері зараз ніхто не проживає.</p>
    % end
</section>

<section class="panel">
    <div class="panel-head"><h2>2. Клієнти, які прибули з міста «{{params['city']}}»</h2></div>
    % if 'q2' not in result:
    <p class="empty">Вкажіть місто.</p>
    % elif result['q2']:
    <div class="table-wrap"><table>
        <thead><tr><th>Клієнт</th><th>Паспорт</th><th>Місто</th></tr></thead>
        <tbody>
        % for c in result['q2']:
        <tr><td>{{c.full_name}}</td><td>{{c.passport_number}}</td><td>{{c.city}}</td></tr>
        % end
        </tbody>
    </table></div>
    % else:
    <p class="empty">Клієнтів із цього міста немає.</p>
    % end
</section>

<section class="panel">
    <div class="panel-head"><h2>3. Хто прибирав номер клієнта {{params['passport']}} у день тижня {{params['weekday']}}</h2></div>
    % if 'q3' not in result:
    <p class="empty">Виправте паспорт або день тижня.</p>
    % elif result['q3']:
    <div class="table-wrap"><table>
        <thead><tr><th>Службовець</th><th>Поверх</th><th>Номер клієнта</th></tr></thead>
        <tbody>
        % for row in result['q3']:
        <tr><td>{{row['employee'].full_name}}</td><td>{{row['floor']}}</td><td>{{row['room_number']}}</td></tr>
        % end
        </tbody>
    </table></div>
    % else:
    <p class="empty">Цього дня поверх клієнта ніхто не прибирає, або клієнт зараз не проживає в готелі.</p>
    % end
</section>

<section class="panel">
    <div class="panel-head"><h2>4. Вільні номери та вільні місця</h2></div>
    % q4 = result['q4']
    <div class="cards slim">
        <div class="card"><span class="num">{{q4['free_rooms']}}</span><span class="lbl">вільних номерів</span></div>
        <div class="card"><span class="num">{{q4['free_places']}}</span><span class="lbl">вільних місць</span></div>
    </div>
    <div class="table-wrap"><table>
        <thead><tr><th>Номер</th><th>Тип</th><th class="num">Місткість</th><th class="num">Проживає</th><th class="num">Вільних місць</th></tr></thead>
        <tbody>
        % for r in q4['rooms']:
        <tr><td>{{r['room_number']}}</td><td>{{r['type_name']}}</td><td class="num">{{r['capacity']}}</td><td class="num">{{r['occupied']}}</td><td class="num">{{r['capacity'] - r['occupied']}}</td></tr>
        % end
        </tbody>
    </table></div>
</section>
