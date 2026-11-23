% rebase('base', title=title, active=active, flash=flash)
<div class="head"><h1>{{title}}</h1></div>
% include('form_error', error=error, errors=errors)
<form method="post" action="{{action}}" class="form" novalidate>
    <div class="grid">
    % include('field', name='name', label='Назва типу', value=raw.get('name', ''), errors=errors, required=True, hint='Зберігається малими літерами, наприклад чотиримісний')
    % include('field', name='capacity', label='Місткість', value=raw.get('capacity', ''), errors=errors, type='number', required=True, hint='Від 1 до 3 осіб', attrs='min="1" max="3"')
    % include('field', name='price_per_day', label='Ціна за добу, грн', value=raw.get('price_per_day', ''), errors=errors, required=True, hint='Наприклад, 1200 або 1200.50', attrs='inputmode="decimal"')
    </div>
    <div class="form-actions">
        <button class="btn primary" type="submit">Зберегти</button>
        <a class="btn" href="/room-types">Скасувати</a>
    </div>
</form>
