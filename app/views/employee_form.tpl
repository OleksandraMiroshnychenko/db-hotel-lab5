% rebase('base', title=title, active=active, flash=flash)
<div class="head"><h1>{{title}}</h1></div>
% include('form_error', error=error, errors=errors)
<form method="post" action="{{action}}" class="form" novalidate>
    <div class="grid">
    % include('field', name='last_name', label='Прізвище', value=raw.get('last_name', ''), errors=errors, required=True)
    % include('field', name='first_name', label='Імʼя', value=raw.get('first_name', ''), errors=errors, required=True)
    % include('field', name='patronymic', label='По батькові', value=raw.get('patronymic', ''), errors=errors)
    </div>
    <div class="form-actions">
        <button class="btn primary" type="submit">Зберегти</button>
        <a class="btn" href="/employees">Скасувати</a>
    </div>
</form>
