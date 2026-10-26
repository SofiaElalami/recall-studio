import json
import math
import random
import time
from pathlib import Path
import streamlit as st

ROOT = Path(__file__).parent
QUESTIONS = json.loads((ROOT / 'data/questions.json').read_text())
BY_ID = {q['id']: q for q in QUESTIONS}
st.set_page_config(page_title='Recall Studio · Accounting Analytics', page_icon='✦', layout='wide')
st.markdown("""
<style>
.stApp {background:#faf9f6;color:#28352f}
.block-container {max-width:1120px;padding-top:2.4rem;padding-bottom:3rem}
h1,h2,h3 {letter-spacing:-.035em}
h1 {font-size:3.1rem!important}
[data-testid="stSidebar"] {background:#eeefe8}
.stButton>button {border-radius:12px;min-height:2.7rem}
[data-testid="stMetric"] {background:#eef2e9;border-radius:18px;padding:18px}
.hero {background:#e7eddf;border-radius:24px;padding:32px;margin-bottom:24px}
.eyebrow {font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:#55654c}
.flashcard {background:#efeaf7;border:1px solid #d8cee8;border-radius:22px;padding:32px;min-height:200px;margin:16px 0}
.small {color:#616c65;font-size:14px}
</style>
""", unsafe_allow_html=True)

defaults = dict(page='Home', cards={}, attempts={}, qid='Q001', exam=None, exam_number=0)
for k,v in defaults.items():
    if k not in st.session_state: st.session_state[k] = v

def go(page, qid=None):
    st.session_state.page = page
    if qid: st.session_state.qid = qid

def review_card(qid, status):
    st.session_state.cards[qid]["status"]=status
    st.session_state.cards[qid]["reviews"]+=1

def save_attempt(qid, key):
    st.session_state.attempts[qid] = st.session_state[key]

def downloads(q, prefix):
    with st.expander('Download exercise files'):
        for f in q['files']:
            st.download_button(f, (ROOT/'data'/f).read_bytes(), file_name=f, key=prefix+f)
        st.caption('Use these original course files in Excel or your SQL tool. Return here to compare your work.')

def answer(q):
    st.markdown('**Worked answer**')
    st.write(q['answer'])
    if q['code']: st.code(q['code'], language='sql' if q['topic']=='SQL' else 'text')
    st.markdown('**How to approach it**')
    st.write(q['method'])
    st.info(q['rule'])

def make_card(q, prefix):
    existing = st.session_state.cards.get(q['id'], {})
    note = st.text_area('What did you miss? Write a short note for your future self.',
                        value=existing.get('note',''), key=prefix+'_note',
                        placeholder='For example: I counted all Brooklyn permits and forgot the event type.')
    if st.button('Save to my mistake cards', key=prefix+'_save', type='primary'):
        st.session_state.cards[q['id']] = {
            'note':note, 'status':'Review again',
            'attempt':st.session_state.attempts.get(q['id'],''),
            'reviews':existing.get('reviews',0)}
        st.session_state['notice']='Card saved. Export your cards before closing or refreshing.'
        st.rerun()

def validate_import(raw):
    obj=json.loads(raw)
    if not isinstance(obj,dict) or obj.get('version')!=1 or not isinstance(obj.get('cards'),dict):
        raise ValueError('Choose a Recall Studio version 1 export.')
    cleaned={}
    for qid, card in obj['cards'].items():
        if qid not in BY_ID or not isinstance(card,dict):
            raise ValueError('The file contains an unknown exercise or invalid card.')
        if card.get('status') not in ['Review again','Got it']: raise ValueError('Invalid card status.')
        if not all(isinstance(card.get(f,''),str) and len(card.get(f,''))<=20000 for f in ['note','attempt']):
            raise ValueError('Invalid card text.')
        n=card.get('reviews',0)
        if not isinstance(n,int) or n<0 or n>100000:raise ValueError('Invalid review count.')
        cleaned[qid]={k:card.get(k,'') for k in ['note','attempt','status']}
        cleaned[qid]['reviews']=n
    return cleaned

