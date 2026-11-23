% rebase('base', title=title, active=active, flash=flash)
<div class="head">
    <h1>Проживання</h1>
    <div class="actions"><a class="btn primary" href="/stays/check-in">Заселити клієнта</a></div>
</div>
<div class="toolbar">
    <div class="tabs">
        <a href="/stays?scope=current{{'&q=' + urlq(q) if q else ''}}" class="{{'active' if scope != 'all' else ''}}">Проживають зараз</a>
        <a href="/stays?scope=all{{'&q=' + urlq(q) if q else ''}}" class="{{'active' if scope == 'all' else ''}}">Уся історія</a>
    </div>
    <form method="get" action="/stays" class="search">
        <input type="hidden" name="scope" value="{{scope}}">
        <input type="search" name="q" value="{{q}}" placeholder="Прізвище, паспорт або номер кімнати" aria-label="Пошук проживань">
        <button class="btn" type="submit">Знайти</button>
    </form>
</div>
% if stays:
<div class="table-wrap">
<table>
    <thead><tr><th>Клієнт</th><th>Паспорт</th><th>Номер</th><th>Заселено</th><th>Виселено</th><th class="num">Діб</th><th></th></tr></thead>
    <tbody>
    % for s in stays:
    <tr>
        <td><a href="/clients/{{s['client_id']}}">{{s['client_name']}}</a></td>
        <td>{{s['passport_number']}}</td>
        <td>{{s['room_number']}} <span class="muted">{{s['room_type']}}</span></td>
        <td>{{fmt_date(s['checkin_date'])}}</td>
        <td>
            % if s['checkout_date']:
            {{fmt_date(s['checkout_date'])}}
            % else:
            <span class="badge part">проживає</span>
            % end
        </td>
        <td class="num">{{s['days']}}</td>
        <td class="row-actions">
            % if not s['checkout_date']:
            <form method="post" action="/stays/{{s['stay_id']}}/check-out" class="inline">
                <input type="hidden" name="back" value="{{here}}">
                <input type="date" name="checkout_date" value="{{today()}}" max="{{today()}}" aria-label="Дата виселення">
                <button class="btn small" type="submit">Виселити</button>
            </form>
            % end
            <a class="btn small" href="/stays/{{s['stay_id']}}/edit">Змінити</a>
            <form method="post" action="/stays/{{s['stay_id']}}/delete" class="inline"
                  onsubmit="return confirm('Видалити запис про проживання?')">
                <input type="hidden" name="back" value="{{here}}">
                <button class="btn small danger" type="submit">Видалити</button>
            </form>
        </td>
    </tr>
    % end
    </tbody>
</table>
</div>
% else:
<p class="empty">Проживань не знайдено.</p>
% end
