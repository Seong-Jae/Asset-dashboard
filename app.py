import os
import json
import urllib.request
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
from datetime import datetime
import streamlit as st
import platform

# --- 한글 폰트 설정 ---
if platform.system() == 'Linux':
    import matplotlib.font_manager as fm
    sys_fonts = fm.findSystemFonts()
    for f in sys_fonts:
        if 'Nanum' in f: fm.fontManager.addfont(f)
    plt.rcParams['font.family'] = 'NanumGothic'
elif platform.system() == 'Darwin':
    plt.rcParams['font.family'] = 'AppleGothic'
else:
    plt.rcParams['font.family'] = 'Malgun Gothic'

plt.rcParams['axes.unicode_minus'] = False 

# --- 기본 페이지 설정 ---
st.set_page_config(page_title="성재님의 자산 MTS", page_icon="📈", layout="wide", initial_sidebar_state="collapsed")

# --- MTS 스타일 커스텀 CSS 주입 ---
st.markdown("""
    <style>
    * {
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
        -webkit-text-size-adjust: 100%;
    }
    
    .stApp { background-color: #0B0E14; }
    .summary-card {
        background-color: #1C1F26;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.5);
        margin-bottom: 20px;
    }
    .summary-title { color: #8B95A1; font-size: 14px; margin-bottom: 5px; font-weight: 600; }
    .summary-total { color: #FFFFFF; font-size: 32px; font-weight: 800; margin: 0px 0px 5px 0px; }
    .profit { color: #FF4256 !important; font-weight: 700; }  
    .loss { color: #3182F6 !important; font-weight: 700; }    
    .neutral { color: #8B95A1 !important; font-weight: 500; }
    
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px; white-space: pre-wrap;
        background-color: #1C1F26; border-radius: 8px 8px 0 0;
        padding: 10px 16px; color: #FAFAFA; font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2C313C; border-bottom-color: #FF4256 !important;
        color: #FF4256 !important; font-weight: bold;
    }
    
    .table-wrapper {
        overflow-x: auto;
        -webkit-overflow-scrolling: touch; 
        border-radius: 10px;
        margin-bottom: 20px;
    }
    table { 
        width: 100%; border-collapse: collapse; background-color: #1C1F26; 
        color: #FFFFFF; white-space: nowrap; 
    }
    th, td { padding: 12px 10px; border-bottom: 1px solid #2C313C; }
    th { background-color: #2C313C; color: #8B95A1; font-size: 13px; text-align: center !important; font-weight: 600; }
    td { font-size: 14px; font-weight: 500; }
    tr:hover { background-color: #252A34; }
    </style>
""", unsafe_allow_html=True)

DATA_FILE = "my_assets_v26.json"
HISTORY_FILE = "trade_history_v26.json"

DEFAULT_ASSETS = [
    {"category": "키움(일반)", "name": "한컴위드", "type": "stock", "qty": 15678, "ticker": "054920", "unit": "주", "avg_price": 3515},
    {"category": "키움(ISA)", "name": "한컴위드", "type": "stock", "qty": 1804, "ticker": "054920", "unit": "주", "avg_price": 5209},
    {"category": "키움(ISA)", "name": "한컴", "type": "stock", "qty": 59, "ticker": "030520", "unit": "주", "avg_price": 16808},
    {"category": "실물자산", "name": "금", "type": "gold", "qty": 37.50, "ticker": "GC=F", "unit": "g", "avg_price": 239776},
    {"category": "외환", "name": "달러", "type": "fx", "qty": 354.42, "ticker": "USD", "unit": "USD", "avg_price": 1410.74}
]

# 차트 색상 세팅
BG_COLOR, PANEL_COLOR, TEXT_COLOR, SUB_TEXT_COLOR = "#0B0E14", "#1C1F26", "#FFFFFF", "#8B95A1"
RED_COLOR, BLUE_COLOR = "#FF4256", "#3182F6"
plt.style.use('dark_background')
plt.rcParams.update({
    "figure.facecolor": BG_COLOR, "axes.facecolor": BG_COLOR, "savefig.facecolor": BG_COLOR,
    "text.color": TEXT_COLOR, "axes.labelcolor": TEXT_COLOR,
    "xtick.color": SUB_TEXT_COLOR, "ytick.color": SUB_TEXT_COLOR, "grid.color": "#2C313C"
})

