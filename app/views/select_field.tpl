% setdefault('hint', '')
% setdefault('required', False)
% setdefault('blank', '')
% setdefault('value', '')
<div class="field{{' invalid' if errors.get(name) else ''}}">
    <label for="{{name}}">{{label}}{{!' <span class="req">*</span>' if required else ''}}</label>
    <select id="{{name}}" name="{{name}}">
        % if blank:
        <option value="">{{blank}}</option>
        % end
        % for option_value, option_label in options:
        <option value="{{option_value}}"{{!' selected' if str(option_value) == str(value) else ''}}>{{option_label}}</option>
        % end
    </select>
    % if hint:
    <small class="hint">{{hint}}</small>
    % end
    % if errors.get(name):
    <small class="error">{{errors[name]}}</small>
    % end
</div>
