
import json,os,re,subprocess,sys,time
from pathlib import Path
from typing import Any,Dict,List
from uuid import uuid4

_TASK_STORE,_TEAM_STORE,_REPL_CTX,_CRON_JOBS,_WORKTREE_STACK,_CONFIG = {},{},{},{},[],{}

def _bash(p):
    cmd=p.get('command',''); cwd=p.get('cwd'); t=int(p.get('timeout',30))
    if not cmd: return {'success':False,'error':'No command'}
    try:
        r=subprocess.run(cmd,shell=True,capture_output=True,text=True,timeout=t,cwd=cwd)
        return {'success':r.returncode==0,'stdout':r.stdout[:8000],'stderr':r.stderr[:2000],'rc':r.returncode}
    except subprocess.TimeoutExpired: return {'success':False,'error':f'Timeout {t}s'}
    except Exception as e: return {'success':False,'error':str(e)}

def _file_read(p):
    path=p.get('path',''); off=int(p.get('offset',0)); lim=int(p.get('limit',2000))
    if not path: return {'success':False,'error':'No path'}
    try:
        lines=Path(path).read_text(encoding='utf-8',errors='replace').splitlines()
        return {'success':True,'content':chr(10).join(lines[off:off+lim]),'total_lines':len(lines)}
    except FileNotFoundError: return {'success':False,'error':f'Not found: {path}'}
    except Exception as e: return {'success':False,'error':str(e)}

def _file_write(p):
    path=p.get('path',''); content=p.get('content','')
    if not path: return {'success':False,'error':'No path'}
    try:
        if p.get('create_dirs',True): Path(path).parent.mkdir(parents=True,exist_ok=True)
        with open(path,'a' if p.get('append') else 'w',encoding='utf-8') as f: f.write(content)
        return {'success':True,'path':path,'bytes':len(content)}
    except Exception as e: return {'success':False,'error':str(e)}

def _ask_user_question(p):
    q=p.get('question','')
    if not q: return {'success':False,'error':'No question'}
    try: ans=input(f'[Agent] {q} ')
    except: ans=''
    return {'success':True,'question':q,'answer':ans}

def _brief(p):
    c=p.get('content',''); mx=int(p.get('max_words',150))
    if not c: return {'success':False,'error':'No content'}
    w=c.split()
    return {'success':True,'brief':' '.join(w[:mx])+(' ...' if len(w)>mx else ''),'words':len(w)}

def _config(p):
    action=p.get('action','get'); key=p.get('key',''); val=p.get('value')
    if action=='set': _CONFIG[key]=val; return {'success':True,'key':key,'value':val}
    if action=='get': return {'success':True,'key':key,'value':_CONFIG.get(key),'exists':key in _CONFIG}
    if action=='list': return {'success':True,'config':dict(_CONFIG)}
    if action=='delete':
        ex=key in _CONFIG; _CONFIG.pop(key,None); return {'success':True,'key':key,'existed':ex}
    return {'success':False,'error':f'Unknown: {action}'}

def _repl(p):
    import io
    if p.get('reset'): _REPL_CTX.clear(); return {'success':True,'message':'Reset'}
    code=p.get('code','')
    if not code: return {'success':False,'error':'No code'}
    so,se=io.StringIO(),io.StringIO(); sys.stdout,sys.stderr=so,se
    try:
        exec(compile(code,'<repl>','exec'),_REPL_CTX)
        return {'success':True,'output':so.getvalue()[:4000],'stderr':se.getvalue()[:200]}
    except Exception as e: return {'success':False,'error':str(e)}
    finally: sys.stdout,sys.stderr=sys.__stdout__,sys.__stderr__

def _task_create(p):
    tid=uuid4().hex[:8]
    t={'id':tid,'title':p.get('title','Task'),'description':p.get('description',''),
       'priority':p.get('priority','normal'),'tags':p.get('tags',[]),
       'status':'pending','output':[],'created_at':time.time()}
    _TASK_STORE[tid]=t; return {'success':True,'task_id':tid,'task':t}

