% if error:
<div class="flash error" role="alert">{{error}}</div>
% elif errors:
<div class="flash error" role="alert">Дані не збережено: виправте позначені поля.</div>
% end
