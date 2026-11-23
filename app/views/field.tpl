% setdefault('type', 'text')
% setdefault('hint', '')
% setdefault('attrs', '')
% setdefault('required', False)
% setdefault('value', '')
<div class="field{{' invalid' if errors.get(name) else ''}}">
    <label for="{{name}}">{{label}}{{!' <span class="req">*</span>' if required else ''}}</label>
    <input id="{{name}}" name="{{name}}" type="{{type}}" value="{{'' if value is None else value}}" {{!attrs}}>
    % if hint:
    <small class="hint">{{hint}}</small>
    % end
    % if errors.get(name):
    <small class="error">{{errors[name]}}</small>
    % end
</div>