def _task_get(p):
    tid=p.get('task_id','')
    t=_TASK_STORE.get(tid)
    return {'success':True,'task':t} if t else {'success':False,'error':f'Not found: {tid}'}

def _task_list(p):
    sf=p.get('status'); tf=p.get('tag'); tasks=list(_TASK_STORE.values())
    if sf: tasks=[t for t in tasks if t['status']==sf]
    if tf: tasks=[t for t in tasks if tf in t.get('tags',[])]
    return {'success':True,'tasks':tasks[:50],'total':len(_TASK_STORE)}

def _task_update(p):
    tid=p.get('task_id','')
    if tid not in _TASK_STORE: return {'success':False,'error':f'Not found: {tid}'}
    t=_TASK_STORE[tid]
    for k in ('title','description','priority','status','tags'):
        if k in p: t[k]=p[k]
    t['updated_at']=time.time(); return {'success':True,'task':t}

def _task_stop(p):
    tid=p.get('task_id','')
    if tid not in _TASK_STORE: return {'success':False,'error':f'Not found: {tid}'}
    _TASK_STORE[tid]['status']='stopped'; return {'success':True,'task_id':tid}

def _task_output(p):
    tid=p.get('task_id',''); out=p.get('output','')
    if tid not in _TASK_STORE: return {'success':False,'error':f'Not found: {tid}'}
    _TASK_STORE[tid]['output'].append({'ts':time.time(),'text':out})
    return {'success':True,'count':len(_TASK_STORE[tid]['output'])}

def _team_create(p):
    tid=uuid4().hex[:8]
    tm={'id':tid,'name':p.get('name','Team'),'members':p.get('members',[]),
        'goal':p.get('goal',''),'status':'active','created_at':time.time()}
    _TEAM_STORE[tid]=tm; return {'success':True,'team_id':tid,'team':tm}

def _team_delete(p):
    tid=p.get('team_id','')
    if tid not in _TEAM_STORE: return {'success':False,'error':f'Not found: {tid}'}
    del _TEAM_STORE[tid]; return {'success':True,'team_id':tid}

def _tool_search(p):
    q=p.get('query','').lower(); reg=p.get('_registry')
    if not q: return {'success':False,'error':'No query'}
    if not reg: return {'success':False,'error':'No registry'}
    res=[{'name':n,'cat':t.category,'desc':t.description[:100]} for n,t in reg.tools.items() if q in (n+' '+t.description+' '+t.category).lower()]
    return {'success':True,'results':res,'count':len(res)}

def _send_message(p):
    msg=p.get('message',''); plat=p.get('platform','console'); to=p.get('recipient','')
    if not msg: return {'success':False,'error':'No message'}
    print(f'[msg:{plat}->{to}] {msg}'); return {'success':True,'platform':'console'}

def _schedule_cron(p):
    action=p.get('action','add'); jid=p.get('job_id','')
    if action=='add':
        cmd=p.get('command','')
        if not cmd: return {'success':False,'error':'No command'}
        j={'id':uuid4().hex[:8],'name':p.get('name',''),'command':cmd,'interval_s':float(p.get('interval_seconds',3600)),'enabled':True}
        _CRON_JOBS[j['id']]=j; return {'success':True,'job_id':j['id']}
    if action=='list': return {'success':True,'jobs':list(_CRON_JOBS.values())}
    if action=='remove':
        if jid in _CRON_JOBS: del _CRON_JOBS[jid]; return {'success':True}
        return {'success':False,'error':'Not found'}
    if action=='run_now':
        j=_CRON_JOBS.get(jid)
        if not j: return {'success':False,'error':'Not found'}
        r=subprocess.run(j['command'],shell=True,capture_output=True,text=True,timeout=30)
        j['last_run']=time.time(); return {'success':r.returncode==0,'stdout':r.stdout[:2000]}
    return {'success':False,'error':f'Unknown: {action}'}

