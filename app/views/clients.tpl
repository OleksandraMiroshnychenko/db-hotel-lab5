% rebase('base', title=title, active=active, flash=flash)
<div class="head">
    <h1>Клієнти</h1>
    <div class="actions"><a class="btn primary" href="/clients/new">Додати клієнта</a></div>
</div>
<form method="get" action="/clients" class="search">
    <input type="search" name="q" value="{{q}}" placeholder="Прізвище, імʼя, паспорт або місто" aria-label="Пошук клієнтів">
    <button class="btn" type="submit">Знайти</button>
    % if q:
    <a href="/clients">Скинути</a>
    % end
</form>
% if clients:
<div class="table-wrap">
<table>
    <thead><tr><th>Клієнт</th><th>Паспорт</th><th>Місто</th><th>Номер зараз</th><th class="num">Проживань</th><th></th></tr></thead>
    <tbody>
    % for c in clients:
    <tr>
        <td><a href="/clients/{{c['client_id']}}">{{full_name(c)}}</a></td>
        <td>{{c['passport_number']}}</td>
        <td>{{c['city']}}</td>
        <td>
            % if c['current_room']:
            <span class="badge part">{{c['current_room']}}</span>
            % else:
            <span class="muted">—</span>
            % end
        </td>
        <td class="num">{{c['stays_count']}}</td>
        <td class="row-actions">
            <a class="btn small" href="/clients/{{c['client_id']}}/edit">Змінити</a>
            <form method="post" action="/clients/{{c['client_id']}}/delete" class="inline"
                  onsubmit="return confirm('Видалити клієнта {{c['last_name']}} разом з історією проживань?')">
                <button class="btn small danger" type="submit">Видалити</button>
            </form>
        </td>
    </tr>
    % end
    </tbody>
</table>
</div>
% else:
<p class="empty">Клієнтів не знайдено.</p>
% end