def format_manwon(x, pos): return f"{int(x / 10000):,}"
def format_currency(x, pos): return f"{int(x):,}"

def load_data():
    assets, principals, deposits, history = DEFAULT_ASSETS.copy(), {}, {}, []
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    assets, principals, deposits = data.get("assets", DEFAULT_ASSETS.copy()), data.get("principals", {}), data.get("deposits", {})
                else: assets = data
        except: pass
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f: history = json.load(f)
        except: pass
    return assets, principals, deposits, history

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump({"assets": st.session_state.assets, "principals": st.session_state.principals, "deposits": st.session_state.deposits}, f, ensure_ascii=False, indent=4)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f: json.dump(st.session_state.history, f, ensure_ascii=False, indent=4)

def get_korean_stock_price(code):
    try:
        url = f"https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{code}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        return int(json.loads(urllib.request.urlopen(req).read().decode('utf-8'))['result']['areas'][0]['datas'][0]['nv'])
    except:
        try:
            h = yf.Ticker(f"{code}.KQ" if code in ["054920", "030520"] else f"{code}.KS").history(period="1d")
            if not h.empty: return int(h['Close'].iloc[-1])
        except: pass
    return 0

@st.cache_data(ttl=60)
def fetch_all_prices(assets):
    prices = {}
    usd_krw = yf.Ticker("KRW=X").history(period="5d")['Close'].iloc[-1] if not yf.Ticker("KRW=X").history(period="5d").empty else 1400
    for item in assets:
        p, t = 0, item["type"]
        if t == "stock": p = get_korean_stock_price(item["ticker"])
        elif t in ["gold", "silver"]:
            h = yf.Ticker(item["ticker"]).history(period="5d")
            if not h.empty: p = (h['Close'].iloc[-1] * usd_krw) / 31.1034768
        elif t == "fx":
            h = yf.Ticker("KRW=X" if item["ticker"].upper() == "USD" else f"{item['ticker'].upper()}KRW=X").history(period="5d")
            if not h.empty: p = h['Close'].iloc[-1]
        elif t == "crypto":
            h = yf.Ticker(item["ticker"]).history(period="5d")
            if not h.empty: p = h['Close'].iloc[-1]
        elif t == "cash": p = 1
        prices[f"{item['category']}_{item['name']}"] = p
    return prices

if 'assets' not in st.session_state:
    st.session_state.assets, st.session_state.principals, st.session_state.deposits, st.session_state.history = load_data()

current_prices = fetch_all_prices(st.session_state.assets)

total_valuation, global_principal = 0, 0
cat_summary = {}
asset_df_data = []

for idx, item in enumerate(st.session_state.assets):
    cat, name, t_type = item.get("category", "기타"), item["name"], item["type"]
    qty, avg_p = float(item["qty"]), float(item.get("avg_price", 0))
    price = current_prices.get(f"{cat}_{name}", 0)
    
    tot_val = price * qty
    total_valuation += tot_val
    invested = tot_val if t_type == "cash" else avg_p * qty
    pl_amt = tot_val - invested if avg_p > 0 and t_type != "cash" else 0
    pl_pct = (pl_amt / invested) * 100 if invested > 0 and t_type != "cash" else 0
    
    if cat not in cat_summary: cat_summary[cat] = {"stock_val": 0, "auto_prin": 0}
    cat_summary[cat]["stock_val"] += tot_val
    cat_summary[cat]["auto_prin"] += invested
    
    asset_df_data.append({
        "분류": cat, "자산명": name, 
        "수량": f"{qty:,.4f}" if t_type == "crypto" else f"{qty:,.2f}" if qty%1!=0 else f"{int(qty):,}",
        "매수단가": f"{avg_p:,.2f}" if t_type in ["fx", "crypto"] else f"{int(avg_p):,}",
        "현재가": f"{price:,.2f}" if t_type in ["fx", "crypto"] else f"{int(price):,}",
        "평가손익": f"{int(pl_amt):,}", "수익률(%)": f"{pl_pct:.2f}%", "평가금액": f"{int(tot_val):,}",
        "_raw_pl": pl_amt, "_raw_val": tot_val, "_type": t_type
    })

for cat, dep in st.session_state.deposits.items():
    if cat != "외환" and dep > 0:
        asset_df_data.append({"분류": cat, "자산명": "예수금(현금)", "수량": "-", "매수단가": "-", "현재가": "-", "평가손익": "-", "수익률(%)": "-", "평가금액": f"{int(dep):,}", "_raw_pl": 0, "_raw_val": dep, "_type": "cash"})