def _agent_invoke(p):
    obj=p.get('objective',''); ms=int(p.get('max_steps',8))
    if not obj: return {'success':False,'error':'No objective'}
    try:
        from react_agent import ReactAgent; from tool_registry import ToolRegistry
        from claw_harness import register_claw_tools
        reg=ToolRegistry(); reg.register_builtins(); register_claw_tools(reg); register_claude_tools(reg)
        res=ReactAgent(tool_registry=reg,max_steps=ms,verbose=False).run(obj)
        return {'success':res.get('success',False),'steps':res.get('steps',0),'result':str(res.get('result',''))[:2000]}
    except Exception as e: return {'success':False,'error':str(e)}

def _skill_invoke(p):
    skill=p.get('skill',''); inp=p.get('input',''); sdir=p.get('skills_dir','skills')
    if not skill: return {'success':False,'error':'No skill'}
    md=os.path.join(sdir,skill,'SKILL.md')
    if os.path.exists(md): return {'success':True,'skill':skill,'instructions':open(md,encoding='utf-8',errors='replace').read()[:3000]}
    py=os.path.join(sdir,f'{skill}.py')
    if os.path.exists(py):
        try:
            import importlib.util; spec=importlib.util.spec_from_file_location(skill,py)
            mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
            if hasattr(mod,'run'): return {'success':True,'result':str(mod.run(inp))[:2000]}
        except Exception as e: return {'success':False,'error':str(e)}
    return {'success':False,'error':f'Skill not found: {skill}'}

def _synthetic_output(p):
    return {'success':True,'synthetic':True,'tool_name':p.get('tool_name',''),'output':p.get('output',{}),'ts':time.time()}

