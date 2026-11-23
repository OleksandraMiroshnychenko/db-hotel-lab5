% rebase('base', title=title, active=active, flash=flash)
<div class="head">
    <h1>Типи номерів</h1>
    <div class="actions"><a class="btn primary" href="/room-types/new">Додати тип</a></div>
</div>
<div class="table-wrap">
<table>
    <thead><tr><th>Назва</th><th class="num">Місткість</th><th class="num">Ціна за добу</th><th class="num">Номерів</th><th></th></tr></thead>
    <tbody>
    % for t in types:
    <tr>
        <td><strong>{{t['name']}}</strong></td>
        <td class="num">{{t['capacity']}}</td>
        <td class="num">{{fmt_money(t['price_per_day'])}}</td>
        <td class="num">{{t['rooms']}}</td>
        <td class="row-actions">
            <a class="btn small" href="/room-types/{{t['room_type_id']}}/edit">Змінити</a>
            <form method="post" action="/room-types/{{t['room_type_id']}}/delete" class="inline"
                  onsubmit="return confirm('Видалити тип «{{t['name']}}»?')">
                <button class="btn small danger" type="submit">Видалити</button>
            </form>
        </td>
    </tr>
    % end
    </tbody>
</table>
</div>
<p class="note">Зміна ціни або місткості типу оновлює кеш усіх номерів цього типу. Місткість не можна зменшити нижче кількості людей, які проживають у номері зараз: це перевіряє тригер бази даних.</p>
