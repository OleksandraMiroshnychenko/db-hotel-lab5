% rebase('base', title=title, active=active, flash=flash)
<div class="head">
    <h1>{{title}}</h1>
    <div class="actions">
        <a class="btn" href="/clients/{{client['client_id']}}/edit">Змінити</a>
        <a class="btn" href="/clients">До списку</a>
    </div>
</div>
<dl class="facts">
    <div><dt>Паспорт</dt><dd>{{client['passport_number']}}</dd></div>
    <div><dt>Місто</dt><dd>{{client['city']}}</dd></div>
</dl>
<section class="panel">
    <div class="panel-head"><h2>Історія проживань</h2></div>
    % if stays:
    <div class="table-wrap">
    <table>
        <thead><tr><th>Номер</th><th>Тип</th><th>Заселено</th><th>Виселено</th><th class="num">Діб</th><th></th></tr></thead>
        <tbody>
        % for s in stays:
        <tr>
            <td>{{s['room_number']}}</td>
            <td>{{s['room_type']}}</td>
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
                    <button class="btn small" type="submit">Виселити</button>
                </form>
                % end
                <a class="btn small" href="/stays/{{s['stay_id']}}/edit">Змінити</a>
            </td>
        </tr>
        % end
        </tbody>
    </table>
    </div>
    % else:
    <p class="empty">Проживань ще не було.</p>
    % end
</section>