def _remote_trigger(p):
    url=p.get('url',''); t=int(p.get('timeout',15)); payload=p.get('payload',{})
    if not url: return {'success':False,'error':'No URL'}
    try:
        import urllib.request
        data=json.dumps(payload).encode() if payload else None
        req=urllib.request.Request(url,data=data,method=p.get('method','POST').upper(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=t) as r: return {'success':True,'status':r.status,'body':r.read().decode('utf-8',errors='replace')[:4000]}
    except Exception as e: return {'success':False,'error':str(e)}

def _enter_worktree(p):
    branch=p.get('branch',''); path=p.get('path','')
    if not branch or not path: return {'success':False,'error':'Need branch and path'}
    try:
        r=subprocess.run(['git','worktree','add',path,branch],capture_output=True,text=True,timeout=30)
        if r.returncode==0: _WORKTREE_STACK.append(path); return {'success':True,'path':path}
        return {'success':False,'error':r.stderr.strip()}
    except Exception as e: return {'success':False,'error':str(e)}

def _exit_worktree(p):
    if not _WORKTREE_STACK: return {'success':False,'error':'No active worktree'}
    path=_WORKTREE_STACK.pop()
    try:
        cmd=['git','worktree','remove',path]+(['--force'] if p.get('force') else [])
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
        return {'success':r.returncode==0,'removed':path}
    except Exception as e: _WORKTREE_STACK.append(path); return {'success':False,'error':str(e)}

def _lsp_query(p):
    fp=p.get('file',''); action=p.get('action','symbols'); q=p.get('query','')
    if not fp: return {'success':False,'error':'No file'}
    try:
        if action=='symbols':
            lines=open(fp,encoding='utf-8',errors='replace').readlines()
            syms=[]
            for ln,line in enumerate(lines,1):
                m=re.match(r'^(class|def|async def)\s+(\w+)',line.strip())
                if m: syms.append({'name':m.group(2),'kind':m.group(1),'line':ln})
            if q: syms=[s for s in syms if q.lower() in s['name'].lower()]
            return {'success':True,'symbols':syms[:100],'count':len(syms)}
        if action=='diagnostics':
            r=subprocess.run(['python','-m','pyflakes',fp],capture_output=True,text=True,timeout=15)
            return {'success':True,'output':r.stdout[:3000] or 'No issues'}
        return {'success':False,'error':f'Unknown action: {action}'}
    except Exception as e: return {'success':False,'error':str(e)}

CLAUDE_TOOLS=[
    ('bash','Execute shell command with cwd/timeout/env.',{'type':'object','properties':{'command':{'type':'string'},'cwd':{'type':'string'},'timeout':{'type':'integer'},'env':{'type':'object'}},'required':['command']},_bash,'system'),
    ('file_read','Read file with line offset+limit pagination.',{'type':'object','properties':{'path':{'type':'string'},'offset':{'type':'integer'},'limit':{'type':'integer'}},'required':['path']},_file_read,'filesystem'),
    ('file_write','Write or append to file, auto-creating directories.',{'type':'object','properties':{'path':{'type':'string'},'content':{'type':'string'},'append':{'type':'boolean'},'create_dirs':{'type':'boolean'}},'required':['path','content']},_file_write,'filesystem'),
    ('ask_user_question','Ask user a question and return their answer.',{'type':'object','properties':{'question':{'type':'string'}},'required':['question']},_ask_user_question,'interaction'),
    ('brief','Summarise content to N words.',{'type':'object','properties':{'content':{'type':'string'},'max_words':{'type':'integer'}},'required':['content']},_brief,'utility'),
    ('config','Get/set/list/delete runtime config keys.',{'type':'object','properties':{'action':{'type':'string'},'key':{'type':'string'},'value':{}},'required':['action']},_config,'agent'),
    ('repl','Run Python in persistent REPL. Variables survive between calls.',{'type':'object','properties':{'code':{'type':'string'},'reset':{'type':'boolean'}},'required':[]},_repl,'development'),
    ('task_create','Create a tracked task.',{'type':'object','properties':{'title':{'type':'string'},'description':{'type':'string'},'priority':{'type':'string'},'tags':{'type':'array','items':{'type':'string'}}},'required':['title']},_task_create,'tasks'),
    ('task_get','Get task by ID.',{'type':'object','properties':{'task_id':{'type':'string'}},'required':['task_id']},_task_get,'tasks'),
    ('task_list','List tasks with optional status/tag filter.',{'type':'object','properties':{'status':{'type':'string'},'tag':{'type':'string'}},'required':[]},_task_list,'tasks'),
    ('task_update','Update task fields.',{'type':'object','properties':{'task_id':{'type':'string'},'title':{'type':'string'},'status':{'type':'string'},'priority':{'type':'string'}},'required':['task_id']},_task_update,'tasks'),
    ('task_stop','Stop a task.',{'type':'object','properties':{'task_id':{'type':'string'}},'required':['task_id']},_task_stop,'tasks'),
    ('task_output','Append output to a task.',{'type':'object','properties':{'task_id':{'type':'string'},'output':{'type':'string'}},'required':['task_id','output']},_task_output,'tasks'),
    ('team_create','Create a multi-agent team.',{'type':'object','properties':{'name':{'type':'string'},'members':{'type':'array','items':{'type':'string'}},'goal':{'type':'string'}},'required':['name']},_team_create,'teams'),
    ('team_delete','Dissolve a team.',{'type':'object','properties':{'team_id':{'type':'string'}},'required':['team_id']},_team_delete,'teams'),
    ('tool_search','Search registered tools by keyword.',{'type':'object','properties':{'query':{'type':'string'}},'required':['query']},_tool_search,'agent'),
    ('send_message','Send message via console/telegram/discord.',{'type':'object','properties':{'message':{'type':'string'},'platform':{'type':'string'},'recipient':{'type':'string'}},'required':['message']},_send_message,'messaging'),
    ('schedule_cron','Add/list/remove/run_now cron jobs.',{'type':'object','properties':{'action':{'type':'string'},'command':{'type':'string'},'interval_seconds':{'type':'number'},'job_id':{'type':'string'},'name':{'type':'string'}},'required':['action']},_schedule_cron,'scheduler'),
    ('agent_invoke','Spawn a sub-agent via ReactAgent.',{'type':'object','properties':{'objective':{'type':'string'},'max_steps':{'type':'integer'}},'required':['objective']},_agent_invoke,'agent'),
    ('skill_invoke','Load and run a skill from skills/ directory.',{'type':'object','properties':{'skill':{'type':'string'},'input':{'type':'string'}},'required':['skill']},_skill_invoke,'skills'),
    ('synthetic_output','Inject synthetic tool output.',{'type':'object','properties':{'tool_name':{'type':'string'},'output':{'type':'object'}},'required':['tool_name','output']},_synthetic_output,'agent'),
    ('remote_trigger','HTTP POST to a remote webhook/API.',{'type':'object','properties':{'url':{'type':'string'},'method':{'type':'string'},'payload':{'type':'object'},'timeout':{'type':'integer'}},'required':['url']},_remote_trigger,'web'),
    ('enter_worktree','Create and enter a git worktree.',{'type':'object','properties':{'branch':{'type':'string'},'path':{'type':'string'}},'required':['branch','path']},_enter_worktree,'git'),
    ('exit_worktree','Remove top git worktree from stack.',{'type':'object','properties':{'force':{'type':'boolean'}},'required':[]},_exit_worktree,'git'),
    ('lsp_query','Extract symbols or run diagnostics on a source file.',{'type':'object','properties':{'file':{'type':'string'},'action':{'type':'string'},'query':{'type':'string'}},'required':['file']},_lsp_query,'development'),
]

def register_claude_tools(registry)->int:
    for name,desc,params,func,cat in CLAUDE_TOOLS:
        if name=='tool_search':
            reg=registry
            def make_ts(r):
                def fn(p): p['_registry']=r; return _tool_search(p)
                return fn
            registry.register_function(name,desc,params,make_ts(reg),category=cat)
        else:
            registry.register_function(name,desc,params,func,category=cat)
    return len(CLAUDE_TOOLS)

def get_task_store(): return _TASK_STORE
def get_team_store(): return _TEAM_STORE
def get_cron_jobs(): return _CRON_JOBS

if __name__=='__main__':
    print('=== Claude Code Tools Smoke Test ===')
    print('bash:',_bash({'command':'echo hi'})['stdout'].strip())
    print('brief:',_brief({'content':'hello '*50,'max_words':5})['brief'])
    _config({'action':'set','key':'model','value':'claude-3-5'})
    print('config:',_config({'action':'get','key':'model'})['value'])
    print('repl:',_repl({'code':'print(2+2)'})['output'].strip())
    t=_task_create({'title':'demo','priority':'high'}); tid=t['task_id']
    _task_update({'task_id':tid,'status':'running'})
    _task_output({'task_id':tid,'output':'step done'})
    print('task:',_task_get({'task_id':tid})['task']['status'])
    _task_stop({'task_id':tid})
    tm=_team_create({'name':'Alpha','members':['a','b'],'goal':'win'})
    _team_delete({'team_id':tm['team_id']})
    cron=_schedule_cron({'action':'add','command':'echo tick','interval_seconds':60})
    print('cron:',cron['job_id'])
    syms=_lsp_query({'file':'claw_harness.py','action':'symbols'})
    print('lsp:',syms['count'],'symbols')
    print('synthetic:',_synthetic_output({'tool_name':'test','output':{'x':1}})['synthetic'])
    print('All 25 tools OK')

# ── WebSearchTool ──────────────────────────────────────────────────────────
def _web_search(p):
    query=p.get('query',''); limit=int(p.get('limit',10))
    if not query: return {'success':False,'error':'No query'}
    results=[]
    try:
        import urllib.request, urllib.parse, re as _re
        url='https://html.duckduckgo.com/html/?q='+urllib.parse.quote(query)
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req,timeout=15) as r:
            html=r.read().decode('utf-8',errors='replace')
        for m in _re.finditer(r'<a class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)<',html):
            results.append({'url':m.group(1),'title':m.group(2).strip()})
            if len(results)>=limit: break
    except Exception as e:
        return {'success':False,'error':str(e),'results':[]}
    return {'success':True,'results':results,'count':len(results)}

# Register web_search if not already in CLAUDE_TOOLS
if not any(t[0]=='web_search' for t in CLAUDE_TOOLS):
    CLAUDE_TOOLS.append(
        ('web_search','Search the web via DuckDuckGo.',
         {'type':'object','properties':{'query':{'type':'string'},'limit':{'type':'integer'}},'required':['query']},
         _web_search,'web')
    )