with st.sidebar:
    st.markdown('## ✦ Recall Studio')
    st.caption('DATA ANALYTICS IN ACCOUNTING')
    for label in ['Home','Practice','Mock exam','My mistake cards']:
        st.button(label, on_click=go, args=(label,), use_container_width=True,
                  type='primary' if st.session_state.page==label else 'secondary')
    st.divider()
    st.markdown('**Take your learning with you**')
    st.caption('Cards stay in this session. Export before closing or refreshing; import next time.')
    payload=json.dumps({'version':1,'cards':st.session_state.cards},indent=2)
    st.download_button('Export my cards', payload, 'recall_cards.json', 'application/json', use_container_width=True)
    with st.expander('Import saved cards'):
        uploaded=st.file_uploader('Select your recall_cards.json',type='json')
        if st.button('Import cards',disabled=uploaded is None):
            try:
                if uploaded.size>2_000_000:raise ValueError('File is too large.')
                cards=validate_import(uploaded.getvalue())
                st.session_state.cards.update(cards)
                st.session_state['notice']=f'Imported {len(cards)} cards. Matching cards were replaced.'
                st.rerun()
            except (ValueError,TypeError,UnicodeDecodeError):
                st.error('Could not import this file. Use an unedited Recall Studio card export.')
    st.caption('No account or AI API key required.')

if 'notice' in st.session_state:
    st.success(st.session_state.pop('notice'))

page=st.session_state.page
if page=='Home':
    st.markdown('<div class="hero"><div class="eyebrow">Your next study session</div><h1>Turn mistakes into<br>something you remember.</h1><p>Practise accounting analytics. Explain your reasoning.<br>Keep the lessons you want to come back to.</p></div>',unsafe_allow_html=True)
    a,b,c=st.columns(3)
    a.metric('Practice questions',len(QUESTIONS))
    b.metric('Cards to revisit',sum(c['status']=='Review again' for c in st.session_state.cards.values()))
    c.metric('Cards marked understood',sum(c['status']=='Got it' for c in st.session_state.cards.values()))
    st.write('')
    a,b=st.columns([1.3,1])
    with a:
        st.subheader('Make one mistake useful')
        st.write('1. Try an exercise using its source file.\n2. Compare your method with the worked solution.\n3. Save a card explaining your mistake.\n4. Recall the rule before turning the card over.')
        st.button('Start practising →',on_click=go,args=('Practice',),type='primary')
    with b:
        with st.container(border=True):
            st.markdown('### A small practice exam')
            st.write('One Excel / ETL question, one SQL question and one regression question. Eight minutes, then a self-assessment.')
            st.button('Try a mock exam',on_click=go,args=('Mock exam',))
    with st.expander('About the questions and materials'):
        st.write('This student-built practice bank uses a selection of the supplied NYC permits, ETL, IntegrateCo, Chinook, Songs and restaurant materials. It does not claim to reproduce the official exam or cover every supplied case. Questions include adaptations of the skills in those cases.')
        st.write('Numerical answers and SQL outputs are calculated from the bundled files. Open explanations and SQL methods are self-assessed; the app does not automatically grade arbitrary formulas, SQL or prose.')
        st.write('Regression benchmarks use total sales per observed date, an intercept and ordinary OLS standard errors. A different aggregation or model produces different results.')

elif page=='Practice':
    st.caption('PRACTICE / BUILD YOUR METHOD')
    st.title('One question at a time.')
    a,b=st.columns([1,2])
    topic=a.selectbox('Topic',['All topics']+sorted({q['topic'] for q in QUESTIONS}))
    search=b.text_input('Search questions',placeholder='Try joins, payroll or temperature')
    filtered=[q for q in QUESTIONS if (topic=='All topics' or q['topic']==topic) and search.lower() in ' '.join([q['title'],q['prompt'],q['case'],q['id']]).lower()]
    if not filtered:
        st.info('No matching questions. Try another search.')
    else:
        ids=[q['id'] for q in filtered]
        idx=ids.index(st.session_state.qid) if st.session_state.qid in ids else 0
        qid=st.selectbox('Exercise',ids,index=idx,format_func=lambda x:f"{x} · {BY_ID[x]['case']} · {BY_ID[x]['title']}")
        st.session_state.qid=qid
        q=BY_ID[qid]
        with st.container(border=True):
            st.caption(f"{q['topic']} · {q['case']} · approximately {q['minutes']} minutes")
            st.subheader(q['title']);st.write(q['prompt'])
            downloads(q,'p_'+qid)
            st.text_area('Your answer and reasoning',value=st.session_state.attempts.get(qid,''),key='attempt_'+qid,
                         on_change=save_attempt,args=(qid,'attempt_'+qid),height=140)
            if 'numeric' in q:
                n=st.text_input('Optional: numeric answer only (decimal point, no thousands separators)',key='num_'+qid)
                if st.button('Check numeric answer',key='check_'+qid):
                    try:
                        val=float(n)
                        if not math.isfinite(val):raise ValueError()
                        if math.isclose(val,q['numeric'],rel_tol=0,abs_tol=0.011):
                            st.success('The number matches. Check that your method also answers the question.')
                        else:st.warning('This number does not match. Check your filters, units and aggregation.')
                    except ValueError:st.info('Enter a number such as 1234.56.')
            if st.checkbox('Show the worked solution',key='solution_'+qid):
                answer(q)
                st.divider()
                make_card(q,'practice_'+qid)

