import json, os, requests, re, time
from datetime import date

STATE = "state.json"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GH_API = "https://api.github.com"

RULES = "1. FREE ONLY: No paid APIs. 2. DEPS: requests,json,re only. 3. BUDGET: 2 LLM calls max. 4. GOAL: +1 new working API per run."

def load():
    if os.path.exists(STATE): return json.load(open(STATE))
    return {"version":1, "score":0, "apis":{}, "reflection":[], "best_prompt":"Extract name,url,description from GitHub repo JSON"}

def save(s): json.dump(s, open(STATE,'w'), indent=2)

def llm(prompt):
    key = os.getenv('GROQ_API_KEY')
    if not key: return ""
    try:
        r = requests.post(GROQ_URL, headers={"Authorization":f"Bearer {key}"},
            json={"model":"llama3-8b-8192","messages":[{"role":"user","content":prompt}]},timeout=15)
        return r.json()['choices'][0]['message']['content']
    except: return ""

def find_new_api():
    r = requests.get(f"{GH_API}/search/repositories?q=public+api+language:python&sort=stars&per_page=3", timeout=10)
    for repo in r.json().get('items',[]):
        name = repo['name'].lower().replace('-','_').replace('.','_')
        if name not in load()['apis']:
            return {"name":name, "url":repo['html_url'], "stars":repo['stargazers_count'],
                    "api_url":repo['html_url'].replace('github.com','api.github.com/repos')}
    return None

def write_harness(api):
    code = f'''
def {api['name']}():
    """Free harness for {api['url']} Stars:{api['stars']}"""
    try:
        r = requests.get("{api['api_url']}", timeout=10)
        return r.json() if r.status_code==200 else None
    except: return None
'''
    return code

def test_harness(code, name):
    try:
        compile(code, '<string>', 'exec')
        local = {}
        exec(code, {"requests":requests}, local)
        result = local[name]()
        return result is not None
    except: return False

def evolve():
    s = load()
    print(f"v{s['version']} | Score:{s['score']} | APIs:{len(s['apis'])}")
    api = find_new_api()
    if not api: return "No new APIs found today."
    code = write_harness(api)
    works = test_harness(code, api['name'])
    if works:
        s['apis'][api['name']] = {"code":code, "url":api['url'], "stars":api['stars']}
        s['score'] += api['stars']
        s['version'] += 1
        msg = f"LEARNED: {api['name']} | Score:{s['score']}"
    else:
        msg = f"FAILED: {api['name']} harness didn't work"
    s['reflection'].append(f"{date.today()} | {msg}")
    s['reflection'] = s['reflection'][-10:]
    save(s)
    with open("reflection.md","w") as f:
        f.write("# API-Forger Log\n\n"+"\n".join(s['reflection'])+f"\n\nAPIs learned: {list(s['apis'].keys())}")
    return msg

if __name__ == "__main__":
    print(evolve())
