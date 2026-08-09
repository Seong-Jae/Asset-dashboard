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

# --- 한글 폰트 설정 (Streamlit Cloud 리눅스 환경 대응) ---
if platform.system() == 'Linux':
    plt.rcParams['font.family'] = 'NanumGothic'
elif platform.system() == 'Darwin':
    plt.rcParams['font.family'] = 'AppleGothic'
else:
    plt.rcParams['font.family'] = 'Malgun Gothic'

plt.rcParams['axes.unicode_minus'] = False # 마이너스 기호 깨짐 방지

# --- 기본 설정 ---
st.set_page_config(page_title="통합 자산 대시보드", layout="wide", initial_sidebar_state="expanded")

DATA_FILE = "my_assets_v26.json"
HISTORY_FILE = "trade_history_v26.json"

DEFAULT_ASSETS = [
    {"category": "키움(일반)", "name": "한컴위드", "type": "stock", "qty": 15678, "ticker": "054920", "unit": "주", "avg_price": 3515},
    {"category": "키움(ISA)", "name": "한컴위드", "type": "stock", "qty": 1804, "ticker": "054920", "unit": "주", "avg_price": 5209},
    {"category": "실물자산", "name": "금", "type": "gold", "qty": 37.50, "ticker": "GC=F", "unit": "g", "avg_price": 239776},
    {"category": "외환", "name": "달러", "type": "fx", "qty": 354.42, "ticker": "USD", "unit": "USD", "avg_price": 1410.74}
]

# --- 차트 다크 테마 색상 설정 ---
BG_COLOR, PANEL_COLOR, TEXT_COLOR, SUB_TEXT_COLOR = "#0E1117", "#262730", "#FAFAFA", "#94A3B8"
RED_COLOR, BLUE_COLOR = "#EF4444", "#3B82F6"

plt.style.use('dark_background')
plt.rcParams.update({
    "figure.facecolor": BG_COLOR, "axes.facecolor": BG_COLOR, "savefig.facecolor": BG_COLOR,
    "text.color": TEXT_COLOR, "axes.labelcolor": TEXT_COLOR,
    "xtick.color": SUB_TEXT_COLOR, "ytick.color": SUB_TEXT_COLOR, "grid.color": "#334155"
})

def format_manwon(x, pos): return f"{int(x / 10000):,}"
def format_currency(x, pos): return f"{int(x):,}"

# --- 데이터 로드 및 저장 함수 ---
def load_data():
    assets, principals, deposits, history = DEFAULT_ASSETS.copy(), {}, {}, []
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    assets = data.get("assets", DEFAULT_ASSETS.copy())
                    principals = data.get("principals", {})
                    deposits = data.get("deposits", {})
                else: assets = data
        except: pass
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except: pass
    return assets, principals, deposits, history

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"assets": st.session_state.assets, "principals": st.session_state.principals, "deposits": st.session_state.deposits}, f, ensure_ascii=False, indent=4)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.history, f, ensure_ascii=False, indent=4)

# --- 시세 조회 함수 ---
def get_korean_stock_price(code):
    try:
        url = f"https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{code}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        data = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
        return int(data['result']['areas'][0]['datas'][0]['nv'])
    except:
        try:
            hist = yf.Ticker(f"{code}.KQ" if code in ["054920", "030520"] else f"{code}.KS").history(period="1d")
            if not hist.empty: return int(hist['Close'].iloc[-1])
        except: pass
    return 0

@st.cache_data(ttl=60)
def fetch_all_prices(assets):
    prices = {}
    usd_krw = yf.Ticker("KRW=X").history(period="5d")['Close'].iloc[-1] if not yf.Ticker("KRW=X").history(period="5d").empty else 1400
    for item in assets:
        p = 0
        t = item["type"]
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

# --- Session State 초기화 ---
if 'assets' not in st.session_state:
    st.session_state.assets, st.session_state.principals, st.session_state.deposits, st.session_state.history = load_data()

# 실시간 시세 반영
current_prices = fetch_all_prices(st.session_state.assets)