summary_df_data = []
for cat, data in cat_summary.items():
    stock_val, auto_prin = data["stock_val"], data["auto_prin"]
    dep = st.session_state.deposits.get(cat, 0.0)
    prin = st.session_state.principals.get(cat, auto_prin)
    
    global_principal += prin
    cat_tot_val = stock_val + dep
    total_valuation += dep
    
    p_amt = cat_tot_val - prin
    p_pct = (p_amt / prin * 100) if prin > 0 else 0
    
    summary_df_data.append({
        "분류": cat, "순원금": f"{int(prin):,}", "예수금": f"{int(dep):,}", 
        "주식등평가금": f"{int(stock_val):,}", "총평가금액": f"{int(cat_tot_val):,}",
        "평가손익": f"{int(p_amt):,}", "수익률(%)": f"{p_pct:.2f}%", "_raw_pl": p_amt
    })

tot_pl = total_valuation - global_principal
tot_pct = (tot_pl / global_principal * 100) if global_principal > 0 else 0

# --- 📌 상단 MTS 스타일 대시보드 카드 (▲/▼ 적용) ---
if tot_pl > 0:
    sign_str = "▲ "
    pl_class = "profit"
elif tot_pl < 0:
    sign_str = "▼ "
    pl_class = "loss"
else:
    sign_str = ""
    pl_class = "neutral"

st.markdown(f"""
<div class="summary-card">
    <div class="summary-title">👋 성재님의 총 자산 (KRW)</div>
    <div class="summary-total">{int(total_valuation):,} 원</div>
    <div style="font-size: 16px; margin-top: 10px;">
        <div class="{pl_class}" style="margin-bottom: 4px;">총 손익: {sign_str}{int(abs(tot_pl)):,}원 ({sign_str}{abs(tot_pct):.2f}%)</div>
        <div class="summary-title">총 투자원금: {int(global_principal):,}원</div>
    </div>
</div>
""", unsafe_allow_html=True)

col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
with col_btn3:
    if st.button("🔄 실시간 시세 갱신", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- 탭 구성 ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["보유 자산", "계좌 요약", "비중 분석", "손익 현황", "시세 차트", "거래 내역"])

def color_profit_loss(val):
    if isinstance(val, str) and ('%' in val or val.replace(',', '').lstrip('-').isdigit()):
        v = float(val.replace('%', '').replace(',', ''))
        color = RED_COLOR if v > 0 else BLUE_COLOR if v < 0 else SUB_TEXT_COLOR
        return f'color: {color}; font-weight: bold;'
    return ''

