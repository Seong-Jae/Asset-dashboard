import os
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox, Toplevel
import urllib.request
import yfinance as yf
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
import platform
import math
from datetime import datetime

BG_COLOR = "#0F172A"
PANEL_COLOR = "#1E293B"
TEXT_COLOR = "#F8FAFC"
SUB_TEXT_COLOR = "#94A3B8"
ACCENT_COLOR = "#3B82F6"
RED_COLOR = "#EF4444"
BLUE_COLOR = "#3B82F6"
BORDER_COLOR = "#334155"

plt.style.use('dark_background')
plt.rcParams.update({
    "figure.facecolor": PANEL_COLOR,
    "axes.facecolor": PANEL_COLOR,
    "savefig.facecolor": PANEL_COLOR,
    "text.color": TEXT_COLOR,
    "axes.labelcolor": TEXT_COLOR,
    "xtick.color": SUB_TEXT_COLOR,
    "ytick.color": SUB_TEXT_COLOR,
    "grid.color": BORDER_COLOR,
})
if platform.system() == 'Darwin':
    plt.rc('font', family='AppleGothic')
else:
    plt.rc('font', family='Malgun Gothic')
plt.rcParams['axes.unicode_minus'] = False

DATA_FILE = "my_assets_v26.json"
HISTORY_FILE = "trade_history_v26.json"

DEFAULT_ASSETS = [
    {"category": "키움(일반)", "name": "한컴위드", "type": "stock", "qty": 15678, "ticker": "054920", "unit": "주", "avg_price": 3515},
    {"category": "키움(ISA)", "name": "한컴위드", "type": "stock", "qty": 1804, "ticker": "054920", "unit": "주", "avg_price": 5209},
    {"category": "키움(ISA)", "name": "한컴", "type": "stock", "qty": 59, "ticker": "030520", "unit": "주", "avg_price": 16808},
    {"category": "실물자산", "name": "금", "type": "gold", "qty": 37.50, "ticker": "GC=F", "unit": "g", "avg_price": 239776},
    {"category": "실물자산", "name": "은", "type": "silver", "qty": 4665, "ticker": "SI=F", "unit": "g", "avg_price": 4735},
    {"category": "외환", "name": "달러", "type": "fx", "qty": 354.42, "ticker": "USD", "unit": "USD", "avg_price": 1410.74},
    {"category": "외환", "name": "엔화", "type": "fx", "qty": 0, "ticker": "JPY", "unit": "JPY", "avg_price": 9.00}
]

def get_korean_stock_price(code):
    try:
        url = f"https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{code}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req)
        data = json.loads(response.read().decode('utf-8'))
        price = data['result']['areas'][0]['datas'][0]['nv']
        return int(price)
    except Exception:
        try:
            ticker = f"{code}.KQ" if code in ["054920", "030520"] else f"{code}.KS"
            hist = yf.Ticker(ticker).history(period="1d")
            if not hist.empty: return int(hist['Close'].iloc[-1])
        except: pass
    return 0

def format_manwon(x, pos):
    return f"{int(x / 10000):,}"

def format_currency(x, pos): return f"{int(x):,}"

class AssetApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("통합 자산 대시보드 (Pro V26 - 예수금 목록 & 비중 차트 분리)")
        self.geometry("1650x850") 
        self.configure(bg=BG_COLOR)
        
        self.assets, self.category_principals, self.category_deposits, self.history = self.load_data()
        self.current_values = {}
        self.current_invested = {}
        self.current_prices = {}
        self.category_summary_data = {}
        self.selected_period = "3mo"
        
        self.setup_styles()
        self.create_widgets()
        
        self.after(200, self.refresh_data)
        
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure("Treeview", background=PANEL_COLOR, foreground=TEXT_COLOR, 
                        fieldbackground=PANEL_COLOR, borderwidth=0, rowheight=35, font=('Malgun Gothic', 10))
        style.map("Treeview", background=[('selected', BORDER_COLOR)])
        
        style.configure("Treeview.Heading", background="#0F172A", foreground=SUB_TEXT_COLOR, 
                        font=('Malgun Gothic', 10, 'bold'), borderwidth=0, padding=10)
        style.map("Treeview.Heading", background=[('active', "#1E293B")])

        style.configure("TNotebook", background=BG_COLOR, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL_COLOR, foreground=TEXT_COLOR, 
                        font=('Malgun Gothic', 11, 'bold'), padding=[20, 10], borderwidth=0)
        style.map("TNotebook.Tab", background=[("selected", ACCENT_COLOR)], foreground=[("selected", "white")])
        
        style.configure("Vertical.TScrollbar", background="#334155", troughcolor=PANEL_COLOR, borderwidth=0, arrowcolor=TEXT_COLOR)
        style.configure("Horizontal.TScrollbar", background="#334155", troughcolor=PANEL_COLOR, borderwidth=0, arrowcolor=TEXT_COLOR)

    def load_data(self):
        assets = DEFAULT_ASSETS.copy()
        principals = {}
        deposits = {}
        history = []
        
        files_to_check = [DATA_FILE, "my_assets_v25.json", "my_assets_v24.json", "my_assets_v23.json"]
        for f_name in files_to_check:
            if os.path.exists(f_name):
                try:
                    with open(f_name, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            assets = data.get("assets", DEFAULT_ASSETS.copy())
                            principals = data.get("principals", {})
                            deposits = data.get("deposits", {})
                        else:
                            assets = data
                        for item in assets:
                            if "category" not in item: item["category"] = "기타"
                            if "avg_price" not in item: item["avg_price"] = 0.0
                        break
                except: pass
                
        history_files = [HISTORY_FILE, "trade_history_v25.json", "trade_history_v24.json"]
        for h_name in history_files:
            if os.path.exists(h_name):
                try:
                    with open(h_name, "r", encoding="utf-8") as f:
                        history = json.load(f)
                    break
                except: pass
            
        return assets, principals, deposits, history

    def save_data(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "assets": self.assets, 
                "principals": self.category_principals,
                "deposits": self.category_deposits
            }, f, ensure_ascii=False, indent=4)
            
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.history, f, ensure_ascii=False, indent=4)

    def create_widgets(self):
        header_frame = tk.Frame(self, bg=BG_COLOR)
        header_frame.pack(fill=tk.X, padx=20, pady=15)
        
        title_frame = tk.Frame(header_frame, bg=BG_COLOR)
        title_frame.pack(side=tk.LEFT)
        
        tk.Label(title_frame, text="내 자산 포트폴리오", font=("Malgun Gothic", 12), fg=SUB_TEXT_COLOR, bg=BG_COLOR).pack(anchor="w", pady=(0, 5))
        val_frame = tk.Frame(title_frame, bg=BG_COLOR)
        val_frame.pack(anchor="w")
        
        self.lbl_total = tk.Label(val_frame, text="데이터 불러오는 중...", font=("Malgun Gothic", 26, "bold"), fg=TEXT_COLOR, bg=BG_COLOR)
        self.lbl_total.pack(side=tk.LEFT)
        
        self.lbl_principal = tk.Label(val_frame, text="총 원금: 로딩 중...", font=("Malgun Gothic", 14), fg=SUB_TEXT_COLOR, bg=BG_COLOR)
        self.lbl_principal.pack(side=tk.LEFT, padx=(25, 10), pady=(10,0))
        
        self.lbl_total_pl = tk.Label(val_frame, text="", font=("Malgun Gothic", 14, "bold"), fg=SUB_TEXT_COLOR, bg=BG_COLOR)
        self.lbl_total_pl.pack(side=tk.LEFT, padx=5, pady=(10,0))
        
        self.btn_refresh = tk.Button(header_frame, text="🔄 실시간 갱신", command=self.refresh_data, 
                                     bg=ACCENT_COLOR, fg="white", font=("Malgun Gothic", 11, "bold"), 
                                     relief="flat", cursor="hand2", padx=20, pady=10, borderwidth=0)
        self.btn_refresh.pack(side=tk.RIGHT, pady=10)

        main_frame = tk.Frame(self, bg=BG_COLOR)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        # 좌측 패널 (자산 목록)
        left_panel = tk.Frame(main_frame, bg=PANEL_COLOR, bd=1, relief="flat")
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))
        
        list_header = tk.Frame(left_panel, bg=PANEL_COLOR)
        list_header.pack(fill=tk.X, padx=15, pady=15)
        tk.Label(list_header, text="보유 자산 목록", font=("Malgun Gothic", 14, "bold"), fg=TEXT_COLOR, bg=PANEL_COLOR).pack(side=tk.LEFT)

        tree_container = tk.Frame(left_panel, bg=PANEL_COLOR)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=2)
        
        vsb_main = ttk.Scrollbar(tree_container, orient="vertical")
        hsb_main = ttk.Scrollbar(tree_container, orient="horizontal")
        
        columns = ("category", "name", "qty", "avg_price", "price", "pl_amt", "pl_pct", "total")
        self.tree = ttk.Treeview(tree_container, columns=columns, show="headings", height=12,
                                 yscrollcommand=vsb_main.set, xscrollcommand=hsb_main.set)
        
        vsb_main.config(command=self.tree.yview)
        hsb_main.config(command=self.tree.xview)

        vsb_main.pack(side=tk.RIGHT, fill=tk.Y)
        hsb_main.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.tree.heading("category", text="분류")
        self.tree.heading("name", text="자산명")
        self.tree.heading("qty", text="수량")
        self.tree.heading("avg_price", text="매수단가")
        self.tree.heading("price", text="현재가")
        self.tree.heading("pl_amt", text="평가손익")
        self.tree.heading("pl_pct", text="수익률")
        self.tree.heading("total", text="평가금액")
        
        self.tree.column("category", width=90, minwidth=80, anchor="center")
        self.tree.column("name", width=140, minwidth=120, anchor="w")
        self.tree.column("qty", width=100, minwidth=90, anchor="e")
        self.tree.column("avg_price", width=100, minwidth=90, anchor="e")
        self.tree.column("price", width=100, minwidth=90, anchor="e")
        self.tree.column("pl_amt", width=120, minwidth=110, anchor="e")
        self.tree.column("pl_pct", width=90, minwidth=80, anchor="e")
        self.tree.column("total", width=130, minwidth=120, anchor="e")
        
        self.tree.bind("<<TreeviewSelect>>", self.on_asset_select)

        self.tree.tag_configure('profit', foreground=RED_COLOR)
        self.tree.tag_configure('loss', foreground=BLUE_COLOR)
        self.tree.tag_configure('neutral', foreground=TEXT_COLOR)

        btn_frame = tk.Frame(left_panel, bg=PANEL_COLOR)
        btn_frame.pack(fill=tk.X, padx=15, pady=15)
        btn_style = {"font": ("Malgun Gothic", 10, "bold"), "fg": "white", "relief": "flat", "padx": 12, "pady": 8, "cursor": "hand2", "borderwidth": 0}
        
        tk.Button(btn_frame, text="🔴 매수", command=self.buy_asset, bg=RED_COLOR, **btn_style).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(btn_frame, text="🔵 매도", command=self.sell_asset, bg=BLUE_COLOR, **btn_style).pack(side=tk.LEFT, padx=4)
        tk.Frame(btn_frame, bg=BORDER_COLOR, width=1).pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=5)
        tk.Button(btn_frame, text="➕ 등록", command=self.add_asset, bg="#475569", **btn_style).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="✏️ 수정", command=self.edit_asset, bg="#475569", **btn_style).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="🗑️ 삭제", command=self.delete_asset, bg="#475569", **btn_style).pack(side=tk.LEFT, padx=4)

        # 우측 패널 (탭 - Notebook)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 탭 1: 분류별 요약
        self.tab_summary = tk.Frame(self.notebook, bg=PANEL_COLOR)
        self.notebook.add(self.tab_summary, text=" 📋 분류별 요약 ")
        
        summary_top = tk.Frame(self.tab_summary, bg=PANEL_COLOR)
        summary_top.pack(fill=tk.X, padx=20, pady=(20, 10))
        tk.Label(summary_top, text="계좌 및 분류별 자산 요약", font=("Malgun Gothic", 14, "bold"), fg=TEXT_COLOR, bg=PANEL_COLOR).pack(side=tk.LEFT)
        
        sum_btn_frame = tk.Frame(summary_top, bg=PANEL_COLOR)
        sum_btn_frame.pack(side=tk.RIGHT)
        
        tk.Button(sum_btn_frame, text="💸 입/출금", command=self.deposit_withdraw_principal, bg="#10B981", fg="white", font=("Malgun Gothic", 10, "bold"), relief="flat", padx=12, pady=5, cursor="hand2").pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(sum_btn_frame, text="💵 예수금", command=self.edit_deposit, bg="#8B5CF6", fg="white", font=("Malgun Gothic", 10, "bold"), relief="flat", padx=12, pady=5, cursor="hand2").pack(side=tk.LEFT)
        
        sum_container = tk.Frame(self.tab_summary, bg=PANEL_COLOR)
        sum_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        vsb_sum = ttk.Scrollbar(sum_container, orient="vertical")
        hsb_sum = ttk.Scrollbar(sum_container, orient="horizontal")

        cols_sum = ("category", "principal", "deposit", "valuation", "total_val", "pl_amt", "pl_pct")
        self.tree_sum = ttk.Treeview(sum_container, columns=cols_sum, show="headings", height=15,
                                     yscrollcommand=vsb_sum.set, xscrollcommand=hsb_sum.set)
        
        vsb_sum.config(command=self.tree_sum.yview)
        hsb_sum.config(command=self.tree_sum.xview)
        
        vsb_sum.pack(side=tk.RIGHT, fill=tk.Y)
        hsb_sum.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree_sum.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.tree_sum.heading("category", text="계좌/분류")
        self.tree_sum.heading("principal", text="순원금 (입출금반영)")
        self.tree_sum.heading("deposit", text="예수금 (현금)")
        self.tree_sum.heading("valuation", text="주식등 평가금")
        self.tree_sum.heading("total_val", text="총 평가금액")
        self.tree_sum.heading("pl_amt", text="평가손익")
        self.tree_sum.heading("pl_pct", text="수익률")

        self.tree_sum.column("category", width=110, minwidth=90, anchor="center")
        self.tree_sum.column("principal", width=130, minwidth=110, anchor="e")
        self.tree_sum.column("deposit", width=110, minwidth=100, anchor="e")
        self.tree_sum.column("valuation", width=130, minwidth=110, anchor="e")
        self.tree_sum.column("total_val", width=130, minwidth=110, anchor="e")
        self.tree_sum.column("pl_amt", width=120, minwidth=100, anchor="e")
        self.tree_sum.column("pl_pct", width=90, minwidth=80, anchor="e")

        self.tree_sum.tag_configure('profit', foreground=RED_COLOR)
        self.tree_sum.tag_configure('loss', foreground=BLUE_COLOR)
        self.tree_sum.tag_configure('neutral', foreground=TEXT_COLOR)

        # 탭 2: 비중 분석 (원금 기준 vs 현재 가격 기준)
        self.tab_pie = tk.Frame(self.notebook, bg=PANEL_COLOR)
        self.notebook.add(self.tab_pie, text=" 📊 비중 분석 ")
        
        pie_top = tk.Frame(self.tab_pie, bg=PANEL_COLOR)
        pie_top.pack(fill=tk.X, padx=20, pady=(15, 5))
        tk.Label(pie_top, text="비중 분석 기준:", font=("Malgun Gothic", 10, "bold"), fg=TEXT_COLOR, bg=PANEL_COLOR).pack(side=tk.LEFT, padx=(0, 10))
        
        self.pie_mode_var = tk.StringVar(value="val")
        tk.Radiobutton(pie_top, text="현재 평가금액 기준", variable=self.pie_mode_var, value="val", 
                       command=self.draw_pie_charts, bg=PANEL_COLOR, fg=TEXT_COLOR, selectcolor=BG_COLOR, font=("Malgun Gothic", 9, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(pie_top, text="총 원금 기준", variable=self.pie_mode_var, value="prin", 
                       command=self.draw_pie_charts, bg=PANEL_COLOR, fg=TEXT_COLOR, selectcolor=BG_COLOR, font=("Malgun Gothic", 9, "bold")).pack(side=tk.LEFT, padx=5)
        
        self.fig_pie = Figure(figsize=(7, 8), dpi=100)
        self.fig_pie.patch.set_facecolor(PANEL_COLOR) 
        self.canvas_pie = FigureCanvasTkAgg(self.fig_pie, master=self.tab_pie)
        self.canvas_pie.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # 탭 3: 손익 현황
        self.tab_bar = tk.Frame(self.notebook, bg=PANEL_COLOR)
        self.notebook.add(self.tab_bar, text=" 📉 손익 현황 ")
        
        self.fig_bar = Figure(figsize=(6, 8), dpi=100)
        self.fig_bar.patch.set_facecolor(PANEL_COLOR)
        self.ax_bar_cat = self.fig_bar.add_subplot(211)   
        self.ax_bar_item = self.fig_bar.add_subplot(212) 
        self.fig_bar.subplots_adjust(hspace=0.45, left=0.18, right=0.95, top=0.9, bottom=0.15)
        self.canvas_bar = FigureCanvasTkAgg(self.fig_bar, master=self.tab_bar)
        self.canvas_bar.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 탭 4: 가격 추이 차트
        self.tab_trend = tk.Frame(self.notebook, bg=PANEL_COLOR)
        self.notebook.add(self.tab_trend, text=" 📈 가격 추이 차트 ")
        
        trend_top = tk.Frame(self.tab_trend, bg=PANEL_COLOR)
        trend_top.pack(fill=tk.X, padx=20, pady=(15, 5))
        tk.Label(trend_top, text="조회 기간 선택:", font=("Malgun Gothic", 10, "bold"), fg=TEXT_COLOR, bg=PANEL_COLOR).pack(side=tk.LEFT, padx=(0, 10))
        
        self.period_var = tk.StringVar(value="3mo")
        periods = [("1개월", "1mo"), ("3개월", "3mo"), ("6개월", "6mo"), ("1년", "1y"), ("3년", "3y"), ("5년", "5y")]
        for text, val in periods:
            rb = tk.Radiobutton(trend_top, text=text, variable=self.period_var, value=val, 
                                command=self.on_period_change, bg=PANEL_COLOR, fg=TEXT_COLOR, 
                                selectcolor=BG_COLOR, font=("Malgun Gothic", 9, "bold"))
            rb.pack(side=tk.LEFT, padx=3)

        self.fig_trend = Figure(figsize=(7, 7), dpi=100)
        self.fig_trend.patch.set_facecolor(PANEL_COLOR)
        self.ax_line = self.fig_trend.add_subplot(111)
        self.fig_trend.subplots_adjust(left=0.18, right=0.95, top=0.9, bottom=0.15)
        self.canvas_trend = FigureCanvasTkAgg(self.fig_trend, master=self.tab_trend)
        self.canvas_trend.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # 탭 5: 거래 히스토리
        self.tab_history = tk.Frame(self.notebook, bg=PANEL_COLOR)
        self.notebook.add(self.tab_history, text=" 📜 거래 히스토리 ")
        
        hist_top = tk.Frame(self.tab_history, bg=PANEL_COLOR)
        hist_top.pack(fill=tk.X, padx=20, pady=(20, 10))
        tk.Label(hist_top, text="매수 및 매도 거래 기록", font=("Malgun Gothic", 14, "bold"), fg=TEXT_COLOR, bg=PANEL_COLOR).pack(side=tk.LEFT)
        
        hist_btn_frame = tk.Frame(hist_top, bg=PANEL_COLOR)
        hist_btn_frame.pack(side=tk.RIGHT)
        tk.Button(hist_btn_frame, text="✏️ 기록 수정", command=self.edit_history, bg="#475569", fg="white", font=("Malgun Gothic", 10, "bold"), relief="flat", padx=12, pady=5, cursor="hand2").pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(hist_btn_frame, text="🗑️ 기록 삭제", command=self.delete_history, bg="#EF4444", fg="white", font=("Malgun Gothic", 10, "bold"), relief="flat", padx=12, pady=5, cursor="hand2").pack(side=tk.LEFT)

        hist_container = tk.Frame(self.tab_history, bg=PANEL_COLOR)
        hist_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        vsb_hist = ttk.Scrollbar(hist_container, orient="vertical")
        hsb_hist = ttk.Scrollbar(hist_container, orient="horizontal")

        cols_hist = ("date", "type", "category", "name", "qty", "price", "total_amt")
        self.tree_hist = ttk.Treeview(hist_container, columns=cols_hist, show="headings", height=15,
                                      yscrollcommand=vsb_hist.set, xscrollcommand=hsb_hist.set)
        
        vsb_hist.config(command=self.tree_hist.yview)
        hsb_hist.config(command=self.tree_hist.xview)
        
        vsb_hist.pack(side=tk.RIGHT, fill=tk.Y)
        hsb_hist.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree_hist.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.tree_hist.heading("date", text="거래일자")
        self.tree_hist.heading("type", text="구분")
        self.tree_hist.heading("category", text="계좌/분류")
        self.tree_hist.heading("name", text="자산명")
        self.tree_hist.heading("qty", text="거래수량")
        self.tree_hist.heading("price", text="체결단가")
        self.tree_hist.heading("total_amt", text="거래금액")

        self.tree_hist.column("date", width=100, minwidth=90, anchor="center")
        self.tree_hist.column("type", width=70, minwidth=60, anchor="center")
        self.tree_hist.column("category", width=110, minwidth=100, anchor="center")
        self.tree_hist.column("name", width=130, minwidth=110, anchor="w")
        self.tree_hist.column("qty", width=100, minwidth=90, anchor="e")
        self.tree_hist.column("price", width=110, minwidth=100, anchor="e")
        self.tree_hist.column("total_amt", width=130, minwidth=120, anchor="e")

        self.tree_hist.tag_configure('buy', foreground=RED_COLOR)
        self.tree_hist.tag_configure('sell', foreground=BLUE_COLOR)
        
        self.insert_initial_data()
        self.update_history_table()
        self.draw_empty_charts()

    def insert_initial_data(self):
        self.tree.delete(*self.tree.get_children())
        for idx, item in enumerate(self.assets):
            qty_str = f"{item['qty']:,.2f} {item['unit']}" if isinstance(item['qty'], float) and item['qty'] % 1 != 0 else f"{int(item['qty']):,} {item['unit']}"
            avg_p = float(item.get("avg_price", 0))
            if item["type"] == "fx" and avg_p > 0: avg_str = f"{avg_p:,.2f}"
            elif avg_p > 0: avg_str = f"{int(avg_p):,}"
            else: avg_str = "-"
            self.tree.insert("", "end", iid=str(idx), values=(item.get("category", "기타"), item["name"], qty_str, avg_str, "-", "-", "-", "-"))

    def update_history_table(self):
        self.tree_hist.delete(*self.tree_hist.get_children())
        for idx, h in enumerate(reversed(self.history)):
            t_type = h.get("type", "매수")
            tag = "buy" if t_type == "매수" else "sell"
            total_amt = float(h["qty"]) * float(h["price"])
            self.tree_hist.insert("", "end", iid=str(idx), values=(
                h.get("date", ""),
                t_type,
                h.get("category", ""),
                h.get("name", ""),
                f"{h['qty']:,} {h.get('unit', '')}",
                f"{h['price']:,.2f}" if h['price'] % 1 != 0 else f"{int(h['price']):,}",
                f"{int(total_amt):,}"
            ), tags=(tag,))

    def edit_history(self):
        selected = self.tree_hist.selection()
        if not selected: return messagebox.showwarning("선택 오류", "수정할 거래 기록을 선택해주세요.")
        
        rev_index = int(selected[0])
        actual_index = len(self.history) - 1 - rev_index
        h_item = self.history[actual_index]
        
        dialog = Toplevel(self)
        dialog.title("거래 기록 수정")
        dialog.geometry("380x320")
        dialog.configure(bg=BG_COLOR)
        
        tk.Label(dialog, text="거래 기록 수정", font=("Malgun Gothic", 12, "bold"), bg=BG_COLOR, fg=ACCENT_COLOR).pack(pady=15)
        
        tk.Label(dialog, text="거래일자 (YYYY-MM-DD):", bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w", padx=30)
        ent_date = tk.Entry(dialog, font=("Malgun Gothic", 10)); ent_date.pack(fill=tk.X, padx=30, pady=5)
        ent_date.insert(0, h_item.get("date", ""))
        
        tk.Label(dialog, text=f"수량 ({h_item.get('unit', '')}):", bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w", padx=30)
        ent_qty = tk.Entry(dialog, font=("Malgun Gothic", 10)); ent_qty.pack(fill=tk.X, padx=30, pady=5)
        ent_qty.insert(0, str(h_item.get("qty", "")))
        
        tk.Label(dialog, text="체결 단가 (원):", bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w", padx=30)
        ent_price = tk.Entry(dialog, font=("Malgun Gothic", 10)); ent_price.pack(fill=tk.X, padx=30, pady=5)
        ent_price.insert(0, str(h_item.get("price", "")))
        
        def save_edit():
            try:
                new_date = ent_date.get().strip()
                new_qty = float(ent_qty.get())
                new_price = float(ent_price.get())
                if new_qty <= 0 or new_price < 0 or not new_date: raise ValueError
                
                self.history[actual_index]["date"] = new_date
                self.history[actual_index]["qty"] = new_qty
                self.history[actual_index]["price"] = new_price
                
                self.save_data()
                self.update_history_table()
                messagebox.showinfo("수정 완료", "거래 기록이 수정되었습니다.")
                dialog.destroy()
            except ValueError: messagebox.showerror("입력 오류", "정상적인 값을 입력해주세요.")

        tk.Button(dialog, text="수정 반영", command=save_edit, bg=ACCENT_COLOR, fg="white", font=("Malgun Gothic", 10, "bold"), relief="flat", padx=15, pady=5).pack(pady=15)

    def delete_history(self):
        selected = self.tree_hist.selection()
        if not selected: return messagebox.showwarning("선택 오류", "삭제할 거래 기록을 선택해주세요.")
        
        if messagebox.askyesno("확인", "선택한 거래 기록을 삭제하시겠습니까?"):
            rev_index = int(selected[0])
            actual_index = len(self.history) - 1 - rev_index
            del self.history[actual_index]
            self.save_data()
            self.update_history_table()
            messagebox.showinfo("삭제 완료", "거래 기록이 삭제되었습니다.")

    def draw_empty_charts(self):
        self.fig_pie.clear()
        ax = self.fig_pie.add_subplot(111)
        ax.set_facecolor(PANEL_COLOR)
        ax.text(0.5, 0.5, "데이터를 갱신해주세요", ha='center', va='center', color=SUB_TEXT_COLOR)
        ax.axis('off')
        self.canvas_pie.draw()
        
        for ax in [self.ax_bar_cat, self.ax_bar_item]:
            ax.clear(); ax.axis('off')
        self.ax_bar_cat.text(0.5, 0.5, "갱신 후 손익 현황이 표시됩니다", ha='center', va='center', color=SUB_TEXT_COLOR)
        self.canvas_bar.draw()
        
        self.ax_line.clear(); self.ax_line.axis('off')
        self.ax_line.text(0.5, 0.5, "좌측 자산 선택 시 추세선이 표시됩니다", ha='center', va='center', color=SUB_TEXT_COLOR)
        self.canvas_trend.draw()

    def draw_pie_charts(self):
        self.fig_pie.clear()
        mode = self.pie_mode_var.get()
        cat_totals = {}
        item_totals_by_cat = {}
        
        if mode == "val":
            for item in self.assets:
                cat = item.get("category", "기타")
                val = self.current_values.get(f"tot_{item['name']}_{item['category']}", 0)
                if val > 0:
                    cat_totals[cat] = cat_totals.get(cat, 0) + val
                    if cat not in item_totals_by_cat: item_totals_by_cat[cat] = {}
                    item_totals_by_cat[cat][item['name']] = item_totals_by_cat[cat].get(item['name'], 0) + val
                    
            for cat, dep in self.category_deposits.items():
                if dep > 0:
                    cat_totals[cat] = cat_totals.get(cat, 0) + dep
                    if cat not in item_totals_by_cat: item_totals_by_cat[cat] = {}
                    item_totals_by_cat[cat]["예수금(현금)"] = item_totals_by_cat[cat].get("예수금(현금)", 0) + dep
            title_suffix = " (현재 평가금액 기준)"
        else:
            for cat, data in self.category_summary_data.items():
                prin = data.get("principal", 0)
                if prin > 0:
                    cat_totals[cat] = prin
                    
            for item in self.assets:
                cat = item.get("category", "기타")
                inv = self.current_invested.get(f"{item['name']}_{item['category']}", 0)
                if inv > 0:
                    if cat not in item_totals_by_cat: item_totals_by_cat[cat] = {}
                    item_totals_by_cat[cat][item['name']] = item_totals_by_cat[cat].get(item['name'], 0) + inv
                    
            for cat, dep in self.category_deposits.items():
                if dep > 0:
                    if cat not in item_totals_by_cat: item_totals_by_cat[cat] = {}
                    item_totals_by_cat[cat]["예수금(현금)"] = item_totals_by_cat[cat].get("예수금(현금)", 0) + dep
            title_suffix = " (총 원금 기준)"

        if not cat_totals:
            ax = self.fig_pie.add_subplot(111)
            ax.set_facecolor(PANEL_COLOR)
            ax.text(0.5, 0.5, "데이터 없음", ha='center', va='center', color=SUB_TEXT_COLOR)
            ax.axis('off')
            self.canvas_pie.draw()
            return
            
        categories = list(cat_totals.keys())
        N = len(categories) + 1 
        ncols = 2 if N > 1 else 1
        nrows = (N + ncols - 1) // ncols
        
        self.fig_pie.subplots_adjust(hspace=0.4, wspace=0.1, top=0.9, bottom=0.05)
        
        ax_main = self.fig_pie.add_subplot(nrows, ncols, 1)
        ax_main.set_facecolor(PANEL_COLOR)
        colors_main = ['#3B82F6', '#10B981', '#F59E0B', '#8B5CF6', '#EC4899', '#14B8A6', '#F43F5E', '#0EA5E9']
        ax_main.pie(cat_totals.values(), labels=cat_totals.keys(), autopct='%1.1f%%', 
                    startangle=140, colors=colors_main, textprops={'color': TEXT_COLOR, 'fontsize': 9},
                    wedgeprops={'edgecolor': PANEL_COLOR, 'linewidth': 1})
        ax_main.set_title(f"전체 계좌/분류 비중{title_suffix}", color=TEXT_COLOR, fontweight="bold", pad=10, fontsize=11)
        
        colors_sub = plt.cm.tab20.colors
        for i, cat in enumerate(categories):
            ax = self.fig_pie.add_subplot(nrows, ncols, i + 2)
            ax.set_facecolor(PANEL_COLOR)
            items = item_totals_by_cat.get(cat, {})
            if items:
                ax.pie(items.values(), labels=items.keys(), autopct='%1.1f%%', 
                       startangle=140, colors=colors_sub[i*2::3], textprops={'color': TEXT_COLOR, 'fontsize': 8},
                       wedgeprops={'edgecolor': PANEL_COLOR, 'linewidth': 1})
            ax.set_title(f"[{cat}] 구성", color=TEXT_COLOR, fontweight="bold", pad=10, fontsize=10)

        self.canvas_pie.draw()

    def draw_bar_charts(self):
        self.ax_bar_cat.clear()
        cat_names = []; cat_pls = []; cat_colors = []
        for cat, data in self.category_summary_data.items():
            p_amt = data["p_amt"]
            cat_names.append(cat)
            cat_pls.append(p_amt)
            cat_colors.append(RED_COLOR if p_amt >= 0 else BLUE_COLOR)

        if cat_names:
            self.ax_bar_cat.axis('on')
            bars_cat = self.ax_bar_cat.bar(cat_names, cat_pls, color=cat_colors, width=0.4)
            self.ax_bar_cat.set_title("계좌(분류)별 원금 대비 손익 현황 (만원)", color=TEXT_COLOR, fontweight="bold", pad=12, fontsize=11)
            
            max_v = max(cat_pls) if cat_pls else 0
            min_v = min(cat_pls) if cat_pls else 0
            limit_span = max(abs(max_v), abs(min_v)) * 1.45 if max(abs(max_v), abs(min_v)) > 0 else 100000
            self.ax_bar_cat.set_ylim(-limit_span, limit_span)

            self.ax_bar_cat.axhline(y=0, color=TEXT_COLOR, linewidth=1, alpha=0.5)
            self.ax_bar_cat.grid(True, axis='y', linestyle='--', alpha=0.1)
            
            self.ax_bar_cat.yaxis.set_major_formatter(FuncFormatter(format_manwon))
            self.ax_bar_cat.tick_params(axis='x', colors=TEXT_COLOR, rotation=10, labelsize=9)
            self.ax_bar_cat.tick_params(axis='y', colors=SUB_TEXT_COLOR)
            for spine in self.ax_bar_cat.spines.values(): spine.set_color(BORDER_COLOR)

            for bar in bars_cat:
                height = bar.get_height()
                manwon_val = int(height / 10000)
                va_pos = 'bottom' if height >= 0 else 'top'
                offset = 4 if height >= 0 else -14
                self.ax_bar_cat.annotate(f'{manwon_val:,}만',
                                         xy=(bar.get_x() + bar.get_width() / 2, height),
                                         xytext=(0, offset), textcoords="offset points",
                                         ha='center', va=va_pos, fontsize=8, color=TEXT_COLOR, fontweight='bold')
        else:
            self.ax_bar_cat.axis('off')
            self.ax_bar_cat.text(0.5, 0.5, "분류별 손익 데이터 없음", ha='center', va='center', color=SUB_TEXT_COLOR)

        self.ax_bar_item.clear()
        names = []; pls = []; colors = []
        for item in self.assets:
            if item["type"] == "cash" or item.get("avg_price", 0) <= 0: continue
            pl = self.current_values.get(f"pl_amt_{item['name']}_{item['category']}", 0)
            if pl != 0:
                names.append(f"{item['name']}\n({item['category']})")
                pls.append(pl)
                colors.append(RED_COLOR if pl > 0 else BLUE_COLOR)

        if names:
            self.ax_bar_item.axis('on')
            bars_item = self.ax_bar_item.bar(names, pls, color=colors, width=0.4)
            self.ax_bar_item.set_title("자산(종목)별 평가 손익 현황 (만원)", color=TEXT_COLOR, fontweight="bold", pad=12, fontsize=11)
            
            max_v = max(pls) if pls else 0
            min_v = min(pls) if pls else 0
            limit_span = max(abs(max_v), abs(min_v)) * 1.45 if max(abs(max_v), abs(min_v)) > 0 else 100000
            self.ax_bar_item.set_ylim(-limit_span, limit_span)

            self.ax_bar_item.axhline(y=0, color=TEXT_COLOR, linewidth=1, alpha=0.5)
            self.ax_bar_item.grid(True, axis='y', linestyle='--', alpha=0.1)
            
            self.ax_bar_item.yaxis.set_major_formatter(FuncFormatter(format_manwon))
            self.ax_bar_item.tick_params(axis='x', colors=TEXT_COLOR, rotation=20, labelsize=8)
            self.ax_bar_item.tick_params(axis='y', colors=SUB_TEXT_COLOR)
            for spine in self.ax_bar_item.spines.values(): spine.set_color(BORDER_COLOR)

            for bar in bars_item:
                height = bar.get_height()
                manwon_val = int(height / 10000)
                va_pos = 'bottom' if height >= 0 else 'top'
                offset = 4 if height >= 0 else -14
                self.ax_bar_item.annotate(f'{manwon_val:,}만',
                                          xy=(bar.get_x() + bar.get_width() / 2, height),
                                          xytext=(0, offset), textcoords="offset points",
                                          ha='center', va=va_pos, fontsize=8, color=TEXT_COLOR, fontweight='bold')
        else:
            self.ax_bar_item.axis('off')
            self.ax_bar_item.text(0.5, 0.5, "종목별 손익 데이터 없음", ha='center', va='center', color=SUB_TEXT_COLOR)
            
        self.canvas_bar.draw()

    def on_asset_select(self, event):
        selected = self.tree.selection()
        if not selected: return
        if str(selected[0]).startswith("dep_"): return
        item = self.assets[int(selected[0])]
        self.fetch_trend_data(item)

    def on_period_change(self):
        selected = self.tree.selection()
        if selected and not str(selected[0]).startswith("dep_"):
            item = self.assets[int(selected[0])]
            self.fetch_trend_data(item)

    def fetch_trend_data(self, item):
        self.ax_line.clear()
        self.ax_line.axis('off')
        self.ax_line.text(0.5, 0.5, f"[{item['name']}] 추세선 로딩 중...", ha='center', va='center', color=SUB_TEXT_COLOR)
        self.canvas_trend.draw()
        
        period = self.period_var.get()
        
        def task():
            try:
                t_type = item["type"]; ticker = item["ticker"]
                dates, prices = None, None
                
                if t_type == "stock":
                    yf_ticker = f"{ticker}.KQ" if ticker in ["054920", "030520"] else f"{ticker}.KS"
                    hist = yf.Ticker(yf_ticker).history(period=period)
                    if not hist.empty: dates, prices = hist.index, hist['Close']
                elif t_type in ["gold", "silver"]:
                    asset_hist = yf.Ticker(ticker).history(period=period)['Close']
                    krw_hist = yf.Ticker("KRW=X").history(period=period)['Close']
                    df = pd.DataFrame({"asset": asset_hist, "krw": krw_hist}).ffill().dropna()
                    if not df.empty:
                        dates, prices = df.index, (df["asset"] * df["krw"]) / 31.1034768
                elif t_type == "fx":
                    currency = ticker.upper()
                    yf_ticker = "KRW=X" if currency == "USD" else f"{currency}KRW=X"
                    hist = yf.Ticker(yf_ticker).history(period=period)
                    if not hist.empty: dates, prices = hist.index, hist['Close']
                elif t_type == "crypto":
                    hist = yf.Ticker(ticker).history(period=period)
                    if not hist.empty: dates, prices = hist.index, hist['Close']
                
                self.after(0, lambda: self.update_trend_chart(item["name"], dates, prices, item.get("avg_price", 0), period))
            except Exception:
                self.after(0, lambda: self.update_trend_chart(item["name"], None, None, error=True))
                
        threading.Thread(target=task, daemon=True).start()

    def update_trend_chart(self, name, dates, prices, avg_price=0, period="3mo", error=False):
        self.ax_line.clear()
        if error or dates is None or len(dates) == 0:
            self.ax_line.axis('off')
            self.ax_line.text(0.5, 0.5, f"[{name}]\n추세선 데이터 없음", ha='center', va='center', color=SUB_TEXT_COLOR)
        else:
            self.ax_line.axis('on')
            start_price = prices.iloc[0]
            end_price = prices.iloc[-1]
            chart_color = RED_COLOR if end_price >= start_price else BLUE_COLOR
            
            self.ax_line.plot(dates, prices, color=chart_color, linewidth=2)
            self.ax_line.fill_between(dates, prices, min(prices) * 0.99, color=chart_color, alpha=0.1)
            
            if avg_price > 0:
                self.ax_line.axhline(y=avg_price, color='#FBBF24', linestyle='--', linewidth=1.5, label=f'단가: {avg_price:,.2f}' if avg_price < 1000 else f'단가: {avg_price:,.0f}')
                self.ax_line.legend(loc='upper left', frameon=False, labelcolor=TEXT_COLOR)
            
            p_text = {"1mo": "1개월", "3mo": "3개월", "6mo": "6개월", "1y": "1년", "3y": "3년", "5y": "5년"}.get(period, "")
            self.ax_line.set_title(f"{name} (최근 {p_text} 단가 추이)", color=TEXT_COLOR, fontsize=12, pad=12, fontweight='bold')
            self.ax_line.grid(True, linestyle='--', alpha=0.1, color=TEXT_COLOR)
            
            date_format = '%m-%d' if period in ["1mo", "3mo"] else ('%Y-%m' if period in ["6mo", "1y"] else '%Y')
            self.ax_line.xaxis.set_major_formatter(mdates.DateFormatter(date_format))
            self.ax_line.yaxis.set_major_formatter(FuncFormatter(format_currency))
            self.ax_line.tick_params(colors=SUB_TEXT_COLOR, labelsize=9)
            for spine in self.ax_line.spines.values(): spine.set_color(BORDER_COLOR)
        self.canvas_trend.draw()

    def refresh_data(self):
        self.btn_refresh.config(state=tk.DISABLED, text="업데이트 중...", bg="#475569")
        threading.Thread(target=self.fetch_prices, daemon=True).start()

    def fetch_prices(self):
        try:
            usd_krw = yf.Ticker("KRW=X").history(period="5d")['Close'].iloc[-1]
            total_valuation = 0
            self.current_values = {}
            self.current_invested = {}
            cat_summary = {}
            
            for item in self.assets:
                cat = item.get("category", "기타")
                if cat not in cat_summary: 
                    cat_summary[cat] = {"stock_val": 0, "auto_prin": 0}

            for idx, item in enumerate(self.assets):
                price = 0
                t_type = item["type"]
                if t_type == "stock": price = get_korean_stock_price(item["ticker"])
                elif t_type in ["gold", "silver"]:
                    hist = yf.Ticker(item["ticker"]).history(period="5d")
                    if not hist.empty: price = (hist['Close'].iloc[-1] * usd_krw) / 31.1034768
                elif t_type == "fx":
                    curr = item["ticker"].upper()
                    ticker = "KRW=X" if curr == "USD" else f"{curr}KRW=X"
                    hist = yf.Ticker(ticker).history(period="5d")
                    if not hist.empty: price = hist['Close'].iloc[-1]
                elif t_type == "crypto":
                    hist = yf.Ticker(item["ticker"]).history(period="5d")
                    if not hist.empty: price = hist['Close'].iloc[-1]
                elif t_type == "cash": price = 1
                    
                self.current_prices[f"{item['category']}_{item['name']}"] = price
                qty = float(item["qty"])
                avg_p = float(item.get("avg_price", 0))
                total_val = price * qty
                total_valuation += total_val
                
                uid = f"{item['name']}_{item['category']}"
                self.current_values[f"tot_{uid}"] = total_val
                
                pl_amt = pl_pct = 0
                total_invested_auto = total_val if t_type == "cash" else avg_p * qty
                if avg_p > 0 and t_type != "cash":
                    pl_amt = total_val - total_invested_auto
                    pl_pct = (pl_amt / total_invested_auto) * 100
                
                self.current_values[f"pl_amt_{uid}"] = pl_amt
                self.current_invested[uid] = total_invested_auto
                
                cat = item.get("category", "기타")
                cat_summary[cat]["stock_val"] += total_val
                cat_summary[cat]["auto_prin"] += total_invested_auto
                
                qty_str = f"{qty:,.4f} {item['unit']}" if t_type == "crypto" and qty % 1 != 0 else (f"{qty:,.2f} {item['unit']}" if qty % 1 != 0 else f"{int(qty):,} {item['unit']}")
                avg_str = f"{avg_p:,.2f}" if (t_type == "fx" or t_type == "crypto") and avg_p > 0 else f"{int(avg_p):,}" if avg_p > 0 else "-"
                price_str = f"{price:,.2f}" if (t_type == "fx" or t_type == "crypto") else f"{int(price):,}" if t_type != "cash" else "-"
                tot_str = f"{int(total_val):,}"
                
                tag = 'neutral'
                if avg_p > 0 and t_type != "cash" and qty > 0:
                    sign = "▲ " if pl_amt > 0 else "▼ " if pl_amt < 0 else ""
                    pl_amt_str = f"{sign}{abs(int(pl_amt)):,}"
                    pl_pct_str = f"{sign}{abs(pl_pct):.2f}%"
                    tag = 'profit' if pl_amt > 0 else 'loss' if pl_amt < 0 else 'neutral'
                else:
                    pl_amt_str, pl_pct_str = "-", "-"
                
                self.tree.item(str(idx), values=(cat, item["name"], qty_str, avg_str, price_str, pl_amt_str, pl_pct_str, tot_str), tags=(tag,))
                
            self.tree_sum.delete(*self.tree_sum.get_children())
            global_principal = 0
            global_total_valuation = 0
            self.category_summary_data = {}
            
            for cat, data in cat_summary.items():
                stock_val = data["stock_val"]
                auto_prin = data["auto_prin"]
                deposit = self.category_deposits.get(cat, 0.0)
                
                if cat in self.category_principals:
                    principal = self.category_principals[cat]
                else:
                    principal = auto_prin
                    
                global_principal += principal
                cat_total_val = stock_val + deposit
                global_total_valuation += cat_total_val
                
                p_amt = cat_total_val - principal
                p_pct = (p_amt / principal * 100) if principal > 0 else 0
                
                self.category_summary_data[cat] = {"principal": principal, "val": cat_total_val, "p_amt": p_amt}
                
                sign = "▲ " if p_amt > 0 else "▼ " if p_amt < 0 else ""
                p_amt_str = f"{sign}{abs(int(p_amt)):,}"
                p_pct_str = f"{sign}{abs(p_pct):.2f}%"
                tag = 'profit' if p_amt > 0 else 'loss' if p_amt < 0 else 'neutral'
                
                self.tree_sum.insert("", "end", values=(
                    cat, 
                    f"{int(principal):,}", 
                    f"{int(deposit):,}", 
                    f"{int(stock_val):,}", 
                    f"{int(cat_total_val):,}", 
                    p_amt_str, 
                    p_pct_str
                ), tags=(tag,))
                
            tot_pl = global_total_valuation - global_principal
            tot_pct = (tot_pl / global_principal * 100) if global_principal > 0 else 0
            
            self.lbl_total.config(text=f"{int(global_total_valuation):,} 원")
            self.lbl_principal.config(text=f"총 원금: {int(global_principal):,} 원")
            
            sign = "▲ " if tot_pl > 0 else "▼ " if tot_pl < 0 else ""
            color = RED_COLOR if tot_pl > 0 else BLUE_COLOR if tot_pl < 0 else SUB_TEXT_COLOR
            self.lbl_total_pl.config(text=f"{sign}{abs(int(tot_pl)):,} 원 ({sign}{abs(tot_pct):.2f}%)", fg=color)
            
            # 예수금 트리뷰 항목 업데이트 (외환 제외)
            for child in self.tree.get_children():
                if str(child).startswith("dep_"):
                    self.tree.delete(child)
                    
            for cat, dep in self.category_deposits.items():
                if cat != "외환" and dep > 0:
                    self.tree.insert("", "end", iid=f"dep_{cat}", values=(
                        cat, "예수금(현금)", f"{int(dep):,} 원", "-", "-", "-", "-", f"{int(dep):,}"
                    ), tags=('neutral',))
            
            self.after(0, self.draw_pie_charts)
            self.after(0, self.draw_bar_charts)
            if self.tree.selection() and not str(self.tree.selection()[0]).startswith("dep_"): 
                self.after(0, lambda: self.fetch_trend_data(self.assets[int(self.tree.selection()[0])]))
            
        except Exception as e:
            messagebox.showerror("오류 발생", f"데이터를 불러오는 중 문제가 발생했습니다.\n{e}")
        finally:
            self.btn_refresh.config(state=tk.NORMAL, text="🔄 실시간 갱신", bg=ACCENT_COLOR)

    def edit_principal(self):
        selected = self.tree_sum.selection()
        if not selected: return messagebox.showwarning("선택 오류", "원금을 수정할 계좌/분류를 선택해주세요.")
        cat = self.tree_sum.item(selected[0])['values'][0]
        
        dialog = Toplevel(self); dialog.title(f"[{cat}] 원금 설정"); dialog.geometry("380x250"); dialog.configure(bg=BG_COLOR)
        tk.Label(dialog, text=f"[{cat}] 순원금 설정", font=("Malgun Gothic", 12, "bold"), bg=BG_COLOR, fg=TEXT_COLOR).pack(pady=(20, 5))
        tk.Label(dialog, text="(입금, 출금을 반영한 실제 투입 원금을 입력하세요)", font=("Malgun Gothic", 9), bg=BG_COLOR, fg=SUB_TEXT_COLOR).pack(pady=(0, 10))
        ent_prin = tk.Entry(dialog, font=("Malgun Gothic", 12), justify="center"); ent_prin.pack(pady=10, ipady=5)
        if cat in self.category_principals: ent_prin.insert(0, str(int(self.category_principals[cat])))
            
        def save_prin():
            val = ent_prin.get().replace(",", "").replace(" ", "")
            if val == "":
                if cat in self.category_principals: del self.category_principals[cat]
            else:
                try: self.category_principals[cat] = float(val)
                except ValueError: return messagebox.showerror("입력 오류", "정상적인 숫자를 입력해주세요.")
            self.save_data(); self.btn_refresh.invoke(); dialog.destroy()
            
        tk.Button(dialog, text="저장", command=save_prin, bg=ACCENT_COLOR, fg="white", font=("Malgun Gothic", 11, "bold"), relief="flat", padx=20, pady=5).pack(pady=10)

    def edit_deposit(self):
        selected = self.tree_sum.selection()
        if not selected: return messagebox.showwarning("선택 오류", "예수금을 설정할 계좌/분류를 선택해주세요.")
        cat = self.tree_sum.item(selected[0])['values'][0]
        
        dialog = Toplevel(self); dialog.title(f"[{cat}] 예수금 설정"); dialog.geometry("380x250"); dialog.configure(bg=BG_COLOR)
        tk.Label(dialog, text=f"[{cat}] 예수금 (현금 잔고)", font=("Malgun Gothic", 12, "bold"), bg=BG_COLOR, fg=TEXT_COLOR).pack(pady=(20, 5))
        tk.Label(dialog, text="(계좌 내에 남아있는 현금 예수금을 입력하세요)", font=("Malgun Gothic", 9), bg=BG_COLOR, fg=SUB_TEXT_COLOR).pack(pady=(0, 10))
        ent_dep = tk.Entry(dialog, font=("Malgun Gothic", 12), justify="center"); ent_dep.pack(pady=10, ipady=5)
        if self.category_deposits.get(cat, 0) > 0: ent_dep.insert(0, str(int(self.category_deposits[cat])))
            
        def save_dep():
            val = ent_dep.get().replace(",", "").replace(" ", "")
            if val == "":
                if cat in self.category_deposits: del self.category_deposits[cat]
            else:
                try: self.category_deposits[cat] = float(val)
                except ValueError: return messagebox.showerror("입력 오류", "정상적인 숫자를 입력해주세요.")
            self.save_data(); self.btn_refresh.invoke(); dialog.destroy()
            
        tk.Button(dialog, text="저장", command=save_dep, bg="#8B5CF6", fg="white", font=("Malgun Gothic", 11, "bold"), relief="flat", padx=20, pady=5).pack(pady=10)

    def deposit_withdraw_principal(self):
        selected = self.tree_sum.selection()
        if not selected: return messagebox.showwarning("선택 오류", "입출금할 계좌/분류를 선택해주세요.")
        cat = self.tree_sum.item(selected[0])['values'][0]
        
        dialog = Toplevel(self); dialog.title(f"[{cat}] 입금 / 출금"); dialog.geometry("380x300"); dialog.configure(bg=BG_COLOR)
        tk.Label(dialog, text=f"[{cat}] 자금 입/출금", font=("Malgun Gothic", 12, "bold"), bg=BG_COLOR, fg=TEXT_COLOR).pack(pady=(15, 5))
        
        mode_var = tk.StringVar(value="deposit")
        radio_frame = tk.Frame(dialog, bg=BG_COLOR); radio_frame.pack(pady=5)
        tk.Radiobutton(radio_frame, text="입금 (+)", variable=mode_var, value="deposit", bg=BG_COLOR, fg=RED_COLOR, font=("Malgun Gothic", 10, "bold"), selectcolor=PANEL_COLOR).pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(radio_frame, text="출금 (-)", variable=mode_var, value="withdraw", bg=BG_COLOR, fg=BLUE_COLOR, font=("Malgun Gothic", 10, "bold"), selectcolor=PANEL_COLOR).pack(side=tk.LEFT, padx=10)
        
        tk.Label(dialog, text="금액 (원):", font=("Malgun Gothic", 10), bg=BG_COLOR, fg=SUB_TEXT_COLOR).pack(pady=(5, 0))
        ent_amount = tk.Entry(dialog, font=("Malgun Gothic", 12), justify="center"); ent_amount.pack(pady=5, ipady=3)
        
        withdraw_from_deposit = tk.BooleanVar(value=True)
        chk_dep = tk.Checkbutton(dialog, text="출금 시 예수금(현금) 잔고에서도 차감", variable=withdraw_from_deposit, bg=BG_COLOR, fg=TEXT_COLOR, selectcolor=PANEL_COLOR, font=("Malgun Gothic", 9))
        chk_dep.pack(pady=5)
        
        def apply_dw():
            try:
                amt = float(ent_amount.get().replace(",", "").replace(" ", ""))
                if amt <= 0: raise ValueError
                
                current_prin = self.category_principals.get(cat, None)
                if current_prin is None:
                    current_prin = sum(float(item.get("avg_price", 0)) * float(item["qty"]) for item in self.assets if item.get("category") == cat and item["type"] != "cash")
                
                if mode_var.get() == "deposit":
                    new_prin = current_prin + amt
                    curr_dep = self.category_deposits.get(cat, 0.0)
                    self.category_deposits[cat] = curr_dep + amt
                    msg = f"{int(amt):,} 원이 입금되었습니다. (순원금 및 예수금 반영)"
                else:
                    new_prin = current_prin - amt
                    if withdraw_from_deposit.get():
                        curr_dep = self.category_deposits.get(cat, 0.0)
                        if curr_dep < amt:
                            return messagebox.showerror("출금 불가", f"[{cat}] 계좌의 예수금 잔고({int(curr_dep):,}원)가 부족하여 출금할 수 없습니다.")
                        self.category_deposits[cat] = curr_dep - amt
                    msg = f"{int(amt):,} 원이 출금되었습니다."
                    
                self.category_principals[cat] = new_prin
                self.save_data(); self.btn_refresh.invoke()
                messagebox.showinfo("완료", msg)
                dialog.destroy()
            except ValueError:
                messagebox.showerror("입력 오류", "정상적인 숫자를 입력해주세요.")

        tk.Button(dialog, text="반영하기", command=apply_dw, bg="#10B981", fg="white", font=("Malgun Gothic", 11, "bold"), relief="flat", padx=20, pady=5, cursor="hand2").pack(pady=10)

    def buy_asset(self):
        selected = self.tree.selection()
        if not selected: return messagebox.showwarning("선택 오류", "매수할 자산을 선택해주세요.")
        if str(selected[0]).startswith("dep_"): return messagebox.showwarning("선택 오류", "예수금 항목은 우측 탭의 [예수금] 버튼을 이용해 관리해주세요.")
        
        index = int(selected[0])
        asset = self.assets[index]
        cat = asset['category']
        
        c_price = self.current_prices.get(f"{asset['category']}_{asset['name']}", "")
        if c_price != "": c_price = round(c_price, 2) if asset["type"] in ["fx", "crypto"] else int(c_price)
        
        dialog = Toplevel(self); dialog.title(f"[{asset['name']}] 추가 매수"); dialog.geometry("380x320"); dialog.configure(bg=BG_COLOR)
        tk.Label(dialog, text=f"[{asset['category']}] {asset['name']} 매수", font=("Malgun Gothic", 12, "bold"), bg=BG_COLOR, fg=ACCENT_COLOR).grid(row=0, column=0, columnspan=2, pady=15)
        
        tk.Label(dialog, text="거래일자 (YYYY-MM-DD):", bg=BG_COLOR, fg=TEXT_COLOR).grid(row=1, column=0, padx=15, pady=8, sticky="e")
        ent_date = tk.Entry(dialog, font=("Malgun Gothic", 10)); ent_date.grid(row=1, column=1, padx=10, pady=8)
        ent_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        tk.Label(dialog, text=f"매수 수량 ({asset['unit']}):", bg=BG_COLOR, fg=TEXT_COLOR).grid(row=2, column=0, padx=15, pady=8, sticky="e")
        ent_qty = tk.Entry(dialog, font=("Malgun Gothic", 11)); ent_qty.grid(row=2, column=1, padx=10, pady=8)
        
        tk.Label(dialog, text="체결 단가 (원):", bg=BG_COLOR, fg=TEXT_COLOR).grid(row=3, column=0, padx=15, pady=8, sticky="e")
        ent_price = tk.Entry(dialog, font=("Malgun Gothic", 11)); ent_price.grid(row=3, column=1, padx=10, pady=8)
        if c_price != "": ent_price.insert(0, str(c_price))

        def apply_buy():
            try:
                t_date = ent_date.get().strip()
                b_qty = float(ent_qty.get()); b_price = float(ent_price.get())
                if b_qty <= 0 or b_price < 0 or not t_date: raise ValueError
                
                total_cost = b_qty * b_price
                
                current_deposit = self.category_deposits.get(cat, 0.0)
                if current_deposit < total_cost:
                    return messagebox.showerror("예수금 부족", f"[{cat}] 계좌의 예수금({int(current_deposit):,}원)이 부족합니다.\n(필요 금액: {int(total_cost):,}원)")
                
                self.category_deposits[cat] = current_deposit - total_cost
                
                old_qty = float(asset['qty']); old_avg = float(asset.get('avg_price', 0))
                new_qty = old_qty + b_qty
                new_avg = ((old_qty * old_avg) + (b_qty * b_price)) / new_qty if new_qty > 0 else 0
                if new_qty.is_integer(): new_qty = int(new_qty)
                
                self.assets[index]['qty'] = new_qty
                self.assets[index]['avg_price'] = new_avg
                
                self.history.append({
                    "date": t_date, "type": "매수", "category": cat,
                    "name": asset['name'], "qty": b_qty, "price": b_price, "unit": asset['unit']
                })
                
                self.save_data()
                self.insert_initial_data()
                self.update_history_table()
                
                messagebox.showinfo("매수 완료", f"일자: {t_date}\n매수 수량: {b_qty} {asset['unit']}\n총 사용금액: {int(total_cost):,}원 예수금 차감됨\n변경된 평단가: {new_avg:,.2f} 원")
                dialog.destroy()
                self.btn_refresh.invoke()
            except ValueError: messagebox.showerror("입력 오류", "날짜를 정확히 입력하고 수량/단가에 숫자를 입력해주세요.")

        tk.Button(dialog, text="🔴 매수 반영 및 기록", command=apply_buy, bg=RED_COLOR, fg="white", font=("Malgun Gothic", 11, "bold"), relief="flat", padx=15, pady=5).grid(row=4, column=0, columnspan=2, pady=15)

    def sell_asset(self):
        selected = self.tree.selection()
        if not selected: return messagebox.showwarning("선택 오류", "매도할 자산을 선택해주세요.")
        if str(selected[0]).startswith("dep_"): return messagebox.showwarning("선택 오류", "예수금 항목은 우측 탭의 [예수금] 버튼을 이용해 관리해주세요.")
        
        index = int(selected[0])
        asset = self.assets[index]
        cat = asset['category']
        
        c_price = self.current_prices.get(f"{asset['category']}_{asset['name']}", "")
        if c_price != "": c_price = round(c_price, 2) if asset["type"] in ["fx", "crypto"] else int(c_price)
        
        dialog = Toplevel(self); dialog.title(f"[{asset['name']}] 매도"); dialog.geometry("380x300"); dialog.configure(bg=BG_COLOR)
        tk.Label(dialog, text=f"[{cat}] {asset['name']} 매도", font=("Malgun Gothic", 12, "bold"), bg=BG_COLOR, fg=ACCENT_COLOR).grid(row=0, column=0, columnspan=2, pady=15)
        
        tk.Label(dialog, text="거래일자 (YYYY-MM-DD):", bg=BG_COLOR, fg=TEXT_COLOR).grid(row=1, column=0, padx=15, pady=8, sticky="e")
        ent_date = tk.Entry(dialog, font=("Malgun Gothic", 10)); ent_date.grid(row=1, column=1, padx=10, pady=8)
        ent_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        tk.Label(dialog, text=f"매도 수량 ({asset['unit']}):", bg=BG_COLOR, fg=TEXT_COLOR).grid(row=2, column=0, padx=15, pady=8, sticky="e")
        ent_qty = tk.Entry(dialog, font=("Malgun Gothic", 11)); ent_qty.grid(row=2, column=1, padx=10, pady=8)
        
        tk.Label(dialog, text="체결 단가 (원):", bg=BG_COLOR, fg=TEXT_COLOR).grid(row=3, column=0, padx=15, pady=8, sticky="e")
        ent_price = tk.Entry(dialog, font=("Malgun Gothic", 11)); ent_price.grid(row=3, column=1, padx=10, pady=8)
        if c_price != "": ent_price.insert(0, str(c_price))

        def apply_sell():
            try:
                t_date = ent_date.get().strip()
                s_qty = float(ent_qty.get()); s_price = float(ent_price.get())
                if s_qty <= 0 or s_price < 0 or not t_date: raise ValueError
                
                old_qty = float(asset['qty']); old_avg = float(asset.get('avg_price', 0))
                if s_qty > old_qty: return messagebox.showerror("수량 초과", "보유 수량보다 많이 매도할 수 없습니다.")
                
                gross_proceeds = s_qty * s_price 
                tax_and_fee = gross_proceeds * 0.002 if asset["type"] == "stock" else 0
                net_proceeds = gross_proceeds - tax_and_fee 
                
                current_deposit = self.category_deposits.get(cat, 0.0)
                self.category_deposits[cat] = current_deposit + net_proceeds
                
                new_qty = old_qty - s_qty
                if new_qty.is_integer(): new_qty = int(new_qty)
                realized_pl = (s_price - old_avg) * s_qty - tax_and_fee
                
                self.assets[index]['qty'] = new_qty
                if new_qty == 0: self.assets[index]['avg_price'] = 0
                
                self.history.append({
                    "date": t_date, "type": "매도", "category": cat,
                    "name": asset['name'], "qty": s_qty, "price": s_price, "unit": asset['unit']
                })
                
                self.save_data()
                self.insert_initial_data()
                self.update_history_table()
                
                sign = "+" if realized_pl > 0 else ""
                msg = f"일자: {t_date}\n매도대금(세후): {int(net_proceeds):,}원 예수금 입금\n실현 손익: {sign}{int(realized_pl):,} 원"
                if tax_and_fee > 0:
                    msg += f"\n(수수료/세금 공제: {int(tax_and_fee):,}원)"
                    
                messagebox.showinfo("매도 완료", msg)
                dialog.destroy()
                self.btn_refresh.invoke()
            except ValueError: messagebox.showerror("입력 오류", "날짜를 정확히 입력하고 수량/단가에 숫자를 입력해주세요.")

        tk.Button(dialog, text="🔵 매도 반영 및 기록", command=apply_sell, bg=BLUE_COLOR, fg="white", font=("Malgun Gothic", 11, "bold"), relief="flat", padx=15, pady=5).grid(row=4, column=0, columnspan=2, pady=15)

    def open_asset_dialog(self, asset=None, index=None):
        dialog = Toplevel(self); dialog.title("자산 정보"); dialog.geometry("400x370"); dialog.configure(bg=BG_COLOR)
        lbl_style = {"bg": BG_COLOR, "fg": TEXT_COLOR, "font": ("Malgun Gothic", 10)}
        tk.Label(dialog, text="계좌 분류:", **lbl_style).grid(row=0, column=0, padx=15, pady=10, sticky="e")
        cb_category = ttk.Combobox(dialog, values=["키움(일반)", "키움(ISA)", "가상자산", "실물자산", "외환", "현금", "기타"], font=("Malgun Gothic", 10)); cb_category.grid(row=0, column=1, padx=10, pady=10)
        tk.Label(dialog, text="자산명:", **lbl_style).grid(row=1, column=0, padx=15, pady=10, sticky="e")
        ent_name = tk.Entry(dialog, font=("Malgun Gothic", 10)); ent_name.grid(row=1, column=1, padx=10, pady=10)
        tk.Label(dialog, text="유형:", **lbl_style).grid(row=2, column=0, padx=15, pady=10, sticky="e")
        cb_type = ttk.Combobox(dialog, values=["stock", "crypto", "gold", "silver", "cash", "fx"], state="readonly", font=("Malgun Gothic", 10)); cb_type.grid(row=2, column=1, padx=10, pady=10)
        tk.Label(dialog, text="보유 수량:", **lbl_style).grid(row=3, column=0, padx=15, pady=10, sticky="e")
        ent_qty = tk.Entry(dialog, font=("Malgun Gothic", 10)); ent_qty.grid(row=3, column=1, padx=10, pady=10)
        tk.Label(dialog, text="티커/종목코드:", **lbl_style).grid(row=4, column=0, padx=15, pady=10, sticky="e")
        ent_ticker = tk.Entry(dialog, font=("Malgun Gothic", 10)); ent_ticker.grid(row=4, column=1, padx=10, pady=10)
        tk.Label(dialog, text="매수 단가 (평단가):", **lbl_style).grid(row=5, column=0, padx=15, pady=10, sticky="e")
        ent_avg_price = tk.Entry(dialog, font=("Malgun Gothic", 10)); ent_avg_price.grid(row=5, column=1, padx=10, pady=10)
        
        if asset:
            cb_category.set(asset.get("category", "기타")); ent_name.insert(0, asset.get("name", "")); cb_type.set(asset.get("type", ""))
            ent_qty.insert(0, str(asset.get("qty", ""))); ent_ticker.insert(0, asset.get("ticker", "")); ent_avg_price.insert(0, str(asset.get("avg_price", "0")))
        else: cb_category.set("키움(일반)"); cb_type.set("stock"); ent_avg_price.insert(0, "0")

        def save():
            try:
                cat = cb_category.get(); name = ent_name.get(); t_type = cb_type.get()
                qty = float(ent_qty.get())
                if qty.is_integer() and t_type != "crypto": qty = int(qty)
                ticker = ent_ticker.get().strip()
                try: avg_price = float(ent_avg_price.get())
                except: avg_price = 0.0
                
                if t_type == "stock": unit = "주"
                elif t_type == "crypto": unit = "개"
                elif t_type in ["gold", "silver"]: unit = "g"
                elif t_type == "cash": unit = "원"
                elif t_type == "fx": unit = ticker.upper()
                else: unit = ""
                
                new_asset = {"category": cat, "name": name, "type": t_type, "qty": qty, "ticker": ticker, "unit": unit, "avg_price": avg_price}
                if index is not None: self.assets[index] = new_asset
                else: self.assets.append(new_asset)
                self.save_data(); self.insert_initial_data(); dialog.destroy()
            except ValueError: messagebox.showerror("입력 오류", "수량/단가에는 숫자만 입력해주세요.")

        tk.Button(dialog, text="저장하기", command=save, bg=ACCENT_COLOR, fg="white", font=("Malgun Gothic", 10, "bold"), relief="flat", padx=20, pady=5).grid(row=6, column=0, columnspan=2, pady=15)

    def add_asset(self): self.open_asset_dialog()
    def edit_asset(self):
        selected = self.tree.selection()
        if not selected: return messagebox.showwarning("오류", "수정할 자산을 선택해주세요.")
        if str(selected[0]).startswith("dep_"): return messagebox.showwarning("선택 오류", "예수금 항목은 우측 탭의 [예수금] 버튼을 이용해 관리해주세요.")
        self.open_asset_dialog(self.assets[int(selected[0])], int(selected[0]))
    def delete_asset(self, event=None):
        selected = self.tree.selection()
        if not selected: return messagebox.showwarning("오류", "삭제할 자산을 선택해주세요.")
        if str(selected[0]).startswith("dep_"): return messagebox.showwarning("선택 오류", "예수금 항목은 우측 탭의 [예수금] 버튼을 이용해 관리해주세요.")
        if messagebox.askyesno("확인", "삭제하시겠습니까?"):
            del self.assets[int(selected[0])]; self.save_data(); self.insert_initial_data()

if __name__ == '__main__':
    app = AssetApp()
    app.mainloop()