# --- 계산 로직 ---
total_valuation, global_principal = 0, 0
cat_summary = {}

# 자산 목록 처리
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

# 예수금 추가
for cat, dep in st.session_state.deposits.items():
    if cat != "외환" and dep > 0:
        asset_df_data.append({"ID": "-", "분류": cat, "자산명": "예수금(현금)", "수량": "-", "매수단가": "-", "현재가": "-", "평가손익": "-", "수익률(%)": "-", "평가금액": f"{int(dep):,}", "_raw_pl": 0, "_raw_val": dep, "_type": "cash"})

# 요약 데이터 처리
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

# --- UI 레이아웃 시작 ---
col1, col2 = st.columns([1, 1])
with col1:
    st.markdown(f"## 💰 총 평가금액: **{int(total_valuation):,} 원**")
with col2:
    color = RED_COLOR if tot_pl > 0 else BLUE_COLOR if tot_pl < 0 else SUB_TEXT_COLOR
    sign = "+" if tot_pl > 0 else ""
    st.markdown(f"<h3 style='color:{color}; text-align:right;'>총 손익: {sign}{int(tot_pl):,} 원 ({sign}{tot_pct:.2f}%)</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{SUB_TEXT_COLOR}; text-align:right;'>총 원금: {int(global_principal):,} 원</p>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📝 보유 자산", "📋 분류별 요약", "📊 비중 분석", "📉 손익 현황", "📈 차트", "📜 히스토리"])

# --- 탭 1: 보유 자산 ---
with tab1:
    st.dataframe(pd.DataFrame(asset_df_data).drop(columns=['_raw_pl', '_raw_val', '_type', 'ID']), use_container_width=True)
    
    with st.expander("➕ 매수 / 매도 / 신규 등록 (클릭하여 펼치기)"):
        action = st.radio("작업 선택", ["매수", "매도", "신규 등록"])
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

# --- 탭 2: 분류별 요약 (입출금) ---
with tab2:
    st.dataframe(pd.DataFrame(summary_df_data).drop(columns=['_raw_pl']), use_container_width=True)
    with st.expander("💸 입/출금 및 예수금 직접 설정"):
        cats = [c["분류"] for c in summary_df_data]
        if cats:
            target_cat = st.selectbox("분류 선택", cats)
            col_m1, col_m2 = st.columns(2)
            dw_amt = col_m1.number_input("입/출금 금액", min_value=0.0, step=10000.0)
            dw_type = col_m2.radio("작업", ["입금(+)", "출금(-)"])
            
            if st.button("입/출금 적용"):
                if dw_amt > 0:
                    curr_prin = st.session_state.principals.get(target_cat, cat_summary[target_cat]["auto_prin"])
                    curr_dep = st.session_state.deposits.get(target_cat, 0.0)
                    if dw_type == "입금(+)":
                        st.session_state.principals[target_cat] = curr_prin + dw_amt
                        st.session_state.deposits[target_cat] = curr_dep + dw_amt
                    else:
                        if curr_dep < dw_amt: st.error("예수금이 부족합니다.")
                        else:
                            st.session_state.principals[target_cat] = curr_prin - dw_amt
                            st.session_state.deposits[target_cat] = curr_dep - dw_amt
                    save_data()
                    st.rerun()

# --- 탭 3 & 4: 차트 (Matplotlib) ---
with tab3:
    mode = st.radio("기준", ["현재 평가금액", "총 원금"], horizontal=True)
    fig_pie, ax_pie = plt.subplots(figsize=(6,6))
    
    cat_vals = {}
    if mode == "현재 평가금액":
        for d in summary_df_data: cat_vals[d['분류']] = int(d['총평가금액'].replace(',', ''))
    else:
        for d in summary_df_data: cat_vals[d['분류']] = int(d['순원금'].replace(',', ''))
        
    if cat_vals:
        ax_pie.pie(cat_vals.values(), labels=cat_vals.keys(), autopct='%1.1f%%', colors=plt.cm.Set3.colors, textprops={'color': TEXT_COLOR})
        st.pyplot(fig_pie)