with tab1:
    df_assets = pd.DataFrame(asset_df_data).drop(columns=['_raw_pl', '_raw_val', '_type'])
    cols_center = ['분류', '자산명']
    cols_right = ['수량', '매수단가', '현재가', '평가손익', '수익률(%)', '평가금액']
    
    styled_df = (df_assets.style
                 .hide(axis="index")
                 .map(color_profit_loss, subset=['평가손익', '수익률(%)'])
                 .set_properties(subset=cols_center, **{'text-align': 'center'})
                 .set_properties(subset=cols_right, **{'text-align': 'right'})
                )
    
    st.markdown(f'<div class="table-wrapper">{styled_df.to_html()}</div>', unsafe_allow_html=True)
    
    with st.expander("💼 주식 매수 / 매도 / 신규 계좌 등록"):
        action = st.radio("작업 선택", ["매수", "매도", "신규 계좌 등록"], horizontal=True)
        
        if action == "매수":
            asset_names = [f"{i} : {a['category']} - {a['name']}" for i, a in enumerate(st.session_state.assets)]
            options = ["✨ 새로운 종목 매수"] + asset_names
            
            sel_option = st.selectbox("대상 자산", options)
            
            if sel_option == "✨ 새로운 종목 매수":
                existing_cats = list(set([a['category'] for a in st.session_state.assets] + list(st.session_state.deposits.keys())))
                
                col_n1, col_n2, col_n3 = st.columns(3)
                new_cat = col_n1.selectbox("계좌(분류) 선택", existing_cats)
                new_name = col_n2.text_input("자산명 (예: 삼성전자)")
                new_type = col_n3.selectbox("자산 종류", ["stock", "crypto", "fx", "gold", "silver"])
                
                col_n4, col_n5, col_n6 = st.columns(3)
                new_ticker = col_n4.text_input("종목코드/티커 (예: 005930)")
                new_unit = col_n5.text_input("단위 (예: 주, 달러)", "주")
                t_date = col_n6.date_input("거래일자", datetime.now())
                
                col_n7, col_n8 = st.columns(2)
                t_qty = col_n7.number_input("매수 수량", min_value=0.0, step=1.0)
                t_price = col_n8.number_input("체결단가 (원)", min_value=0.0, step=100.0)
                
                if st.button("새 종목 매수 실행", use_container_width=True, type="primary"):
                    if new_name and new_ticker and t_qty > 0 and t_price >= 0:
                        gross_amt = t_qty * t_price
                        curr_dep = st.session_state.deposits.get(new_cat, 0.0)
                        if curr_dep < gross_amt:
                            st.error(f"예수금 부족! (현재: {int(curr_dep):,}원 / 필요: {int(gross_amt):,}원)")
                        else:
                            st.session_state.deposits[new_cat] = curr_dep - gross_amt
                            new_asset = {
                                "category": new_cat, "name": new_name, "type": new_type,
                                "qty": t_qty, "ticker": new_ticker, "unit": new_unit, "avg_price": t_price
                            }
                            st.session_state.assets.append(new_asset)
                            st.session_state.history.append({"date": str(t_date), "type": "매수", "category": new_cat, "name": new_name, "qty": t_qty, "price": t_price, "unit": new_unit})
                            save_data()
                            st.rerun()
                    else:
                        st.error("자산명, 종목코드, 수량 및 단가를 정확히 입력해주세요.")
            
            else:
                sel_asset_idx = int(sel_option.split(" : ")[0])
                sel_asset = st.session_state.assets[sel_asset_idx]
                
                col_a, col_b, col_c = st.columns(3)
                t_date = col_a.date_input("거래일자", datetime.now())
                t_qty = col_b.number_input("매수 수량", min_value=0.0, step=1.0)
                t_price = col_c.number_input("체결단가 (원)", min_value=0.0, step=100.0, value=float(current_prices.get(f"{sel_asset['category']}_{sel_asset['name']}", 0)))
                
                if st.button(f"매수 실행", use_container_width=True, type="primary"):
                    if t_qty > 0 and t_price >= 0:
                        cat = sel_asset['category']
                        gross_amt = t_qty * t_price
                        curr_dep = st.session_state.deposits.get(cat, 0.0)
                        if curr_dep < gross_amt:
                            st.error(f"예수금 부족! (현재: {int(curr_dep):,}원 / 필요: {int(gross_amt):,}원)")
                        else:
                            st.session_state.deposits[cat] = curr_dep - gross_amt
                            old_qty, old_avg = float(sel_asset['qty']), float(sel_asset.get('avg_price', 0))
                            new_qty = old_qty + t_qty
                            sel_asset['avg_price'] = ((old_qty * old_avg) + (t_qty * t_price)) / new_qty
                            sel_asset['qty'] = int(new_qty) if new_qty.is_integer() else new_qty
                            st.session_state.history.append({"date": str(t_date), "type": "매수", "category": cat, "name": sel_asset['name'], "qty": t_qty, "price": t_price, "unit": sel_asset['unit']})
                            save_data()
                            st.rerun()

        elif action == "매도":
            asset_names = [f"{i} : {a['category']} - {a['name']}" for i, a in enumerate(st.session_state.assets)]
            if not asset_names:
                st.warning("보유 중인 자산이 없습니다.")
            else:
                sel_asset_idx = int(st.selectbox("대상 자산", asset_names).split(" : ")[0])
                sel_asset = st.session_state.assets[sel_asset_idx]
                
                col_a, col_b, col_c = st.columns(3)
                t_date = col_a.date_input("거래일자", datetime.now())
                t_qty = col_b.number_input("매도 수량", min_value=0.0, step=1.0)
                t_price = col_c.number_input("체결단가 (원)", min_value=0.0, step=100.0, value=float(current_prices.get(f"{sel_asset['category']}_{sel_asset['name']}", 0)))
                
                if st.button(f"매도 실행", use_container_width=True, type="primary"):
                    if t_qty > 0 and t_price >= 0:
                        cat = sel_asset['category']
                        gross_amt = t_qty * t_price
                        old_qty = float(sel_asset['qty'])
                        if t_qty > old_qty: st.error("보유 수량보다 많습니다.")
                        else:
                            tax_fee = gross_amt * 0.002 if sel_asset['type'] == 'stock' else 0
                            st.session_state.deposits[cat] = st.session_state.deposits.get(cat, 0.0) + (gross_amt - tax_fee)
                            new_qty = old_qty - t_qty
                            sel_asset['qty'] = int(new_qty) if new_qty.is_integer() else new_qty
                            if new_qty == 0: sel_asset['avg_price'] = 0
                            st.session_state.history.append({"date": str(t_date), "type": "매도", "category": cat, "name": sel_asset['name'], "qty": t_qty, "price": t_price, "unit": sel_asset['unit']})
                            save_data()
                            st.rerun()

        elif action == "신규 계좌 등록":
            st.markdown("<br><b>✨ 새로운 계좌(분류) 개설</b>", unsafe_allow_html=True)
            col_k1, col_k2 = st.columns(2)
            new_account_name = col_k1.text_input("새 계좌명 (예: 토스증권, 하나은행)")
            init_deposit = col_k2.number_input("초기 입금액 (예수금)", min_value=0.0, step=10000.0)
            
            if st.button("신규 계좌 등록", use_container_width=True, type="primary"):
                if new_account_name:
                    if new_account_name in st.session_state.deposits:
                        st.error("이미 존재하는 계좌명입니다.")
                    else:
                        st.session_state.deposits[new_account_name] = init_deposit
                        st.session_state.principals[new_account_name] = init_deposit
                        st.success(f"'{new_account_name}' 계좌가 성공적으로 생성되었습니다!")
                        save_data()
                        st.rerun()
                else:
                    st.error("계좌명을 입력해주세요.")

