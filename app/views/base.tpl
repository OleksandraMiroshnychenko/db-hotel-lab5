<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{title}} · Готель</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
<header class="topbar">
    <a class="brand" href="/">Готель<span>адміністратор</span></a>
    <nav>
        % for key, label, url in nav_items:
        <a href="{{url}}" class="{{'active' if key == active else ''}}">{{label}}</a>
        % end
    </nav>
</header>
<main class="page">
    % if flash:
    <div class="flash {{flash['kind']}}" role="status">{{flash['text']}}</div>
    % for warning in flash.get('warnings', []):
    <div class="flash warn" role="alert">{{warning}}</div>
    % end
    % end
    {{!base}}
</main>
</body>
</html>
