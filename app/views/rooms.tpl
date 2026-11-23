% rebase('base', title=title, active=active, flash=flash)
<div class="head">
    <h1>Номери</h1>
    <div class="actions"><a class="btn primary" href="/rooms/new">Додати номер</a></div>
</div>
<div class="table-wrap">
<table>
    <thead>
        <tr><th>№</th><th>Поверх</th><th>Тип</th><th class="num">Місць</th><th class="num">Ціна за добу</th>
            <th>Телефон</th><th>Заповненість</th><th></th></tr>
    </thead>
    <tbody>
    % for r in rooms:
    <tr>
        <td><strong>{{r['room_number']}}</strong></td>
        <td>{{r['floor']}}</td>
        <td>{{r['room_type']}}</td>
        <td class="num">{{r['capacity']}}</td>
        <td class="num">{{fmt_money(r['price_per_day'])}}</td>
        <td>{{r['phone']}}</td>
        <td>
            % if r['occupied'] == 0:
            <span class="badge free">вільний</span>
            % elif r['free_places'] == 0:
            <span class="badge full">зайнятий</span>
            % else:
            <span class="badge part">є {{r['free_places']}} вільне місце</span>
            % end
            <span class="muted">{{r['occupied']}} / {{r['capacity']}}</span>
        </td>
        <td class="row-actions">
            % if r['free_places'] > 0:
            <a class="btn small" href="/stays/check-in?room={{r['room_number']}}">Заселити</a>
            % end
            <a class="btn small" href="/rooms/{{r['room_id']}}/edit">Змінити</a>
            <form method="post" action="/rooms/{{r['room_id']}}/delete" class="inline"
                  onsubmit="return confirm('Видалити номер {{r['room_number']}}?')">
                <button class="btn small danger" type="submit">Видалити</button>
            </form>
        </td>
    </tr>
    % end
    </tbody>
</table>
</div>