with tab2:
    df_sum = pd.DataFrame(summary_df_data).drop(columns=['_raw_pl'])
    
    cols_center_sum = ['분류']
    cols_right_sum = ['순원금', '예수금', '주식등평가금', '총평가금액', '평가손익', '수익률(%)']
    
    styled_sum = (df_sum.style
                  .hide(axis="index")
                  .map(color_profit_loss, subset=['평가손익', '수익률(%)'])
                  .set_properties(subset=cols_center_sum, **{'text-align': 'center'})
                  .set_properties(subset=cols_right_sum, **{'text-align': 'right'})
                 )
    
    st.markdown(f'<div class="table-wrapper">{styled_sum.to_html()}</div>', unsafe_allow_html=True)
    
    with st.expander("💳 입/출금 및 예수금 직접 설정"):
        cats = [c["분류"] for c in summary_df_data]
        if cats:
            target_cat = st.selectbox("계좌 선택", cats)
            col_m1, col_m2 = st.columns(2)
            dw_amt = col_m1.number_input("금액 (원)", min_value=0.0, step=10000.0)
            dw_type = col_m2.radio("작업", ["입금 (+)", "출금 (-)"], horizontal=True)
            
            if st.button("입/출금 적용", use_container_width=True):
                if dw_amt > 0:
                    curr_prin = st.session_state.principals.get(target_cat, cat_summary[target_cat]["auto_prin"])
                    curr_dep = st.session_state.deposits.get(target_cat, 0.0)
                    if dw_type == "입금 (+)":
                        st.session_state.principals[target_cat] = curr_prin + dw_amt
                        st.session_state.deposits[target_cat] = curr_dep + dw_amt
                    else:
                        if curr_dep < dw_amt: st.error("예수금이 부족합니다.")
                        else:
                            st.session_state.principals[target_cat] = curr_prin - dw_amt
                            st.session_state.deposits[target_cat] = curr_dep - dw_amt
                    save_data()
                    st.rerun()

