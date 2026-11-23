% rebase('base', title=title, active=active, flash=flash)
% avail = data['availability']
% counts = data['counts']
<div class="head">
    <h1>Огляд готелю</h1>
    <div class="actions">
        <a class="btn primary" href="/stays/check-in">Заселити клієнта</a>
        <a class="btn" href="/clients/new">Новий клієнт</a>
    </div>
</div>

<section class="cards">
    <div class="card">
        <span class="num">{{avail['free_rooms']}}</span>
        <span class="lbl">вільних номерів із {{counts['rooms']}}</span>
    </div>
    <div class="card">
        <span class="num">{{avail['free_places']}}</span>
        <span class="lbl">вільних місць</span>
    </div>
    <div class="card">
        <span class="num">{{counts['guests']}}</span>
        <span class="lbl">проживають зараз</span>
    </div>
    <div class="card">
        <span class="num">{{counts['clients']}}</span>
        <span class="lbl">клієнтів у базі</span>
    </div>
    <div class="card">
        <span class="num">{{counts['employees']}}</span>
        <span class="lbl">службовців</span>
    </div>
</section>

<section class="panel">
    <div class="panel-head">
        <h2>Хто проживає зараз</h2>
        <a href="/stays">Усі проживання</a>
    </div>
    % if data['current']:
    <div class="table-wrap">
    <table>
        <thead><tr><th>Клієнт</th><th>Номер</th><th>Тип</th><th>Заселено</th><th class="num">Діб</th><th></th></tr></thead>
        <tbody>
        % for s in data['current']:
        <tr>
            <td><a href="/clients/{{s['client_id']}}">{{s['client_name']}}</a></td>
            <td>{{s['room_number']}}</td>
            <td>{{s['room_type']}}</td>
            <td>{{fmt_date(s['checkin_date'])}}</td>
            <td class="num">{{s['days']}}</td>
            <td class="row-actions">
                <form method="post" action="/stays/{{s['stay_id']}}/check-out" class="inline">
                    <input type="hidden" name="back" value="{{here}}">
                    <button class="btn small" type="submit">Виселити</button>
                </form>
            </td>
        </tr>
        % end
        </tbody>
    </table>
    </div>
    % else:
    <p class="empty">Зараз у готелі ніхто не проживає.</p>
    % end
</section>