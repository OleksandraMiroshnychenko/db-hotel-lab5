% rebase('base', title=title, active=active, flash=flash)
<div class="head">
    <h1>Службовці</h1>
    <div class="actions"><a class="btn primary" href="/employees/new">Прийняти на роботу</a></div>
</div>
<div class="table-wrap">
<table>
    <thead>
        <tr><th>Службовець</th>
            % for day in WEEKDAYS_SHORT:
            <th class="center">{{day}}</th>
            % end
            <th></th></tr>
    </thead>
    <tbody>
    % for e in employees:
    <tr>
        <td><strong>{{e['full_name']}}</strong></td>
        % for d in range(1, 8):
        <td class="center">
            % if d in e['schedule']:
            <span class="badge part">пов. {{e['schedule'][d]}}</span>
            % else:
            <span class="muted">—</span>
            % end
        </td>
        % end
        <td class="row-actions">
            <a class="btn small" href="/employees/{{e['employee_id']}}/schedule">Графік</a>
            <a class="btn small" href="/employees/{{e['employee_id']}}/edit">Змінити</a>
            <form method="post" action="/employees/{{e['employee_id']}}/delete" class="inline"
                  onsubmit="return confirm('Звільнити службовця {{e['last_name']}}? Його графік прибирання буде видалено.')">
                <button class="btn small danger" type="submit">Звільнити</button>
            </form>
        </td>
    </tr>
    % end
    </tbody>
</table>
</div>
<p class="note">Прийом на роботу, звільнення й зміну графіка виконують збережені процедури <code>hire_employee</code>, <code>fire_employee</code> та <code>change_schedule</code>. Графік звільненого службовця видаляється автоматично.</p>