with tab3:
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    mode = st.radio("분석 기준", ["현재 평가금액 기준", "총 원금 기준"], horizontal=True)
    
    fig_pie, ax_pie = plt.subplots(figsize=(6, 5))
    cat_vals = {}
    if mode == "현재 평가금액 기준":
        for d in summary_df_data: cat_vals[d['분류']] = int(d['총평가금액'].replace(',', ''))
    else:
        for d in summary_df_data: cat_vals[d['분류']] = int(d['순원금'].replace(',', ''))
        
    if cat_vals:
        wedges, texts, autotexts = ax_pie.pie(
            cat_vals.values(), labels=cat_vals.keys(), autopct='%1.1f%%', 
            colors=plt.cm.Set3.colors, textprops={'color': TEXT_COLOR, 'fontsize': 10},
            radius=1.0
        )
        for autotext in autotexts:
            autotext.set_color('black')
            autotext.set_fontweight('bold')
        ax_pie.set_title("전체 자산 비중", color=TEXT_COLOR, pad=15, fontweight='bold')
        ax_pie.set_xlim(-1.5, 1.5)
        ax_pie.set_ylim(-1.5, 1.5)
        st.pyplot(fig_pie)
    
    st.markdown("<hr style='border: 1px solid #2C313C;'>", unsafe_allow_html=True)
    st.markdown("#### 🔍 계좌(분류)별 상세 자산 구성")
    
    cols = st.columns(2)
    idx = 0
    
    custom_order = ["키움(일반)", "실물자산", "키움(ISA)", "외환"]
    display_cats = [c for c in custom_order if c in cat_vals.keys()]
    display_cats += [c for c in cat_vals.keys() if c not in display_cats]
    
    for cat in display_cats:
        sub_items = [d for d in asset_df_data if d['분류'] == cat and d['_raw_val'] > 0]
        if sub_items:
            with cols[idx % 2]:
                fig_sub, ax_sub = plt.subplots(figsize=(4, 4))
                s_names = [d['자산명'] for d in sub_items]
                s_vals = [d['_raw_val'] for d in sub_items]
                
                wedges, texts, autotexts = ax_sub.pie(
                    s_vals, labels=s_names, autopct='%1.1f%%', 
                    colors=plt.cm.tab20.colors, textprops={'color': TEXT_COLOR, 'fontsize': 9},
                    radius=1.0
                )
                for autotext in autotexts:
                    autotext.set_color('black')
                    autotext.set_fontweight('bold')
                ax_sub.set_title(f"[{cat}]", color=TEXT_COLOR, fontweight='bold')
                ax_sub.set_xlim(-1.8, 1.8)
                ax_sub.set_ylim(-1.8, 1.8)
                st.pyplot(fig_sub)
            idx += 1

with tab4:
    st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True) 
    fig_bar, (ax1, ax2) = plt.subplots(2, 1, figsize=(7, 11))
    plt.subplots_adjust(hspace=0.4, top=0.92) 
    
    cat_names = [d['분류'] for d in summary_df_data]
    cat_pls = [d['_raw_pl'] for d in summary_df_data]
    c_colors = [RED_COLOR if x >= 0 else BLUE_COLOR for x in cat_pls]
    if cat_names:
        bars1 = ax1.bar(cat_names, cat_pls, color=c_colors, width=0.5)
        ax1.set_title("계좌별 손익 현황 (만원)", color=TEXT_COLOR, pad=20, fontweight='bold')
        ax1.axhline(0, color=TEXT_COLOR, alpha=0.3)
        ax1.yaxis.set_major_formatter(FuncFormatter(format_manwon))
        for bar in bars1:
            h = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2, h, f"{int(h/10000)}만", ha='center', va='bottom' if h>0 else 'top', color=TEXT_COLOR, fontweight='bold', fontsize=9)
            
    item_pl_agg = {}
    for d in asset_df_data:
        if d['_type'] != 'cash' and d['_raw_pl'] != 0:
            name = d['자산명']
            item_pl_agg[name] = item_pl_agg.get(name, 0) + d['_raw_pl']
            
    if item_pl_agg:
        i_names = list(item_pl_agg.keys())
        i_pls = list(item_pl_agg.values())
        i_colors = [RED_COLOR if x >= 0 else BLUE_COLOR for x in i_pls]
        
        bars2 = ax2.bar(i_names, i_pls, color=i_colors, width=0.5)
        ax2.set_title("종목별 합산 손익 현황 (만원)", color=TEXT_COLOR, pad=20, fontweight='bold')
        ax2.axhline(0, color=TEXT_COLOR, alpha=0.3)
        ax2.yaxis.set_major_formatter(FuncFormatter(format_manwon))
        for bar in bars2:
            h = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2, h, f"{int(h/10000)}만", ha='center', va='bottom' if h>0 else 'top', color=TEXT_COLOR, fontweight='bold', fontsize=9)
            
    st.pyplot(fig_bar)

