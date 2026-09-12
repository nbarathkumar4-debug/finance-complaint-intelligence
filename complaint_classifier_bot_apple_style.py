import streamlit as st
from google import genai
from datetime import datetime
import pandas as pd
import csv, io, os, html
import json
import re
import urllib.request
import urllib.error

def gemini_generate(prompt):
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        raise RuntimeError('GEMINI_API_KEY is not configured in this Windows session.')
    url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key=' + api_key
    payload = json.dumps({'contents': [{'parts': [{'text': prompt}]}]}).encode('utf-8')
    request = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode('utf-8'))
        candidates = data.get('candidates', [])
        if not candidates:
            raise RuntimeError('Gemini returned no response candidates.')
        parts = candidates[0].get('content', {}).get('parts', [])
        text_parts = [part.get('text', '') for part in parts if part.get('text')]
        if not text_parts:
            raise RuntimeError('Gemini returned an empty response.')
        return ''.join(text_parts)
    except urllib.error.HTTPError as e:
        detail = e.read().decode('utf-8', errors='replace')
        raise RuntimeError(f'Gemini API error {e.code}: {detail[:500]}') from e
    except urllib.error.URLError as e:
        raise RuntimeError(f'Unable to reach Gemini API: {e.reason}') from e


st.set_page_config(page_title='Finance Complaint Intelligence', page_icon='◆', layout='wide', initial_sidebar_state='collapsed')
DB='complaints_database.csv'
COLS=['timestamp','complaint','category','sentiment','priority','key_issue','business_action']

