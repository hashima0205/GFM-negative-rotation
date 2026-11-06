"""Small TOML writer for identity records (stdlib tomllib reads them)."""
import json,math
def dumps(data):
    lines=[]
    def scalar(value):
        if isinstance(value,dict):return '{'+', '.join(json.dumps(str(k),ensure_ascii=False)+' = '+scalar(v) for k,v in value.items())+'}'
        if isinstance(value,(list,tuple)):return '['+', '.join(scalar(v) for v in value)+']'
        if isinstance(value,float) and not math.isfinite(value):return str(value).lower()
        return json.dumps(value,ensure_ascii=False)
    def table(obj,path):
        if path:lines.append('['+'.'.join(json.dumps(k,ensure_ascii=False) for k in path)+']')
        for key,value in obj.items():
            if not isinstance(value,dict):lines.append(json.dumps(str(key),ensure_ascii=False)+' = '+scalar(value))
        lines.append('')
        for key,value in obj.items():
            if isinstance(value,dict):table(value,[*path,str(key)])
    table(data,[]);return '\n'.join(lines).rstrip()+'\n'