elif page=='My mistake cards':
    st.caption('REVIEW / YOUR PERSONAL DECK')
    st.title('Remember the reasoning.')
    st.write('Try to answer aloud before revealing the back. “Got it” is your own judgement, not a test score.')
    cards=st.session_state.cards
    if not cards:
        st.info('Your deck is empty. Try an exercise and save a card from its worked solution.')
        st.button('Find an exercise',on_click=go,args=('Practice',))
    else:
        mode=st.radio('Show cards',['Review again','Got it','All'],horizontal=True)
        ids=[qid for qid,c in cards.items() if mode=='All' or c['status']==mode]
        if not ids:st.success('No cards in this group.')
        else:
            qid=st.selectbox('Choose a card',ids,format_func=lambda x:f"{x} · {BY_ID[x]['title']}")
            q=BY_ID[qid];card=cards[qid]
            st.caption(f"{q['case']} · Reviewed {card['reviews']} times")
            import html
            st.markdown('<div class="flashcard"><div class="eyebrow">Front · recall first</div><h3>'+html.escape(q['prompt'])+'</h3></div>',unsafe_allow_html=True)
            recall=st.text_area('What do you remember?',key='recall_'+qid,placeholder='Explain the method before looking.')
            if st.checkbox('Turn card over',key='flip_'+qid):
                answer(q)
                if card['note']:st.markdown('**My mistake:**');st.write(card['note'])
                if card['attempt']:
                    with st.expander('My original attempt'):st.write(card['attempt'])
                a,b=st.columns(2)
                a.button('Review again',key='again_'+qid,use_container_width=True,on_click=review_card,args=(qid,'Review again'))
                b.button('Got it',key='got_'+qid,type='primary',use_container_width=True,on_click=review_card,args=(qid,'Got it'))
            st.button('Reopen the original exercise',on_click=go,args=('Practice',qid))
            with st.expander('Edit my note'):
                note=st.text_area('Note',value=card['note'],key='edit_'+qid)
                if st.button('Save note'):
                    card['note']=note;st.rerun()

elif page=='Mock exam':
    st.caption('MOCK EXAM / 8 MINUTES')
    st.title('Practise under a time limit.')
    st.write('Three questions from the practice bank. Work in Excel or your SQL tool and record your reasoning here. Solutions appear after you finish or time expires.')
    if st.button('Start a new exam',type='primary'):
        groups=[[q for q in QUESTIONS if q['topic'] in ['Excel','Excel / ETL']],
                [q for q in QUESTIONS if q['topic']=='SQL'],
                [q for q in QUESTIONS if q['topic']=='Regression']]
        st.session_state.exam_number+=1
        st.session_state.exam={'ids':[random.choice(g)['id'] for g in groups],'end':time.time()+480,'done':False}
        st.rerun()
    exam=st.session_state.exam
    if exam:
        if time.time()>=exam['end']:exam['done']=True
        @st.fragment(run_every='1s' if not exam['done'] else None)
        def clock():
            remaining=max(0,int(exam['end']-time.time()))
            st.metric('Time remaining',f'{remaining//60:02d}:{remaining%60:02d}')
            if remaining<=0 and not exam['done']:
                exam['done']=True;st.rerun()
        clock()
        if not exam['done'] and st.button('Finish and review'):
            exam['done']=True;st.rerun()
        for i,qid in enumerate(exam['ids'],1):
            q=BY_ID[qid];prefix=f"exam_{st.session_state.exam_number}_{qid}"
            with st.container(border=True):
                st.subheader(f"{i}. {q['title']}")
                st.caption(q['topic']+' · '+q['case']);st.write(q['prompt'])
                downloads(q,prefix)
                key=prefix+'_attempt'
                st.text_area('Your answer and reasoning',key=key,disabled=exam['done'],
                             on_change=save_attempt,args=(qid,key))
                if exam['done']:
                    answer(q)
                    st.radio('Self-assessment',['Not reviewed','Needs practice','Understood'],key=prefix+'_rating',horizontal=True)
                    make_card(q,prefix)
        if exam['done']:st.success('Exam finished. Compare each answer and save the errors you want to revisit.')