with tab5:
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    col_t1, col_t2 = st.columns(2)
    t_asset = col_t1.selectbox("조회할 종목", [a['name'] for a in st.session_state.assets if a['type'] != 'cash'])
    t_period = col_t2.selectbox("조회 기간", ["1mo", "3mo", "6mo", "1y", "3y", "5y"], index=1)
    
    if st.button("📊 차트 불러오기", use_container_width=True):
        asset_info = next((a for a in st.session_state.assets if a['name'] == t_asset), None)
        if asset_info:
            tkr = asset_info['ticker']
            t_type = asset_info['type']
            yf_tkr = f"{tkr}.KQ" if t_type=="stock" and tkr in ["054920", "030520"] else f"{tkr}.KS" if t_type=="stock" else tkr
            if t_type == "fx": yf_tkr = "KRW=X" if tkr.upper()=="USD" else f"{tkr.upper()}KRW=X"
            
            with st.spinner('차트 데이터를 불러오는 중...'):
                try:
                    hist = yf.Ticker(yf_tkr).history(period=t_period)
                    if not hist.empty:
                        # 금, 은 종목일 경우 환율 및 단위 변환
                        if t_type in ["gold", "silver"]:
                            krw_hist = yf.Ticker("KRW=X").history(period=t_period)['Close']
                            hist.index = hist.index.tz_localize(None).normalize()
                            krw_hist.index = krw_hist.index.tz_localize(None).normalize()
                            krw_hist = krw_hist.reindex(hist.index).ffill().bfill()
                            hist['Close'] = (hist['Close'] * krw_hist) / 31.1034768
                            
                        fig_l, ax_l = plt.subplots(figsize=(8, 4))
                        dates, prices = hist.index, hist['Close']
                        c = RED_COLOR if prices.iloc[-1] >= prices.iloc[0] else BLUE_COLOR
                        
                        ax_l.plot(dates, prices, color=c, linewidth=2, label='종가')
                        ax_l.fill_between(dates, prices, min(prices)*0.99, color=c, alpha=0.1)
                        
                        avg_p = float(asset_info.get('avg_price', 0))
                        
                        # 📌 평단가 범위 체크 및 스마트 표시 로직
                        if avg_p > 0:
                            min_p, max_p = prices.min(), prices.max()
                            # 차트 상하단 5% 정도의 여유 공간 계산
                            margin = (max_p - min_p) * 0.05 if max_p != min_p else max_p * 0.05
                            lower_bound = min_p - margin
                            upper_bound = max_p + margin
                            
                            formatted_avg = f"{avg_p:,.2f}" if t_type in ["fx", "crypto"] else f"{int(avg_p):,}"
                            
                            if lower_bound <= avg_p <= upper_bound:
                                # 평단가가 차트 범위 안에 있으면 기존처럼 점선을 그림
                                ax_l.axhline(avg_p, color='#FBBF24', linestyle='--', linewidth=1.5, label=f'내 평단가 ({formatted_avg})')
                            else:
                                # 평단가가 차트 범위를 벗어나면 점선은 그리지 않고 투명한 더미를 통해 범례(텍스트)로만 표시
                                ax_l.plot([], [], ' ', label=f'내 평단가: {formatted_avg} (차트 범위 밖)')
                        
                        ax_l.legend(frameon=False, loc='best')
                        ax_l.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d' if t_period in ["1mo","3mo"] else '%Y-%m'))
                        
                        if t_type in ["fx", "crypto"]:
                            ax_l.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"{x:,.2f}"))
                        else:
                            ax_l.yaxis.set_major_formatter(FuncFormatter(format_currency))
                            
                        ax_l.set_title(f"{t_asset} 시세 추이", color=TEXT_COLOR, fontweight='bold', pad=15)
                        st.pyplot(fig_l)
                    else:
                        st.warning("해당 기간의 차트 데이터를 불러올 수 없습니다.")
                except Exception as e:
                    st.error("데이터를 가져오는 중 문제가 발생했습니다.")

with tab6:
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    if st.session_state.history:
        hist_df = pd.DataFrame(reversed(st.session_state.history))
        styled_hist = hist_df.style.hide(axis="index").set_properties(**{'text-align': 'center'})
        st.markdown(f'<div class="table-wrapper">{styled_hist.to_html()}</div>', unsafe_allow_html=True)
    else:
        st.info("아직 거래 내역이 없습니다.")