import json,os,urllib.parse,urllib.request

def _web_search(p):
    q=p.get('query',''); lim=int(p.get('limit',10))
    if not q: return {'success':False,'error':'No query'}
    try:
        url='https://html.duckduckgo.com/html/?q='+urllib.parse.quote(q)
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req,timeout=15) as r: html=r.read().decode('utf-8',errors='replace')
        parts=html.split('result__a'); results=[]
        for part in parts[1:lim+1]:
            title=part.split('>')[1].split('<')[0] if '>' in part else ''
            results.append({'title':title.strip(),'url':'','snippet':''})
        return {'success':True,'query':q,'results':results,'count':len(results),'engine':'duckduckgo'}
    except Exception as e: return {'success':False,'error':str(e),'query':q}

def _mcp_call(p):
    srv=p.get('server_url',os.environ.get('MCP_SERVER_URL','http://localhost:3000'))
    tool=p.get('tool',''); args=p.get('args',{})
    if not tool: return {'success':False,'error':'No tool'}
    payload=json.dumps({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':tool,'arguments':args}}).encode()
    try:
        req=urllib.request.Request(srv,data=payload,headers={'Content-Type':'application/json'},method='POST')
        with urllib.request.urlopen(req,timeout=15) as r: resp=json.loads(r.read())
        return {'success':True,'tool':tool,'result':resp.get('result',resp)}
    except Exception as e: return {'success':False,'error':str(e),'tool':tool}

def _list_mcp_resources(p):
    srv=p.get('server_url',os.environ.get('MCP_SERVER_URL','http://localhost:3000'))
    payload=json.dumps({'jsonrpc':'2.0','id':1,'method':'resources/list','params':{}}).encode()
    try:
        req=urllib.request.Request(srv,data=payload,headers={'Content-Type':'application/json'},method='POST')
        with urllib.request.urlopen(req,timeout=15) as r: resp=json.loads(r.read())
        res=resp.get('result',{}).get('resources',[])
        return {'success':True,'resources':res,'count':len(res)}
    except Exception as e: return {'success':False,'error':str(e)}

def _mcp_auth(p):
    action=p.get('action','set'); token=p.get('token',os.environ.get('MCP_AUTH_TOKEN',''))
    if action=='set':
        if not token: return {'success':False,'error':'No token'}
        os.environ['MCP_AUTH_TOKEN']=token; return {'success':True,'action':'set'}
    elif action=='clear': os.environ.pop('MCP_AUTH_TOKEN',None); return {'success':True,'action':'clear'}
    return {'success':False,'error':f'Unknown action: {action}'}

def _read_mcp_resource(p):
    srv=p.get('server_url',os.environ.get('MCP_SERVER_URL','http://localhost:3000'))
    uri=p.get('uri',''); token=os.environ.get('MCP_AUTH_TOKEN','')
    if not uri: return {'success':False,'error':'No URI'}
    payload=json.dumps({'jsonrpc':'2.0','id':1,'method':'resources/read','params':{'uri':uri}}).encode()
    try:
        h={'Content-Type':'application/json'}
        if token: h['Authorization']='Bearer '+token
        req=urllib.request.Request(srv,data=payload,headers=h,method='POST')
        with urllib.request.urlopen(req,timeout=15) as r: resp=json.loads(r.read())
        c=resp.get('result',{}).get('contents',[])
        return {'success':True,'uri':uri,'contents':c,'count':len(c)}
    except Exception as e: return {'success':False,'error':str(e),'uri':uri}
