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
st.set_page_config(page_title="내 자산 MTS", page_icon="📈", layout="wide", initial_sidebar_state="collapsed")

# --- MTS 스타일 커스텀 CSS 주입 ---
st.markdown("""
    <style>
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
        padding: 10px 16px; color: #FAFAFA;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2C313C; border-bottom-color: #FF4256 !important;
        color: #FF4256 !important; font-weight: bold;
    }
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
        "ID": idx, "분류": cat, "자산명": name, 
        "수량": f"{qty:,.4f}" if t_type == "crypto" else f"{qty:,.2f}" if qty%1!=0 else f"{int(qty):,}",
        "매수단가": f"{avg_p:,.2f}" if t_type in ["fx", "crypto"] else f"{int(avg_p):,}",
        "현재가": f"{price:,.2f}" if t_type in ["fx", "crypto"] else f"{int(price):,}",
        "평가손익": f"{int(pl_amt):,}", "수익률(%)": f"{pl_pct:.2f}%", "평가금액": f"{int(tot_val):,}",
        "_raw_pl": pl_amt, "_raw_val": tot_val, "_type": t_type
    })

for cat, dep in st.session_state.deposits.items():
    if cat != "외환" and dep > 0:
        asset_df_data.append({"ID": "-", "분류": cat, "자산명": "예수금(현금)", "수량": "-", "매수단가": "-", "현재가": "-", "평가손익": "-", "수익률(%)": "-", "평가금액": f"{int(dep):,}", "_raw_pl": 0, "_raw_val": dep, "_type": "cash"})

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

# --- 상단 MTS 스타일 대시보드 카드 ---
sign = "+" if tot_pl > 0 else ""
pl_class = "profit" if tot_pl > 0 else "loss" if tot_pl < 0 else "neutral"

st.markdown(f"""
<div class="summary-card">
    <div class="summary-title">총 평가금액 (KRW)</div>
    <div class="summary-total">{int(total_valuation):,} 원</div>
    <div style="font-size: 16px; margin-top: 10px;">
        <div class="{pl_class}" style="margin-bottom: 4px;">총 손익: {sign}{int(tot_pl):,}원 ({sign}{tot_pct:.2f}%)</div>
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
    df_assets = pd.DataFrame(asset_df_data).drop(columns=['_raw_pl', '_raw_val', '_type', 'ID'])
    # Pandas 버전 호환성을 위해 map 사용 (에러 수정 완료)
    styled_df = df_assets.style.map(color_profit_loss, subset=['평가손익', '수익률(%)'])
    st.dataframe(styled_df, use_container_width=True)
    
    with st.expander("💼 주식 매수 / 매도 / 신규 등록"):
        action = st.radio("작업 선택", ["매수", "매도", "신규 등록"], horizontal=True)
        if action in ["매수", "매도"]:
            asset_names = [f"{i} : {a['category']} - {a['name']}" for i, a in enumerate(st.session_state.assets)]
            sel_asset_idx = int(st.selectbox("대상 자산", asset_names).split(" : ")[0])
            sel_asset = st.session_state.assets[sel_asset_idx]
            
            col_a, col_b, col_c = st.columns(3)
            t_date = col_a.date_input("거래일자", datetime.now())
            t_qty = col_b.number_input("수량", min_value=0.0, step=1.0)
            t_price = col_c.number_input("체결단가 (원)", min_value=0.0, step=100.0, value=float(current_prices.get(f"{sel_asset['category']}_{sel_asset['name']}", 0)))
            
            if st.button(f"{action} 실행", use_container_width=True, type="primary"):
                if t_qty > 0 and t_price >= 0:
                    cat = sel_asset['category']
                    gross_amt = t_qty * t_price
                    if action == "매수":
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

with tab2:
    df_sum = pd.DataFrame(summary_df_data).drop(columns=['_raw_pl'])
    styled_sum = df_sum.style.map(color_profit_loss, subset=['평가손익', '수익률(%)'])
    st.dataframe(styled_sum, use_container_width=True)
    
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

# --- 탭 3: 비중 분석 (전체 비중 & 분류별 상세 구성 추가) ---
with tab3:
    mode = st.radio("분석 기준", ["현재 평가금액 기준", "총 원금 기준"], horizontal=True)
    
    # 1. 전체 분류 비중 파이차트
    fig_pie, ax_pie = plt.subplots(figsize=(6, 5))
    cat_vals = {}
    if mode == "현재 평가금액 기준":
        for d in summary_df_data: cat_vals[d['분류']] = int(d['총평가금액'].replace(',', ''))
    else:
        for d in summary_df_data: cat_vals[d['분류']] = int(d['순원금'].replace(',', ''))
        
    if cat_vals:
        # pie 함수가 반환하는 wedges, texts, autotexts(퍼센트 텍스트)를 각각 변수로 받음
        wedges, texts, autotexts = ax_pie.pie(cat_vals.values(), labels=cat_vals.keys(), autopct='%1.1f%%', colors=plt.cm.Set3.colors, textprops={'color': TEXT_COLOR, 'fontsize': 10})
        
        # 내부 퍼센트 글자(autotexts)만 검정색 + 굵게 설정
        for autotext in autotexts:
            autotext.set_color('black')
            autotext.set_fontweight('bold')
            
        ax_pie.set_title("전체 자산 비중", color=TEXT_COLOR, pad=15, fontweight='bold')
        st.pyplot(fig_pie)
    
    st.markdown("<hr style='border: 1px solid #2C313C;'>", unsafe_allow_html=True)
    st.markdown("#### 🔍 계좌(분류)별 상세 자산 구성")
    
    # 2. 각 분류별 자산 구성 파이차트 (모바일 2열 배치)
    cols = st.columns(2)
    idx = 0
    
    # 📌 출력 순서 커스텀: 실물자산이 키움(ISA)보다 먼저 오도록 순서 지정
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
                
                wedges, texts, autotexts = ax_sub.pie(s_vals, labels=s_names, autopct='%1.1f%%', colors=plt.cm.tab20.colors, textprops={'color': TEXT_COLOR, 'fontsize': 9})
                
                # 내부 퍼센트 글자만 검정색 + 굵게 설정
                for autotext in autotexts:
                    autotext.set_color('black')
                    autotext.set_fontweight('bold')
                    
                ax_sub.set_title(f"[{cat}]", color=TEXT_COLOR, fontweight='bold')
                st.pyplot(fig_sub)
            idx += 1

# --- 탭 4: 손익 현황 (동일 종목 합산 처리 추가) ---
with tab4:
    # 차트 간격 조정을 위해 hspace 추가
    fig_bar, (ax1, ax2) = plt.subplots(2, 1, figsize=(7, 11))
    plt.subplots_adjust(hspace=0.4) 
    
    # 1. 분류별 손익
    cat_names = [d['분류'] for d in summary_df_data]
    cat_pls = [d['_raw_pl'] for d in summary_df_data]
    c_colors = [RED_COLOR if x >= 0 else BLUE_COLOR for x in cat_pls]
    if cat_names:
        bars1 = ax1.bar(cat_names, cat_pls, color=c_colors, width=0.5)
        ax1.set_title("계좌별 손익 현황 (만원)", color=TEXT_COLOR, pad=15, fontweight='bold')
        ax1.axhline(0, color=TEXT_COLOR, alpha=0.3)
        ax1.yaxis.set_major_formatter(FuncFormatter(format_manwon))
        for bar in bars1:
            h = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2, h, f"{int(h/10000)}만", ha='center', va='bottom' if h>0 else 'top', color=TEXT_COLOR, fontweight='bold', fontsize=9)
            
    # 2. 종목별 손익 (같은 자산명 끼리 손익 합산)
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
        ax2.set_title("종목별 합산 손익 현황 (만원)", color=TEXT_COLOR, pad=15, fontweight='bold')
        ax2.axhline(0, color=TEXT_COLOR, alpha=0.3)
        ax2.yaxis.set_major_formatter(FuncFormatter(format_manwon))
        for bar in bars2:
            h = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2, h, f"{int(h/10000)}만", ha='center', va='bottom' if h>0 else 'top', color=TEXT_COLOR, fontweight='bold', fontsize=9)
            
    st.pyplot(fig_bar)