with tab4:
    fig_bar, (ax1, ax2) = plt.subplots(2, 1, figsize=(7, 10))
    
    cat_names = [d['분류'] for d in summary_df_data]
    cat_pls = [d['_raw_pl'] for d in summary_df_data]
    c_colors = [RED_COLOR if x >= 0 else BLUE_COLOR for x in cat_pls]
    if cat_names:
        bars1 = ax1.bar(cat_names, cat_pls, color=c_colors, width=0.5)
        ax1.set_title("분류별 손익 (만원)", color=TEXT_COLOR)
        ax1.axhline(0, color=TEXT_COLOR, alpha=0.5)
        ax1.yaxis.set_major_formatter(FuncFormatter(format_manwon))
        for bar in bars1:
            h = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2, h, f"{int(h/10000)}만", ha='center', va='bottom' if h>0 else 'top', color=TEXT_COLOR)
            
    items = [d for d in asset_df_data if d['_type'] != 'cash' and d['_raw_pl'] != 0]
    if items:
        i_names = [d['자산명'] for d in items]
        i_pls = [d['_raw_pl'] for d in items]
        i_colors = [RED_COLOR if x >= 0 else BLUE_COLOR for x in i_pls]
        bars2 = ax2.bar(i_names, i_pls, color=i_colors, width=0.5)
        ax2.set_title("종목별 손익 (만원)", color=TEXT_COLOR)
        ax2.axhline(0, color=TEXT_COLOR, alpha=0.5)
        ax2.yaxis.set_major_formatter(FuncFormatter(format_manwon))
        for bar in bars2:
            h = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2, h, f"{int(h/10000)}만", ha='center', va='bottom' if h>0 else 'top', color=TEXT_COLOR)
            
    st.pyplot(fig_bar)

# --- 탭 5: 가격 추이 차트 ---
with tab5:
    col_t1, col_t2 = st.columns(2)
    t_asset = col_t1.selectbox("자산 선택", [a['name'] for a in st.session_state.assets if a['type'] != 'cash'])
    t_period = col_t2.selectbox("기간", ["1mo", "3mo", "6mo", "1y", "3y", "5y"], index=1)
    
    if st.button("차트 그리기", use_container_width=True):
        asset_info = next((a for a in st.session_state.assets if a['name'] == t_asset), None)
        if asset_info:
            tkr = asset_info['ticker']
            t_type = asset_info['type']
            yf_tkr = f"{tkr}.KQ" if t_type=="stock" and tkr in ["054920", "030520"] else f"{tkr}.KS" if t_type=="stock" else tkr
            if t_type == "fx": yf_tkr = "KRW=X" if tkr.upper()=="USD" else f"{tkr.upper()}KRW=X"
            
            hist = yf.Ticker(yf_tkr).history(period=t_period)
            if not hist.empty:
                fig_l, ax_l = plt.subplots(figsize=(8, 4))
                dates, prices = hist.index, hist['Close']
                c = RED_COLOR if prices.iloc[-1] >= prices.iloc[0] else BLUE_COLOR
                ax_l.plot(dates, prices, color=c)
                ax_l.fill_between(dates, prices, min(prices)*0.99, color=c, alpha=0.1)
                avg_p = float(asset_info.get('avg_price', 0))
                if avg_p > 0: ax_l.axhline(avg_p, color='#FBBF24', linestyle='--', label='평단가')
                ax_l.legend()
                ax_l.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d' if t_period in ["1mo","3mo"] else '%Y-%m'))
                ax_l.yaxis.set_major_formatter(FuncFormatter(format_currency))
                st.pyplot(fig_l)

# --- 탭 6: 히스토리 ---
with tab6:
    if st.session_state.history:
        hist_df = pd.DataFrame(reversed(st.session_state.history))
        st.dataframe(hist_df, use_container_width=True)
    else:
        st.info("거래 기록이 없습니다.")