st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html,body,[class*="css"]{font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}.stApp{background:radial-gradient(circle at 82% 4%,rgba(80,145,255,.14),transparent 28%),radial-gradient(circle at 8% 35%,rgba(120,100,255,.07),transparent 25%),#f8fafc;color:#14213d}.block-container{max-width:1240px;padding-top:1.2rem}#MainMenu,footer{visibility:hidden}header[data-testid="stHeader"]{background:transparent}
.top{display:flex;justify-content:space-between;align-items:center;padding:8px 2px 22px;animation:down .6s ease both}.brand{display:flex;align-items:center;gap:10px;font-weight:700;color:#14213d}.mark{width:32px;height:32px;border-radius:10px;display:flex;align-items:center;justify-content:center;color:white;background:linear-gradient(135deg,#153e75,#4d8dff);box-shadow:0 8px 24px #2e67cc40}.status{font-size:12px;color:#64748b;border:1px solid #e2e8f0;background:#ffffffbb;padding:7px 12px;border-radius:99px}.dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#22c55e;margin-right:6px}
.hero{position:relative;overflow:hidden;min-height:405px;border-radius:34px;padding:68px 65px;margin-bottom:65px;background:radial-gradient(circle at 82% 40%,rgba(100,166,255,.32),transparent 30%),radial-gradient(circle at 95% 8%,rgba(135,107,255,.2),transparent 25%),linear-gradient(135deg,#fff,#f7faff 55%,#eef5ff);border:1px solid #cbd5e1aa;box-shadow:0 25px 70px #0f234614}.eyebrow{color:#4a73bf;font-size:11px;font-weight:700;letter-spacing:1.7px;text-transform:uppercase}.hero h1{max-width:650px;color:#102344;font-size:clamp(45px,5vw,72px);line-height:.98;font-weight:800;letter-spacing:-4px;margin:14px 0 0;animation:up .75s ease .1s both}.hero p{max-width:560px;color:#42526b;font-size:19px;line-height:1.55;margin-top:24px;animation:up .75s ease .18s both}.pill{display:inline-block;margin-top:24px;padding:10px 16px;border-radius:99px;color:white;background:#102b50;font-size:12px;font-weight:600;animation:up .75s ease .25s both}.flow{position:absolute;right:5%;top:68px;width:45%;padding:23px;border-radius:24px;background:#ffffffb8;border:1px solid #fff;box-shadow:0 25px 60px #244f8c24;backdrop-filter:blur(18px);animation:float 1s ease .2s both}.flowtitle{font-size:10px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:#6b7b91;margin-bottom:15px}.steps{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.step{min-height:82px;border-radius:16px;background:#ffffffe8;border:1px solid #e5edf8;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center}.step b{font-size:10px;color:#163258}.icon{font-size:20px;margin-bottom:6px}.quote{margin-top:13px;padding:15px;border-radius:16px;background:#f7faffdd;border:1px solid #e2eaf5;color:#3d4d63;font-size:12px;line-height:1.5}
.heading{color:#102344;font-size:38px;line-height:1.05;font-weight:800;letter-spacing:-1.8px;margin:8px 0 10px}.copy{color:#66758b;font-size:14px;line-height:1.6;margin-bottom:24px}.kpi{min-height:140px;padding:22px;border-radius:22px;background:#ffffffe0;border:1px solid #e7edf5;box-shadow:0 12px 34px #1f37580e;transition:.25s}.kpi:hover{transform:translateY(-4px);box-shadow:0 18px 40px #1f37581a}.klabel{color:#718096;font-size:11px;font-weight:600}.kvalue{color:#102344;font-size:34px;font-weight:800;letter-spacing:-1.4px;margin-top:10px}.knote{color:#8a98aa;font-size:10px;margin-top:9px}.panel{background:#ffffffe0;border:1px solid #e6edf5;border-radius:24px;padding:25px;box-shadow:0 12px 38px #1f37580e;margin-bottom:16px}.ptitle{color:#172c4b;font-size:16px;font-weight:700}.psub{color:#8a98aa;font-size:11px;margin:4px 0 14px}.ai{padding:28px;border-radius:27px;background:radial-gradient(circle at 100% 0,#4b87eb1f,transparent 32%),#fff;border:1px solid #e2eaf4;box-shadow:0 18px 55px #1d3e6814;animation:up .6s ease both}.badge{display:inline-block;color:#315fae;background:#edf4ff;padding:7px 11px;border-radius:99px;font-size:10px;font-weight:700;letter-spacing:.8px;text-transform:uppercase}.rbox{height:100%;padding:18px;border-radius:18px;background:#f8fafd;border:1px solid #e8eef6}.rlab{color:#7a8799;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:7px}.rval{color:#162b4b;font-size:15px;font-weight:700;line-height:1.45}.action{padding:20px;margin-top:14px;border-radius:19px;background:linear-gradient(135deg,#102b50,#1f4d88);color:#fff;box-shadow:0 16px 36px #102b502b}.action small{display:block;opacity:.7;font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px}.action div{font-size:14px;line-height:1.55}.risk{margin:55px 0;padding:55px;border-radius:32px;color:white;overflow:hidden;background:radial-gradient(circle at 80% 20%,#5291ff3d,transparent 30%),radial-gradient(circle at 10% 100%,#4d68ff2e,transparent 28%),#081b36;box-shadow:0 30px 80px #081b3630}.risk h2{font-size:44px;line-height:1.02;font-weight:800;letter-spacing:-2px;margin:8px 0 12px}.risk p{color:#a9b9cf;max-width:440px;line-height:1.65;font-size:14px}.risknum{width:180px;height:180px;margin:5px auto;border-radius:50%;display:flex;flex-direction:column;justify-content:center;align-items:center;background:#ffffff09;border:1px solid #ffffff24;box-shadow:0 0 0 12px #5291ff0a,0 0 0 28px #5291ff06}.risknum strong{font-size:52px}.risknum span{color:#9fb0c7;font-size:11px}.mgmt{padding:30px;border-radius:27px;background:#fff;border:1px solid #e5ecf5;box-shadow:0 18px 55px #1f375812}
.stButton>button{border-radius:99px;min-height:43px;font-weight:650;border:1px solid #dbe5f0;transition:.22s}.stButton>button:hover{transform:translateY(-2px);box-shadow:0 10px 25px #1f37581a}button[kind="primary"]{background:#102b50!important;border-color:#102b50!important}.stTextArea textarea,.stTextInput input,.stMultiSelect div[data-baseweb="select"]{border-radius:17px!important;border-color:#dfe7f0!important}hr{border:none!important;border-top:1px solid #e7edf4!important;margin:32px 0!important}.footer{text-align:center;color:#8b98a9;font-size:11px;line-height:1.7;padding:30px 10px 5px}@keyframes up{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:none}}@keyframes down{from{opacity:0;transform:translateY(-10px)}to{opacity:1;transform:none}}@keyframes float{from{opacity:0;transform:translateY(22px) scale(.97)}to{opacity:1;transform:none}}@media(max-width:900px){.hero{padding:42px 28px;min-height:auto}.flow{position:relative;right:auto;top:auto;width:100%;margin-top:35px}.hero h1{font-size:48px;letter-spacing:-2.5px}.risk{padding:35px 25px}}
</style>''', unsafe_allow_html=True)

def load():
    if not os.path.exists(DB): return []
    try:
        df=pd.read_csv(DB)
        if df.empty:return []
        for c in COLS:
            if c not in df.columns: df[c]='Unknown'
        return df[COLS].to_dict('records')
    except Exception:return []

def save(): pd.DataFrame(st.session_state.analyzed_complaints,columns=COLS).to_csv(DB,index=False)

def csv_data(records):
    b=io.StringIO(); w=csv.DictWriter(b,fieldnames=COLS); w.writeheader(); w.writerows(records); return b.getvalue()

def management_summary(df):
    data=df[['category','sentiment','priority','key_issue']].to_string(index=False)
    prompt=f'''You are a senior management analyst at a financial services company. Analyze this customer complaint dataset:\n{data}\n\nPrepare a concise management-level summary with exactly these sections: Executive Summary: 3-4 sentences. Major Complaint Areas: most important categories/issues. Risk Assessment: operational, customer-service, security or reputational risks. Recommended Management Actions: 4-5 practical actions. Management Priority: single most important issue first. Use professional banking/business language. Do not invent statistics.'''
    try:return gemini_generate(prompt)
    except Exception as e:return f'Unable to generate management summary: {e}'

def report(df,summary):
    now=datetime.now().strftime('%d %B %Y, %I:%M %p'); total=len(df)
    neg=df.sentiment.astype(str).str.upper().eq('NEGATIVE').sum(); crit=df.priority.astype(str).str.upper().eq('CRITICAL').sum(); high=df.priority.astype(str).str.upper().eq('HIGH').sum()
    cats=''.join(f"<li>{html.escape(str(k))}: <strong>{v}</strong></li>" for k,v in df.category.value_counts().items())
    rows=''.join(f"<tr><td>{html.escape(str(r.timestamp))}</td><td>{html.escape(str(r.category))}</td><td>{html.escape(str(r.sentiment))}</td><td>{html.escape(str(r.priority))}</td><td>{html.escape(str(r.key_issue))}</td></tr>" for _,r in df.iterrows())
    return f'''<!doctype html><html><head><meta charset="utf-8"><title>Financial Complaint Management Report</title><style>body{{font-family:Arial;margin:40px;color:#172c4b;background:#f7f9fc}}.header{{background:linear-gradient(135deg,#102b50,#285a9d);color:white;padding:34px;border-radius:18px}}.kpis{{display:flex;gap:15px;margin-top:25px;flex-wrap:wrap}}.kpi{{background:white;border:1px solid #dde6f0;padding:18px;min-width:160px;border-radius:14px}}.kpi strong{{display:block;font-size:28px;margin-top:8px;color:#102b50}}.section{{margin-top:32px}}table{{width:100%;border-collapse:collapse;background:white}}th{{background:#102b50;color:white;padding:10px;text-align:left}}td{{border:1px solid #dce5ef;padding:9px}}.summary{{white-space:pre-wrap;background:white;border:1px solid #dde6f0;padding:22px;border-radius:14px;line-height:1.6}}</style></head><body><div class="header"><h1>Financial Complaint Management Report</h1><p>AI-Assisted Customer Complaint Intelligence System</p><p>Generated: {html.escape(now)}</p></div><div class="kpis"><div class="kpi">Total Complaints<strong>{total}</strong></div><div class="kpi">Negative Complaints<strong>{neg}</strong></div><div class="kpi">High Priority<strong>{high}</strong></div><div class="kpi">Critical<strong>{crit}</strong></div></div><div class="section"><h2>Complaint Categories</h2><ul>{cats}</ul></div><div class="section"><h2>AI Management Summary</h2><div class="summary">{html.escape(str(summary))}</div></div><div class="section"><h2>Complaint Records</h2><table><tr><th>Timestamp</th><th>Category</th><th>Sentiment</th><th>Priority</th><th>Key Issue</th></tr>{rows}</table></div></body></html>'''

def render_result(a):
    st.markdown('<div class="ai"><span class="badge">Gemini AI analysis complete</span><h2 style="color:#102344;margin:12px 0 18px">Complaint intelligence</h2></div>',unsafe_allow_html=True)
    x,y,z=st.columns(3)
    for col,label,key in [(x,'Category','category'),(y,'Sentiment','sentiment'),(z,'Priority','priority')]:
        with col: st.markdown(f'<div class="rbox"><div class="rlab">{label}</div><div class="rval">{html.escape(str(a[key]))}</div></div>',unsafe_allow_html=True)
    st.markdown(f'<div class="action"><small>Key issue</small><div>{html.escape(str(a["key_issue"]))}</div><small style="margin-top:18px">Recommended business action</small><div>{html.escape(str(a["business_action"]))}</div></div>',unsafe_allow_html=True)
    p=str(a['priority']).upper()
    if 'CRITICAL' in p: st.error('🚨 CRITICAL PRIORITY — Immediate management attention recommended.')
    elif 'HIGH' in p: st.warning('⚠️ HIGH PRIORITY — Prompt review recommended.')

if 'analyzed_complaints' not in st.session_state: st.session_state.analyzed_complaints=load()
if 'complaint_input' not in st.session_state: st.session_state.complaint_input=''
if 'management_summary' not in st.session_state: st.session_state.management_summary=''
if 'last_analysis' not in st.session_state: st.session_state.last_analysis=None
if 'batch_results' not in st.session_state: st.session_state.batch_results=[]

st.markdown(f'''<div class="top"><div class="brand"><div class="mark">◆</div>Finance Complaint Intelligence</div><div class="status"><span class="dot"></span>AI system active · {len(st.session_state.analyzed_complaints)} stored</div></div>''',unsafe_allow_html=True)
st.markdown('''<section class="hero"><div class="eyebrow">AI-POWERED COMPLAINT INTELLIGENCE</div><h1>Finance,<br>understood.</h1><p>Turn customer complaints into actionable intelligence. Detect risk, understand sentiment and help management make faster decisions.</p><div class="pill">✦ Powered by Gemini AI</div><div class="flow"><div class="flowtitle">From customer voice to business action</div><div class="steps"><div class="step"><div class="icon">◌</div><b>Complaint</b></div><div class="step"><div class="icon">✦</div><b>AI Analysis</b></div><div class="step"><div class="icon">◇</div><b>Risk</b></div><div class="step"><div class="icon">✓</div><b>Action</b></div></div><div class="quote">“My transfer has been pending for 3 days. The money left my account but hasn't arrived.”</div></div></section>''',unsafe_allow_html=True)

t1,t2,t3,t4,t5=st.tabs(['Overview','AI Analysis','Complaint History','Risk Monitoring','Management Reports'])

with t1:
    st.markdown('<div class="eyebrow">DASHBOARD</div><div class="heading">Know what your customers<br>are telling you.</div><div class="copy">A real-time management view of complaint volume, sentiment and operational risk.</div>',unsafe_allow_html=True)
    if st.session_state.analyzed_complaints:
        df=pd.DataFrame(st.session_state.analyzed_complaints); total=len(df); neg=df.sentiment.astype(str).str.upper().eq('NEGATIVE').sum(); high=df.priority.astype(str).str.upper().eq('HIGH').sum(); crit=df.priority.astype(str).str.upper().eq('CRITICAL').sum(); hc=high+crit; risk=hc/total*100 if total else 0
        for col,label,val,note in zip(st.columns(4),['TOTAL COMPLAINTS','NEGATIVE SENTIMENT','HIGH / CRITICAL','RISK EXPOSURE'],[f'{total:,}',f'{neg:,}',f'{hc:,}',f'{risk:.1f}%'],['Records in your intelligence database','Complaints requiring attention','Priority cases in the database','High + Critical share of complaints']):
            with col: st.markdown(f'<div class="kpi"><div class="klabel">{label}</div><div class="kvalue">{val}</div><div class="knote">{note}</div></div>',unsafe_allow_html=True)
        st.markdown('<br>',unsafe_allow_html=True)
        if crit: st.error(f'🚨 {crit} critical complaint(s) require immediate management review.')
        elif high: st.warning(f'⚠️ {high} high-priority complaint(s) require prompt attention.')
        else: st.success('✓ No High/Critical complaints are currently recorded.')
        st.divider(); a,b=st.columns(2)
        with a:
            st.markdown('<div class="panel"><div class="ptitle">Complaint categories</div><div class="psub">Where customer problems are concentrated</div></div>',unsafe_allow_html=True); st.bar_chart(df.category.value_counts())
        with b:
            st.markdown('<div class="panel"><div class="ptitle">Sentiment distribution</div><div class="psub">The emotional signal across complaints</div></div>',unsafe_allow_html=True); st.bar_chart(df.sentiment.value_counts())
        st.markdown('<div class="panel"><div class="ptitle">Priority distribution</div><div class="psub">Understand the urgency profile of the complaint base</div></div>',unsafe_allow_html=True); st.bar_chart(df.priority.value_counts()); st.divider()
        st.markdown('<div class="eyebrow">MANAGEMENT SIGNALS</div><div class="heading" style="font-size:30px">The patterns behind the numbers.</div>',unsafe_allow_html=True)
        vals=[df.category.value_counts().index[0],df.sentiment.value_counts().index[0],df.priority.value_counts().index[0]]
        labels=['Largest complaint area','Dominant sentiment','Most common priority']
        for col,label,val in zip(st.columns(3),labels,vals):
            with col: st.markdown(f'<div class="panel"><div class="ptitle">{label}</div><div class="heading" style="font-size:23px;margin-top:10px">{html.escape(str(val))}</div></div>',unsafe_allow_html=True)
    else:
        st.markdown('<div class="panel" style="padding:45px;text-align:center"><div class="eyebrow">READY WHEN YOU ARE</div><div class="heading" style="font-size:31px">Your complaint intelligence starts here.</div><div class="copy">Analyze your first customer complaint with Gemini AI and the dashboard will begin building automatically.</div></div>',unsafe_allow_html=True)

with t2:
    st.markdown('<div class="eyebrow">AI ANALYSIS</div><div class="heading">Listen to the customer.<br>Let AI find the signal.</div><div class="copy">Analyze one complaint or paste up to 30 complaints at once. Batch mode separates the complaints, classifies them together with Gemini AI, and stores every result as an individual record.</div>',unsafe_allow_html=True)

    mode=st.radio('Analysis mode',['Single complaint','Batch complaints'],horizontal=True)

    if mode=='Single complaint':
        complaint=st.text_area('Customer complaint',value=st.session_state.complaint_input,height=190,placeholder='Example: My transfer has been pending for 3 days. The money left my account but has not arrived. This is unacceptable!')
        st.markdown('<div class="ptitle" style="margin:12px 0">Try a sample</div>',unsafe_allow_html=True)
        s1,s2,s3=st.columns(3)
        samples=[('Technical issue',"The banking app crashed while I was making a payment. Now I don't know whether the payment went through."),('Billing issue','Why was I charged a service fee that I was never informed about? This is very disappointing.'),('Security issue','I received a transaction notification for a payment I never made. Someone may have accessed my account.')]
        for col,(label,text) in zip([s1,s2,s3],samples):
            with col:
                if st.button(label,use_container_width=True): st.session_state.complaint_input=text; st.rerun()
        st.markdown('<br>',unsafe_allow_html=True)
        go=st.button('Analyze complaint with Gemini AI  →',use_container_width=True,type='primary')
        if go:
            if not complaint.strip(): st.error('Please enter a customer complaint first.')
            else:
                st.session_state.complaint_input=complaint
                prompt=f'''Analyze this customer complaint from a financial services company.\n\nCOMPLAINT:\n"{complaint}"\n\nCategory: Choose ONE: Technical Issue, Billing/Charges, Customer Service, Security/Fraud, Payment/Transfer Issue, Process/Verification, Delivery/Timeline, Documentation, Pricing, Account Access.\nSentiment: Choose ONE: POSITIVE, NEGATIVE, NEUTRAL.\nPriority: Choose ONE: CRITICAL, HIGH, MEDIUM, LOW.\nKey Issue: Give a one-sentence summary.\nBusiness Action: Give a practical recommendation in 2-3 sentences.\n\nReturn ONLY:\nCategory: ...\nSentiment: ...\nPriority: ...\nKey Issue: ...\nBusiness Action: ...\nDo not add an introduction or conclusion.'''
                with st.spinner('Gemini AI is analyzing the complaint...'):
                    try:
                        text=gemini_generate(prompt); result={}
                        for line in text.strip().split('\n'):
                            if ':' in line:
                                k,v=line.split(':',1); result[k.strip().lower()]=v.strip()
                        a={'timestamp':datetime.now().strftime('%Y-%m-%d %H:%M:%S'),'complaint':complaint,'category':result.get('category','Unknown'),'sentiment':result.get('sentiment','Unknown'),'priority':result.get('priority','Unknown'),'key_issue':result.get('key issue','Unknown'),'business_action':result.get('business action','Unknown')}
                        st.session_state.analyzed_complaints.append(a); st.session_state.last_analysis=a; save(); st.success('Analysis completed successfully.')
                    except Exception as e: st.error(f'Error analyzing complaint: {e}'); st.info('Please make sure GEMINI_API_KEY is correctly configured.')
        if st.session_state.last_analysis: st.markdown('<br>',unsafe_allow_html=True); render_result(st.session_state.last_analysis)

    else:
        st.markdown('<div class="panel"><div class="ptitle">Batch analysis — up to 30 complaints</div><div class="psub">Best format: number each complaint (1. … 2. … 3. …) or separate complaints with a blank line.</div></div>',unsafe_allow_html=True)
        batch_text=st.text_area('Paste your complaints here',height=360,placeholder='1. My ATM transaction failed but money was deducted.\n\n2. I was charged a service fee I did not expect.\n\n3. My mobile banking app keeps crashing.\n\n...\n\n30. My account verification has been pending for a week.',key='batch_input')

        def split_batch_complaints(text):
            text=text.strip()
            if not text: return []
            numbered=re.split(r'(?m)(?=^\s*(?:complaint\s*)?\d+\s*[\).:\-])',text,flags=re.IGNORECASE)
            numbered=[re.sub(r'^\s*(?:complaint\s*)?\d+\s*[\).:\-]\s*','',x,flags=re.IGNORECASE).strip() for x in numbered if x.strip()]
            if len(numbered)>=2: return numbered
            paragraphs=[x.strip() for x in re.split(r'\n\s*\n+',text) if x.strip()]
            if len(paragraphs)>=2: return paragraphs
            lines=[x.strip() for x in text.splitlines() if x.strip()]
            return lines

        parsed=split_batch_complaints(batch_text)
        if batch_text.strip():
            if len(parsed)>30: st.warning(f'{len(parsed)} complaints detected. Only the first 30 will be processed.')
            elif len(parsed)<30: st.info(f'{len(parsed)} complaint(s) detected. You can continue adding complaints until you reach 30.')
            else: st.success('✓ Exactly 30 complaints detected and ready for batch analysis.')
            with st.expander('Preview detected complaints',expanded=False):
                for i,c in enumerate(parsed[:30],1): st.write(f'**{i}.** {c}')

        batch_go=st.button('Analyze all complaints with Gemini AI  →',use_container_width=True,type='primary',disabled=not bool(batch_text.strip()))
        if batch_go:
            complaints=parsed[:30]
            if not complaints:
                st.error('Please paste at least one complaint.')
            else:
                batch_prompt=f'''You are a senior financial-services customer complaint classification system.\n\nClassify EACH of the following {len(complaints)} customer complaints independently.\n\nCOMPLAINTS:\n{chr(10).join(f'{i}. {c}' for i,c in enumerate(complaints,1))}\n\nFor every complaint, return one JSON object with exactly these keys:\n"complaint_number", "category", "sentiment", "priority", "key_issue", "business_action"\n\nCategory must be ONE of: Technical Issue, Billing/Charges, Customer Service, Security/Fraud, Payment/Transfer Issue, Process/Verification, Delivery/Timeline, Documentation, Pricing, Account Access.\nSentiment must be ONE of: POSITIVE, NEGATIVE, NEUTRAL.\nPriority must be ONE of: CRITICAL, HIGH, MEDIUM, LOW.\nKey Issue must be a concise one-sentence summary.\nBusiness Action must be a practical recommendation in 2-3 sentences.\n\nReturn ONLY a valid JSON array containing exactly {len(complaints)} objects, in the same order as the complaints. Do not use markdown fences. Do not add an introduction or conclusion.'''
                with st.spinner(f'Gemini AI is analyzing {len(complaints)} complaints together...'):
                    try:
                        raw=gemini_generate(batch_prompt).strip()
                        raw=re.sub(r'^```(?:json)?\s*','',raw,flags=re.IGNORECASE)
                        raw=re.sub(r'\s*```$','',raw)
                        start_json=raw.find('['); end_json=raw.rfind(']')
                        if start_json==-1 or end_json==-1 or end_json<=start_json: raise ValueError('Gemini did not return a valid JSON array.')
                        results=json.loads(raw[start_json:end_json+1])
                        if not isinstance(results,list) or len(results)!=len(complaints):
                            raise ValueError(f'Gemini returned {len(results) if isinstance(results,list) else 0} results for {len(complaints)} complaints.')
                        new_records=[]
                        for complaint_item,res in zip(complaints,results):
                            if not isinstance(res,dict): raise ValueError('Gemini returned an invalid result object.')
                            a={'timestamp':datetime.now().strftime('%Y-%m-%d %H:%M:%S'),'complaint':complaint_item,'category':str(res.get('category','Unknown')),'sentiment':str(res.get('sentiment','Unknown')),'priority':str(res.get('priority','Unknown')),'key_issue':str(res.get('key_issue','Unknown')),'business_action':str(res.get('business_action','Unknown'))}
                            new_records.append(a)
                        st.session_state.analyzed_complaints.extend(new_records)
                        st.session_state.last_analysis=new_records[-1]
                        st.session_state.batch_results=new_records
                        save()
                        st.success(f'✓ Batch analysis completed — {len(new_records)} separate complaints were classified and saved.')
                    except Exception as e:
                        st.error(f'Batch analysis failed: {e}')
                        st.info('Try numbering each complaint 1–30 and make sure each complaint is clearly separated.')

        if st.session_state.get('batch_results'):
            st.markdown('<br>',unsafe_allow_html=True)
            st.markdown('<div class="eyebrow">BATCH RESULTS</div><div class="heading" style="font-size:30px">Complaints. Classified separately.</div>',unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(st.session_state.batch_results)[['complaint','category','sentiment','priority','key_issue','business_action']],use_container_width=True,hide_index=True)

with t3:
    st.markdown('<div class="eyebrow">HISTORY</div><div class="heading">Every complaint.<br>One intelligence layer.</div><div class="copy">Search, filter and review every complaint analyzed by the system.</div>',unsafe_allow_html=True)
    if st.session_state.analyzed_complaints:
        df=pd.DataFrame(st.session_state.analyzed_complaints); search=st.text_input('Search complaints',placeholder='Search complaint text, category, issue or action...'); f1,f2,f3=st.columns(3)
        cats=sorted(df.category.astype(str).unique()); sens=sorted(df.sentiment.astype(str).unique()); pris=sorted(df.priority.astype(str).unique())
        with f1: sc=st.multiselect('Category',cats)
        with f2: ss=st.multiselect('Sentiment',sens)
        with f3: sp=st.multiselect('Priority',pris)
        filt=df.copy()
        if search.strip():
            q=search.lower(); filt=filt[filt.apply(lambda r:q in ' '.join(map(str,r.values)).lower(),axis=1)]
        if sc:filt=filt[filt.category.isin(sc)]
        if ss:filt=filt[filt.sentiment.isin(ss)]
        if sp:filt=filt[filt.priority.isin(sp)]
        st.info(f'Showing {len(filt)} of {len(df)} complaint(s)')
        if not filt.empty:
            show=filt[['timestamp','category','sentiment','priority','complaint']].copy(); show.columns=['Time','Category','Sentiment','Priority','Complaint']; st.dataframe(show,use_container_width=True,hide_index=True); st.divider(); st.markdown('<div class="eyebrow">DETAIL VIEW</div><div class="heading" style="font-size:30px">Explore the records.</div>',unsafe_allow_html=True)
            for _,r in filt.iloc[::-1].iterrows():
                with st.expander(f"{str(r['complaint'])[:90]}... · {r['priority']}"):
                    x,y,z=st.columns(3)
                    with x:st.markdown(f"**Category**\n\n`{r['category']}`")
                    with y:st.markdown(f"**Sentiment**\n\n`{r['sentiment']}`")
                    with z:st.markdown(f"**Priority**\n\n`{r['priority']}`")
                    st.divider(); st.markdown(f"**Customer Complaint**\n\n{r['complaint']}\n\n**Key Issue**\n\n{r['key_issue']}\n\n**Business Action**\n\n{r['business_action']}")
        else:st.warning('No complaints match the selected filters.')
    else:st.info('No complaint history is available yet. Analyze your first complaint to begin.')

with t4:
    st.markdown('<div class="eyebrow">RISK MONITORING</div><div class="heading">Risk doesn\'t wait.</div><div class="copy">Identify critical customer issues before they become larger operational, security or reputational problems.</div>',unsafe_allow_html=True)
    if st.session_state.analyzed_complaints:
        df=pd.DataFrame(st.session_state.analyzed_complaints); crit=df[df.priority.astype(str).str.upper().eq('CRITICAL')]; high=df[df.priority.astype(str).str.upper().eq('HIGH')]; neg=df[df.sentiment.astype(str).str.upper().eq('NEGATIVE')]; hc=df[df.priority.astype(str).str.upper().isin(['HIGH','CRITICAL'])]; pct=len(hc)/len(df)*100 if len(df) else 0
        st.markdown(f'<section class="risk"><div class="eyebrow" style="color:#7faeff">OPERATIONAL RISK</div><h2>Stay ahead of<br>the signal.</h2><p>High and critical complaints are surfaced automatically so management can focus attention where it matters most.</p><div class="risknum"><strong>{len(crit)}</strong><span>Critical cases</span></div></section>',unsafe_allow_html=True)
        for col,label,val in zip(st.columns(4),['Critical','High','Negative','Risk Exposure'],[len(crit),len(high),len(neg),f'{pct:.1f}%']):
            with col:st.metric(label,val)
        if pct>=50:st.error('🚨 HIGH RISK ENVIRONMENT — More than half of recorded complaints are High/Critical priority.')
        elif pct>=25:st.warning('⚠️ ELEVATED RISK — A significant proportion of complaints require management attention.')
        else:st.success('✓ CURRENT RISK LEVEL — High/Critical complaints represent less than 25% of recorded complaints.')
        st.markdown('<div class="panel"><div class="ptitle">Risk concentration by category</div><div class="psub">Categories containing High or Critical complaints</div></div>',unsafe_allow_html=True); st.bar_chart(hc.category.value_counts()) if not hc.empty else st.info('No High/Critical category concentration available.'); st.divider()
        st.markdown('### Critical complaints'); st.dataframe(crit[['timestamp','category','complaint','key_issue','business_action']],use_container_width=True,hide_index=True) if not crit.empty else st.success('No critical complaints recorded.'); st.markdown('### High priority complaints'); st.dataframe(high[['timestamp','category','complaint','key_issue']],use_container_width=True,hide_index=True) if not high.empty else st.success('No high-priority complaints recorded.')
    else:st.info('Analyze complaints first to activate risk monitoring.')

with t5:
    st.markdown('<div class="eyebrow">MANAGEMENT REPORTING</div><div class="heading">From complaints<br>to decisions.</div><div class="copy">Convert complaint intelligence into an executive-level management summary and downloadable business report.</div>',unsafe_allow_html=True)
    if st.session_state.analyzed_complaints:
        df=pd.DataFrame(st.session_state.analyzed_complaints); st.markdown('<div class="mgmt"><div class="eyebrow">AI EXECUTIVE SUMMARY</div><div class="ptitle" style="font-size:23px">Give management the bigger picture.</div><div class="copy" style="margin-top:8px">Gemini reviews the complaint database and identifies major areas, risks, recommended actions and management priority.</div></div>',unsafe_allow_html=True)
        if st.button('Generate AI Management Summary  →',type='primary',use_container_width=True):
            with st.spinner('Gemini is preparing the management analysis...'): st.session_state.management_summary=management_summary(df)
        if st.session_state.management_summary:
            st.markdown('<div class="mgmt">',unsafe_allow_html=True); st.markdown(st.session_state.management_summary); st.markdown('</div>',unsafe_allow_html=True)
        else:st.info('Generate the AI Management Summary to create the executive analysis.')
        st.divider(); st.markdown('<div class="eyebrow">EXPORT</div><div class="heading" style="font-size:30px">Take the intelligence with you.</div>',unsafe_allow_html=True)
        st.download_button('Download complete complaint CSV',csv_data(st.session_state.analyzed_complaints),f'finance_complaints_{datetime.now():%Y%m%d_%H%M%S}.csv','text/csv',use_container_width=True)
        if st.session_state.management_summary:
            st.download_button('Download professional management report',report(df,st.session_state.management_summary),f'management_report_{datetime.now():%Y%m%d_%H%M%S}.html','text/html',use_container_width=True)
        else:st.warning('Generate the AI Management Summary first to enable the professional management report.')
        st.divider(); st.markdown('<div class="eyebrow">DATABASE</div><div class="heading" style="font-size:28px">Data management.</div>',unsafe_allow_html=True); st.warning('Deleting the complaint database permanently removes all currently stored complaint records.')
        if st.button('Clear all complaint data',use_container_width=True):
            st.session_state.analyzed_complaints=[]; st.session_state.complaint_input=''; st.session_state.management_summary=''; st.session_state.last_analysis=None
            if os.path.exists(DB):os.remove(DB)
            st.success('Complaint database cleared.'); st.rerun()
    else:st.info('No complaint data is available for reporting yet.')

st.markdown('<div class="footer"><strong>Finance Complaint Intelligence</strong><br>AI-assisted financial customer complaint management and decision-support prototype.<br><br>Python · Streamlit · Google Gemini AI · Pandas</div>',unsafe_allow_html=True)