with tab5:
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
                hist = yf.Ticker(yf_tkr).history(period=t_period)
                if not hist.empty:
                    fig_l, ax_l = plt.subplots(figsize=(8, 4))
                    dates, prices = hist.index, hist['Close']
                    c = RED_COLOR if prices.iloc[-1] >= prices.iloc[0] else BLUE_COLOR
                    ax_l.plot(dates, prices, color=c, linewidth=2)
                    ax_l.fill_between(dates, prices, min(prices)*0.99, color=c, alpha=0.1)
                    avg_p = float(asset_info.get('avg_price', 0))
                    if avg_p > 0: ax_l.axhline(avg_p, color='#FBBF24', linestyle='--', linewidth=1.5, label='내 평단가')
                    ax_l.legend(frameon=False)
                    ax_l.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d' if t_period in ["1mo","3mo"] else '%Y-%m'))
                    ax_l.yaxis.set_major_formatter(FuncFormatter(format_currency))
                    ax_l.set_title(f"{t_asset} 시세 추이", color=TEXT_COLOR, fontweight='bold', pad=10)
                    st.pyplot(fig_l)

with tab6:
    if st.session_state.history:
        hist_df = pd.DataFrame(reversed(st.session_state.history))
        st.dataframe(hist_df, use_container_width=True)
    else:
        st.info("아직 거래 내역이 없습니다.")