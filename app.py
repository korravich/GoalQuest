import os
import random
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
import streamlit as st
from supabase import create_client
from streamlit_cookies_controller import CookieController
import time
import pandas as pd
import altair as alt
import streamlit.components.v1 as components
import html
from PIL import Image

_icon_path = os.path.join(os.path.dirname(__file__), "korvian_icon.png")
try:
    _icon = Image.open(_icon_path)
except Exception as _e:
    _icon = "🌀"
    _icon_error = f"{_icon_path} -> {_e}"

st.set_page_config(
    page_title="Korvian",
    page_icon=_icon,
    layout="wide",
    initial_sidebar_state="expanded"
)
if "_icon_error" in globals():
    st.warning(f"โหลดไอคอนไม่ได้: {_icon_error}")

def korvian_logo_svg(size=28, color="#b8bac2"):
    return (
        f"<svg width='{size}' height='{size}' viewBox='0 0 28 28' "
        "xmlns='http://www.w3.org/2000/svg'>"
        f"<circle cx='14' cy='14' r='11' fill='none' stroke='{color}' stroke-width='0.9'/>"
        f"<circle cx='14' cy='14' r='9.3' fill='none' stroke='{color}' stroke-width='0.9'/>"
        f"<path fill='{color}' d='M14 6.8 C14 12.2 15.8 14 21.2 14 "
        "C15.8 14 14 15.8 14 21.2 C14 15.8 12.2 14 6.8 14 "
        "C12.2 14 14 12.2 14 6.8 Z'/>"
        "</svg>"
    )



# ระบบเชื่อมต่อ Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
session_supabase = create_client(
    SUPABASE_URL,
    st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
)
cookie_controller = CookieController()

def save_persistent_session(user_id, access_token, refresh_token):
    try:
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires = datetime.now(timezone.utc) + timedelta(days=30)

        session_supabase.table("user_sessions").insert({
            "user_id": user_id,
            "token_hash": token_hash,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires.isoformat()
        }).execute()

        cookie_controller.set(
            "gq_session",
            token,
            max_age=30 * 24 * 60 * 60,
            secure=True,
            same_site="lax"
        )
    
    except Exception as e:
        st.error(f"บันทึก session ไม่สำเร็จ: {e}")
def compact_old_records(uid):
    """รวมยอดรายวันที่เก่ากว่า 30 วันเข้ารายเดือน แล้วลบแถวรายวันทิ้ง"""
    today = datetime.now(timezone(timedelta(hours=7))).date()
    cutoff = today - timedelta(days=30)

    old = (
        supabase.table("daily_records")
        .select("record_date, income, expense")
        .eq("user_id", uid)
        .lt("record_date", cutoff.isoformat())
        .execute()
    )

    if not old.data:
        return

    # รวมยอดแยกตามเดือน
    totals = {}
    for row in old.data:
        month_key = row["record_date"][:7] + "-01"   # เช่น 2026-09-01
        t = totals.setdefault(month_key, {"income": 0.0, "expense": 0.0})
        t["income"] += float(row["income"])
        t["expense"] += float(row["expense"])

    # บวกทบเข้ารายเดือน (ถ้าเดือนนั้นมีอยู่แล้ว)
    for month_key, t in totals.items():
        existing = (
            supabase.table("monthly_records")
            .select("income, expense")
            .eq("user_id", uid)
            .eq("month", month_key)
            .execute()
        )
        old_inc = float(existing.data[0]["income"]) if existing.data else 0.0
        old_exp = float(existing.data[0]["expense"]) if existing.data else 0.0

        supabase.table("monthly_records").upsert({
            "user_id": uid,
            "month": month_key,
            "income": old_inc + t["income"],
            "expense": old_exp + t["expense"]
        }).execute()

    # ลบแถวรายวันที่รวมแล้ว (ลบหลังรวมสำเร็จเท่านั้น)
    supabase.table("daily_records") \
        .delete() \
        .eq("user_id", uid) \
        .lt("record_date", cutoff.isoformat()) \
        .execute()

def load_daily_range(uid, days):
    """ดึงรายรับ-รายจ่ายรายวันย้อนหลัง days วัน (วันที่ไม่มีข้อมูลเป็น 0)"""
    today = datetime.now(timezone(timedelta(hours=7))).date()
    start = today - timedelta(days=days - 1)

    res = (
        supabase.table("daily_records")
        .select("record_date, income, expense")
        .eq("user_id", uid)
        .gte("record_date", start.isoformat())
        .lte("record_date", today.isoformat())
        .execute()
    )
    data = {r["record_date"]: r for r in res.data}

    rows = []
    for i in range(days):
        d = start + timedelta(days=i)
        r = data.get(d.isoformat())
        rows.append({
            "วันที่": pd.Timestamp(d),
            "รายรับ": float(r["income"]) if r else 0.0,
            "รายจ่าย": float(r["expense"]) if r else 0.0,
        })
    return pd.DataFrame(rows).set_index("วันที่")


def load_monthly(uid):
    """ดึงสรุปรายเดือน (ข้อมูลที่เก่ากว่า 30 วัน)"""
    res = (
        supabase.table("monthly_records")
        .select("month, income, expense")
        .eq("user_id", uid)
        .order("month")
        .execute()
    )
    rows = [{
        "เดือน": pd.Timestamp(r["month"]),
        "รายรับ": float(r["income"]),
        "รายจ่าย": float(r["expense"]),
    } for r in res.data]
    if not rows:
        return pd.DataFrame(columns=["รายรับ", "รายจ่าย"])
    return pd.DataFrame(rows).set_index("เดือน")


def add_balance_daily(df, current_balance):
    """เติมคอลัมน์ 'เงินเก็บ' (ยอด ณ สิ้นวัน) โดยคำนวณย้อนจากยอดปัจจุบัน"""
    out = df.copy()
    net = out["รายรับ"] - out["รายจ่าย"]
    after = net[::-1].cumsum()[::-1] - net      # ผลรวมสุทธิของวันหลังจากวันนั้น
    out["เงินเก็บ"] = current_balance - after
    return out


def add_balance_monthly(uid, df, current_balance):
    """เติมคอลัมน์ 'เงินเก็บ' (ยอด ณ สิ้นเดือน) สำหรับกราฟรายเดือน"""
    res = (
        supabase.table("daily_records")
        .select("record_date, income, expense")
        .eq("user_id", uid)
        .execute()
    )
    daily = [
        (pd.Timestamp(r["record_date"]), float(r["income"]) - float(r["expense"]))
        for r in res.data
    ]

    out = df.copy()
    net_m = out["รายรับ"] - out["รายจ่าย"]
    later_months = net_m[::-1].cumsum()[::-1] - net_m

    values = []
    for month, later in later_months.items():
        month_end = month + pd.offsets.MonthEnd(0)
        daily_after = sum(n for d, n in daily if d > month_end)
        values.append(current_balance - later - daily_after)

    out["เงินเก็บ"] = values
    return out


def show_bar_chart(df, monthly=False, goal=0.0, goal_name=""):
    """แท่งรายรับ/รายจ่าย + เส้นเงินเก็บ + เส้นเป้าหมาย ใช้แกนตัวเลขเดียวกัน"""
    data = df.reset_index()
    time_col = data.columns[0]
    data["label"] = data[time_col].dt.strftime("%m/%Y" if monthly else "%d/%m")
    order = list(dict.fromkeys(data["label"]))

    bars_data = data.melt(
        id_vars=[time_col, "label"],
        value_vars=["รายรับ", "รายจ่าย"],
        var_name="ประเภท",
        value_name="จำนวนเงิน"
    )

    has_balance = "เงินเก็บ" in data.columns

    # หาช่วงแกนเดียวที่ครอบคลุมทุกอย่าง เผื่อที่ว่างด้านบน 20%
    tops = [float(bars_data["จำนวนเงิน"].max())]
    lows = [0.0]
    if has_balance:
        tops.append(float(data["เงินเก็บ"].max()))
        lows.append(float(data["เงินเก็บ"].min()))
    if goal > 0:
        tops.append(float(goal))
    top, low = max(tops), min(lows)
    span = top - low
    y_max = top + span * 0.2 if span > 0 else 100
    y_scale = alt.Scale(domain=[low, y_max])

    x_enc = alt.X(
        "label:N", sort=order, title=None,
        axis=alt.Axis(labelAngle=-45)
    )

    bars = (
        alt.Chart(bars_data)
        .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
        .encode(
            x=x_enc,
            xOffset=alt.XOffset("ประเภท:N", sort=["รายรับ", "รายจ่าย"]),
            y=alt.Y("จำนวนเงิน:Q", title="บาท", scale=y_scale),
            color=alt.Color(
                "ประเภท:N",
                scale=alt.Scale(
                    domain=["รายรับ", "รายจ่าย"],
                    range=["#2ECC71", "#E74C3C"]
                ),
                legend=alt.Legend(title=None, orient="top")
            ),
            tooltip=["label", "ประเภท", "จำนวนเงิน"]
        )
    )

    layers = [bars]

    if has_balance:
        line = (
            alt.Chart(data)
            .mark_line(
                color="#3498DB", strokeWidth=3,
                point=alt.OverlayMarkDef(color="#3498DB", size=60)
            )
            .encode(
                x=x_enc,
                y=alt.Y("เงินเก็บ:Q", title="บาท", scale=y_scale),
                tooltip=[
                    alt.Tooltip("label:N", title="ช่วง"),
                    alt.Tooltip("เงินเก็บ:Q", title="เงินเก็บ", format=",.2f")
                ]
            )
        )
        layers.append(line)

    if goal > 0:
        rule = (
            alt.Chart(pd.DataFrame({"เป้าหมาย": [float(goal)]}))
            .mark_rule(color="#F39C12", strokeWidth=1.5, strokeDash=[6, 4])
            .encode(
                y=alt.Y("เป้าหมาย:Q", title="บาท", scale=y_scale),
                tooltip=[alt.Tooltip("เป้าหมาย:Q", format=",.2f")]
            )
        )
        layers.append(rule)

    chart = alt.layer(*layers).properties(height=380, width=520)
    st.altair_chart(chart, use_container_width=False)

    if has_balance:
        text = "🔵 เส้นฟ้า = เงินเก็บ"
        if goal > 0:
            text += f"   ·  🟠 เส้นประ = เป้าหมาย {goal_name} {goal:,.2f} บาท (เส้นฟ้าแตะเส้นนี้ = ถึงเป้าแล้ว)"
        st.caption(text)



# ==========================================
# ระบบสมัครสมาชิกและเข้าสู่ระบบ
# ==========================================

# คืนสถานะการเข้าสู่ระบบจาก Streamlit session
# คืนสถานะล็อกอินจาก session ที่บันทึกไว้
cookie_token = cookie_controller.get("gq_session")

if "user_id" not in st.session_state and cookie_token:
    try:
        token_hash = hashlib.sha256(
            cookie_token.encode()
        ).hexdigest()

        response = (
            session_supabase.table("user_sessions")
            .select("*")
            .eq("token_hash", token_hash)
            .gt("expires_at", datetime.now(timezone.utc).isoformat())
            .maybe_single()
            .execute()
        )

        saved = response.data

        if saved:
            # ใช้ refresh token ขอ token ชุดใหม่ (ไม่ใช้ access token เก่า)
            refreshed = supabase.auth.refresh_session(
                saved["refresh_token"]
            )

            if refreshed.session and refreshed.user:
                new_access = refreshed.session.access_token
                new_refresh = refreshed.session.refresh_token

                # เก็บค่าใหม่ทับลงตาราง
                session_supabase.table("user_sessions").update({
                    "access_token": new_access,
                    "refresh_token": new_refresh
                }).eq("token_hash", token_hash).execute()

                st.session_state["user_id"] = refreshed.user.id
                st.session_state["user_email"] = refreshed.user.email or ""
                st.session_state["access_token"] = new_access
                st.session_state["refresh_token"] = new_refresh
    except Exception:
        pass
if (
    "user_id" in st.session_state
    and "access_token" in st.session_state
    and "refresh_token" in st.session_state
):
    try:
        supabase.auth.set_session(
            st.session_state["access_token"],
            st.session_state["refresh_token"]
        )
    except Exception:
        pass

# ถ้ายังไม่ได้เข้าสู่ระบบ ให้แสดงหน้าสมัครและล็อกอิน
if "user_id" not in st.session_state:
    st.markdown(
        "<div style='display:flex;align-items:center;gap:14px;margin-bottom:4px;'>"
        "<div style='background:#06060a;border-radius:16px;padding:10px;display:flex;'>"
        + korvian_logo_svg(44) +
        "</div>"
        "<span style='font-size:44px;font-weight:800;letter-spacing:2px;'>Korvian</span>"
        "</div>",
        unsafe_allow_html=True
    )
    st.caption("Your Future Depends on What You Do Today (beta)")
    st.subheader("Start your goals")

    login_tab, signup_tab = st.tabs(
        ["เข้าสู่ระบบ", "สมัครสมาชิก"]
    )

    with login_tab:
        with st.form("login_form"):
            login_email = st.text_input("อีเมล")
            login_password = st.text_input("รหัสผ่าน", type="password")
            login_submit = st.form_submit_button(
                "เข้าสู่ระบบ",
                use_container_width=True
            )

        if login_submit:
            try:
                result = supabase.auth.sign_in_with_password({
                    "email": login_email.strip(),
                    "password": login_password
                })

                if result.user and result.session:
                    st.session_state["user_id"] = result.user.id
                    st.session_state["user_email"] = result.user.email
                    st.session_state["access_token"] = result.session.access_token
                    st.session_state["refresh_token"] = result.session.refresh_token

                    save_persistent_session(
                        result.user.id,
                        result.session.access_token,
                        result.session.refresh_token
                    )
                    time.sleep(1)
                    st.rerun()

            except Exception:
                st.error("เข้าสู่ระบบไม่สำเร็จ โปรดตรวจสอบอีเมล รหัสผ่าน หรือการยืนยันอีเมล")
    with signup_tab:
        with st.form("signup_form"):
            signup_email = st.text_input("อีเมลสำหรับสมัคร")
            signup_password = st.text_input(
                "ตั้งรหัสผ่าน",
                type="password"
            )
            signup_password_again = st.text_input(
                "ยืนยันรหัสผ่าน",
                type="password"
            )
            signup_submit = st.form_submit_button(
                "สมัครสมาชิก",
                use_container_width=True
            )

        if signup_submit:
            if not signup_email.strip():
                st.error("กรุณากรอกอีเมล")
            elif len(signup_password) < 8:
                st.error("รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร")
            elif signup_password != signup_password_again:
                st.error("รหัสผ่านทั้งสองช่องไม่ตรงกัน")
            else:
                try:
                    result = supabase.auth.sign_up({
                        "email": signup_email.strip(),
                        "password": signup_password
                    })

                    if result.session and result.user:
                        st.session_state["user_id"] = result.user.id
                        st.session_state["user_email"] = result.user.email
                        st.session_state["access_token"] = result.session.access_token
                        st.session_state["refresh_token"] = result.session.refresh_token

                        save_persistent_session(
                            result.user.id,
                            result.session.access_token,
                            result.session.refresh_token
                        )

                        st.success("สมัครสมาชิกสำเร็จ!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.success(
                            "ส่งคำขอสมัครแล้ว "
                            "กรุณาตรวจอีเมลเพื่อยืนยันบัญชี "
                            "ก่อนเข้าสู่ระบบ"
                        )

                except Exception as e:
                    st.error(f"สมัครสมาชิกไม่สำเร็จ: {e}")

    # ยังไม่เข้าสู่ระบบ ห้ามแสดงส่วนเกมด้านล่าง
    st.stop()



# ==========================================
# 💾 ระบบหลังบ้าน: โหลดข้อมูลจาก Supabase
# ==========================================

if "player_data_loaded" not in st.session_state:
    try:
        user_id = st.session_state["user_id"]

        # โหลดข้อมูลของบัญชีที่เข้าสู่ระบบอยู่เท่านั้น
        response = (
            supabase.table("player_data")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )

        if response.data:
            player_data = response.data[0]
        else:
            # สร้างข้อมูลเริ่มต้นสำหรับผู้เล่นใหม่
            new_player = {
                "user_id": user_id,
                "balance": 0,
                "goal": "0",
                "item": "สิ่งที่อยากได้"
            }

            supabase.table("player_data").insert(
                new_player
            ).execute()

            player_data = new_player

        st.session_state.balance = float(
            player_data["balance"]
        )
        st.session_state.goal = float(
            player_data["goal"]
        )
        st.session_state.item_name = player_data["item"]
        st.session_state.player_data_loaded = True

        # รวมยอดเก่าเข้ารายเดือน (ทำครั้งเดียวตอนเปิดแอป)
        try:
            compact_old_records(user_id)
        except Exception as e:
            st.warning(f"รวมยอดข้อมูลเก่าไม่สำเร็จ: {e}")

    except Exception as e:
        st.error(f"โหลดข้อมูลไม่สำเร็จ: {e}")
        st.stop()



# ==========================================
# 🧭 ระบบเมนูหลัก (Sidebar ด้านข้าง)
# ==========================================

st.sidebar.markdown("""
<style>
section[data-testid="stSidebar"] { background: #f1f5fb; }

/* สีตัวอักษรเฉพาะส่วนเมนู (ไม่ไปแตะปุ่มรีเซ็ต/ออกจากระบบ) */
.gq-title, .gq-sub,
section[data-testid="stSidebar"] div[role="radiogroup"] label p {
    color: #14213d;
}

.gq-banner {
    background: #06060a; border-radius: 14px;
    padding: 14px 16px; margin-bottom: 18px;
}
.gq-row { display: flex; align-items: center; gap: 10px; }
.gq-banner b { color: #fff !important; font-size: 20px; }
.gq-banner span { color: #dbe6f7 !important; font-size: 13px; display: block; margin-top: 4px; }
.gq-title { font-size: 56px; font-weight: 300; letter-spacing: 2px; line-height: 1.1; margin: 0 0 6px 0; }
.gq-sub { font-size: 14px; color: #5b6b82 !important; margin-bottom: 10px; }

section[data-testid="stSidebar"] div[role="radiogroup"] { gap: 10px; }

/* การ์ดเมนู */
section[data-testid="stSidebar"] div[role="radiogroup"] label {
    display: flex !important; align-items: center !important;
    background: #fff !important;
    border: 1px solid #e3eaf4 !important;
    border-radius: 14px !important;
    padding: 12px 14px !important; min-height: 70px !important;
    transition: background-color .2s, border-color .2s;
    cursor: pointer;
}
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
    border-color: #75baff !important;
}

/* ไฮไลต์หน้าที่เลือกอยู่ */
section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked),
section[data-testid="stSidebar"] label[data-testid="stRadioOption"][data-selected="true"] {
    background: #dbeafe !important;
    border-color: #4b91e6 !important;
}

/* ซ่อนวงกลมของ radio */
section[data-testid="stSidebar"] label[data-testid="stRadioOption"] > div > div:first-child,
section[data-testid="stSidebar"] label[data-baseweb="radio"] > div:first-child {
    display: none !important;
}

/* กล่องไอคอนด้านซ้าย */
section[data-testid="stSidebar"] div[role="radiogroup"] label::before {
    content: ""; flex: none; width: 44px; height: 44px;
    margin-right: 14px; border-radius: 12px;
    background-repeat: no-repeat; background-position: center;
    background-size: 26px;
}

/* 1) กราฟแท่ง - กล่องสีฟ้า */
section[data-testid="stSidebar"] div[role="radiogroup"] > label:nth-child(1)::before,
section[data-testid="stSidebar"] div[role="radiogroup"] > *:nth-child(1) label::before {
    background-color: #cfe3ff;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%232f6fd6' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M4 20h16M7 20v-6M12 20V8M17 20v-9'/%3E%3C/svg%3E");
}
/* 2) กระเป๋าเงิน - กล่องสีเหลือง */
section[data-testid="stSidebar"] div[role="radiogroup"] > label:nth-child(2)::before,
section[data-testid="stSidebar"] div[role="radiogroup"] > *:nth-child(2) label::before {
    background-color: #fff0bf;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23d99a00' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect x='3' y='7' width='18' height='13' rx='3'/%3E%3Cpath d='M5 7l10-3v3'/%3E%3Crect x='14' y='11' width='7' height='5' rx='2.5'/%3E%3Cpath d='M17.5 13.5h.01'/%3E%3C/svg%3E");
}
/* 3) หัวใจ - กล่องสีเขียว */
section[data-testid="stSidebar"] div[role="radiogroup"] > label:nth-child(3)::before,
section[data-testid="stSidebar"] div[role="radiogroup"] > *:nth-child(3) label::before {
    background-color: #d3f4e2;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%231f9d6b' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M12 20s-8-5-8-11a4.5 4.5 0 018-2.8A4.5 4.5 0 0120 9c0 6-8 11-8 11z'/%3E%3C/svg%3E");
}
/* 4) การศึกษา - กล่องสีม่วง */
section[data-testid="stSidebar"] div[role="radiogroup"] > label:nth-child(4)::before,
section[data-testid="stSidebar"] div[role="radiogroup"] > *:nth-child(4) label::before {
    background-color: #e6dcfb;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%237c4dcc' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M12 6c-2-1.5-5-2-8-2v13c3 0 6 .5 8 2 2-1.5 5-2 8-2V4c-3 0-6 .5-8 2zM12 6v13'/%3E%3C/svg%3E");
}

/* ลูกศรด้านขวา */
section[data-testid="stSidebar"] div[role="radiogroup"] label::after {
    content: "›"; margin-left: auto; font-size: 26px; color: #7a8aa3;
}

/* ชื่อเมนู + คำอธิบายบรรทัดที่สอง */
section[data-testid="stSidebar"] div[role="radiogroup"] label p {
    font-size: 16px !important; font-weight: 700 !important; margin: 0 !important;
}
section[data-testid="stSidebar"] div[role="radiogroup"] label p::after {
    display: block; font-size: 13px; font-weight: 400; color: #5b6b82;
}
section[data-testid="stSidebar"] div[role="radiogroup"] > label:nth-child(1) p::after,
section[data-testid="stSidebar"] div[role="radiogroup"] > *:nth-child(1) label p::after {
    content: "ดูภาพรวมเป้าหมายของคุณ";
}
section[data-testid="stSidebar"] div[role="radiogroup"] > label:nth-child(2) p::after,
section[data-testid="stSidebar"] div[role="radiogroup"] > *:nth-child(2) label p::after {
    content: "วางแผนเงินเก็บของคุณ";
}
section[data-testid="stSidebar"] div[role="radiogroup"] > label:nth-child(3) p::after,
section[data-testid="stSidebar"] div[role="radiogroup"] > *:nth-child(3) label p::after {
    content: "ติดตามการดูแลตัวเอง";
}
section[data-testid="stSidebar"] div[role="radiogroup"] > label:nth-child(4) p::after,
section[data-testid="stSidebar"] div[role="radiogroup"] > *:nth-child(4) label p::after {
    content: "เร็วๆ นี้";
}

/* ===== Sidebar เลื่อนเข้า-ออก ===== */
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stExpandSidebarButton"] { display: none !important; }

section[data-testid="stSidebar"] {
    position: fixed !important;
    top: 0 !important; left: 0 !important;
    height: 100dvh !important;
    width: min(380px, 88vw) !important;
    min-width: 0 !important;
    max-width: 100vw !important;
    transform: translateX(calc(-100% + 20px)) !important;
    transition: transform .45s cubic-bezier(.22,.8,.3,1),
                width .45s cubic-bezier(.22,.8,.3,1) !important;
    z-index: 999991 !important;
    box-shadow: 4px 0 24px rgba(20,33,61,.18);
}

/* ขีดสีฟ้าบอกว่าดึงออกมาได้ */
section[data-testid="stSidebar"]::after {
    content: ""; position: absolute; top: 50%; right: 7px;
    width: 5px; height: 64px; margin-top: -32px;
    border-radius: 3px; background: #4b91e6; opacity: .8;
    pointer-events: none;
}

/* สถานะต่างๆ (ลำดับสำคัญ ห้ามสลับ) */
section[data-testid="stSidebar"].gq-open { transform: translateX(0) !important; }
@media (hover: hover) {
    section[data-testid="stSidebar"]:hover { transform: translateX(0) !important; }
}
section[data-testid="stSidebar"].gq-full {
    width: 100vw !important;
    transform: translateX(0) !important;
}
section[data-testid="stSidebar"].gq-full::after { opacity: 0; }
section[data-testid="stSidebar"].gq-shut {
    transform: translateX(calc(-100% + 20px)) !important;
}

/* ===== ทำให้แถบ Goal Quest กับการ์ดทั้ง 3 ยาวเท่ากัน ===== */

/* ทุกชั้นที่ครอบ radio ให้ยืดเต็มความกว้าง */
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"],
section[data-testid="stSidebar"] [data-testid="stElementContainer"],
section[data-testid="stSidebar"] [data-testid="stRadio"],
section[data-testid="stSidebar"] [data-testid="stRadio"] > div,
section[data-testid="stSidebar"] div[role="radiogroup"] {
    width: 100% !important;
    max-width: 100% !important;
}

/* กลุ่มการ์ด: เรียงแนวตั้ง ให้ลูกยืดเต็มแนวนอน */
section[data-testid="stSidebar"] div[role="radiogroup"] {
    display: flex !important;
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 10px;
}

/* การ์ดและแถบ Goal Quest ใช้ขนาดกล่องแบบเดียวกัน */
section[data-testid="stSidebar"] div[role="radiogroup"] label,
.gq-banner {
    width: 100% !important;
    box-sizing: border-box !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label {
    min-height: 76px !important;
    padding: 12px 14px !important;
}

/* ตอนขยายเต็มจอ: เว้นขอบที่ตัวครอบ (ไม่ใช่ที่ตัวการ์ด) ทุกอันจึงเท่ากัน */
section[data-testid="stSidebar"].gq-full [data-testid="stSidebarUserContent"] {
    padding-left: 5vw !important;
    padding-right: 5vw !important;
}

/* ไอคอน ตัวอักษร */
section[data-testid="stSidebar"] div[role="radiogroup"] label::before {
    width: 50px !important; height: 50px !important;
    background-size: 28px !important;
}
section[data-testid="stSidebar"] div[role="radiogroup"] label p {
    font-size: 18px !important;
}
section[data-testid="stSidebar"] div[role="radiogroup"] label p::after {
    font-size: 14px !important;
}

/* QUEST ลดลงจาก 72px */
.gq-title { font-size: 40px !important; }

/* ===== มือถือ/จอสัมผัส: ซ่อน sidebar สนิท เหลือแท็บเล็กๆ ===== */
@media (hover: none), (max-width: 768px) {
    section[data-testid="stSidebar"] {
        overflow: visible !important;
        transform: translateX(-100%) !important;
        box-shadow: none !important;
    }
    section[data-testid="stSidebar"].gq-shut {
        transform: translateX(-100%) !important;
        box-shadow: none !important;
    }
    section[data-testid="stSidebar"].gq-open,
    section[data-testid="stSidebar"].gq-full {
        transform: translateX(0) !important;
        box-shadow: 4px 0 24px rgba(20,33,61,.18) !important;
    }

    /* แท็บเล็กๆ ยื่นออกจากขอบ sidebar มาติดขอบจอ */
    section[data-testid="stSidebar"]::after {
        left: 100% !important;
        right: auto !important;
        width: 14px !important;
        height: 56px !important;
        margin-top: -28px !important;
        border-radius: 0 10px 10px 0 !important;
        background: #4b91e6 !important;
        opacity: .85 !important;
        pointer-events: auto !important;
    }
    section[data-testid="stSidebar"].gq-open::after,
    section[data-testid="stSidebar"].gq-full::after {
        opacity: 0 !important;
    }
}

.gq-title { font-size: 20px !important; font-weight: 300 !important; color: #050b1a !important; opacity: 1 !important; }

</style>
""", unsafe_allow_html=True)

st.sidebar.markdown(
    "<div class='gq-banner'>"
    "<div class='gq-row'>"
    + korvian_logo_svg(28) +
    "<b>Korvian</b>"
    "</div>"
    "<span>Your Future Depends on What You Do Today.</span>"
    "</div>"
    "<p class='gq-title'>QUEST</p>"
    "<p class='gq-sub'>เลือกเมนูที่ต้องการ</p>",
    unsafe_allow_html=True
)

menu = st.sidebar.radio(
    "เลือกหน้า",
    ["🎯สรุปผล", "💰 Money Line", "💪 Health Line", "📚 Study Line"],
    label_visibility="collapsed"
)
components.html("""
<script>
function main() {
  const SB = 'section[data-testid="stSidebar"]';
  const sb = () => document.querySelector(SB);
  let busy = false;
  let lockUntil = 0;

  const open = () => {
    const s = sb();
    if (!s || Date.now() < lockUntil) return;
    s.classList.remove('gq-shut');
    s.classList.add('gq-open');
  };
  const close = () => {
    const s = sb();
    if (!s || busy) return;
    s.classList.remove('gq-open');
  };

  // เมาส์: ชี้แล้วเปิด ออกแล้วปิด
  document.addEventListener('pointerover', (e) => {
    if (e.pointerType === 'mouse' && e.target.closest && e.target.closest(SB)) open();
  });
  document.addEventListener('pointerout', (e) => {
    if (e.pointerType !== 'mouse' || busy) return;
    const from = e.target.closest && e.target.closest(SB);
    const to = e.relatedTarget && e.relatedTarget.closest && e.relatedTarget.closest(SB);
    if (from && !to) close();
  });

  // นิ้ว: แตะที่ขอบเพื่อเปิด แตะข้างนอกเพื่อปิด
  document.addEventListener('pointerdown', (e) => {
    if (e.pointerType === 'mouse' || busy) return;
    if (e.target.closest && e.target.closest(SB)) open(); else close();
  }, true);

  // เช็กว่า Streamlit กำลังโหลดหน้าใหม่อยู่ไหม
  const isRunning = () => !!document.querySelector(
    '.stApp[data-test-script-state="running"], [data-testid="stStatusWidget"], [data-stale="true"]'
  );

  function finish() {
    const s = sb();
    lockUntil = Date.now() + 700;   // กันเมาส์ที่ยังขยับอยู่ดึงกลับมาเปิดอีก
    if (s) {
      s.classList.remove('gq-open');
      s.classList.add('gq-shut');
      setTimeout(() => {
        if (s.classList.contains('gq-shut')) s.classList.remove('gq-full');
      }, 650);
    }
    busy = false;
  }

  function startSwitch() {
    if (busy) return;
    const s = sb();
    if (!s) return;
    busy = true;
    s.classList.remove('gq-shut');
    s.classList.add('gq-open', 'gq-full');   // ขยายเต็มจอบังหน้าเว็บ

    const t0 = Date.now();
    let seen = false, idle = 0;
    const iv = setInterval(() => {
      const el = Date.now() - t0;
      if (isRunning()) { seen = true; idle = 0; } else { idle++; }
      // เสร็จเมื่อ: เคยโหลดและนิ่งแล้ว (อย่างน้อย 0.9 วิ) / ไม่เห็นการโหลดเลยเกิน 1.8 วิ / เกิน 8 วิ
      if ((seen && idle >= 3 && el > 900) || (!seen && el > 1800) || el > 8000) {
        clearInterval(iv);
        finish();
      }
    }, 120);
  }

  // กดการ์ดเมนูตัวใดตัวหนึ่ง
  document.addEventListener('click', (e) => {
    const lab = e.target.closest && e.target.closest(SB + ' div[role="radiogroup"] label');
    if (lab) startSwitch();
  }, true);
}

// ฝังสคริปต์ลงในหน้าหลักโดยตรง เพื่อให้ทำงานต่อเนื่องแม้แอปรันใหม่
const doc = window.parent.document;
if (!doc.getElementById('gq-sidebar-script')) {
  const s = doc.createElement('script');
  s.id = 'gq-sidebar-script';
  s.textContent = '(' + main.toString() + ')();';
  doc.head.appendChild(s);
}
</script>
""", height=0)

# ------------------------------------------
# MENU: หน้าแรก & สรุปผล
# ------------------------------------------
if menu == "🎯สรุปผล":
    st.subheader("🏆 สรุปเป้าหมาย")
    st.write("ยินดีต้อนรับ นี่คือภาพรวมในตอนนี้")
    
    # แสดงกล่องสถานะเงินออมปัจจุบัน
    st.metric(label="เงินเก็บปัจจุบันของคุณ", value=f"{st.session_state.balance:,.2f} บาท")
    st.text(f"🎯 Goal : {st.session_state.item_name} ราคา {st.session_state.goal:,.2f} บาท")
    
    # ตรรกะแจ้งเตือนเงินออมดั้งเดิมของคุณ
    
    far = st.session_state.goal - st.session_state.balance
    unfar = st.session_state.balance - st.session_state.goal

    if st.session_state.goal > 0:
        if far > 0:
            messages = [
                f"คุณยังขาดเงินอีก {far:,.2f} บาทนะ แล้ว **{st.session_state.item_name}** ที่คุณอยากได้ล่ะ?",
                f"ขาดอีกแค่ {far:,.2f} บาทเองงงง อีกนิดเดียวก็ได้แล้ว 🤏🤏",
                f"เอ้าท่องพร้อมกันนน เพื่อ **{st.session_state.item_name}** เพื่อ **{st.session_state.item_name}** เพื่อ **{st.session_state.item_name}** 😀",
                "อย่าเพิ่งยอมแพ้ ความสำเร็จมันต้องใช้เวลานะ! 👊",
                "วันนี้อาจยังไม่ถึง แต่คุณต้องทำได้แน่!",
                f"ลำบากตอนนี้ เดี๋ยวตอนได้ **{st.session_state.item_name}** ก็สบายแล้ววว 😣😣"
            ]
            message = random.choice(messages)
            st.info(message)

        elif far == 0:
            messages = [
                f"เย้!! คุณสามารถซื้อ **{st.session_state.item_name}** ได้แล้ว 🎉🎉",
                "ยินดีด้วยยยย คุณทำสำเร็จแล้ว!",
                "ได้แล้วววว นี่แหละชัยชนะ ฮ่าฮ่าฮ่า",
                f"เห็นมั้ยล่ะ **{st.session_state.item_name}** อยู่ใกล้แค่เอื้อมเท่านั้นแหละ",
                "สบายมาก 💪💪",
                "ได้เวลาสำหรับของชิ้นต่อไปแล้ว 🤩🤩"
            ]
            message = random.choice(messages)
            st.info(message)

        else:
            messages = [
                f"ตอนนี้คุณสามารถซื้อ **{st.session_state.item_name}** ได้เป็นร้อยอันแล้วม้าง",
                "คุณนี่อัจฉริยะด้านการเก็บเงินชัดๆ!!",
                f"ทำได้แล้วว และยังมีเงินเกินมาอีกตั้ง {unfar:,.2f} บาทแหละ",
                f"เห็นมั้ยล่ะ **{st.session_state.item_name}** อยู่ใกล้แค่เอื้อมเท่านั้นแหละ",
                "สบายมาก 💪💪",
                "คุณมีเงินเกินแล้ว ซื้อได้ทั้งบริษัทแล้วมั้งเนี่ย 💰",
                "อนาคตเศรษฐีพันล้านรึป่าวเนี่ยย 💸💸"
            ]
            message = random.choice(messages)
            st.info(message)

    st.write("---")
    st.subheader("📊 รายรับ-รายจ่าย")

    period = st.radio(
        "ช่วงเวลา",
        ["7 วัน", "30 วัน", "รายเดือน"],
        horizontal=True,
        label_visibility="collapsed"
    )

    try:
        uid = st.session_state["user_id"]

        if period == "รายเดือน":
            df = load_monthly(uid)
            if df.empty:
                st.info(
                    "ยังไม่มีสรุปรายเดือน "
                    "ข้อมูลจะถูกรวมเป็นรายเดือนเมื่อเก่ากว่า 30 วัน"
                )
            else:
                chart_df = add_balance_monthly(uid, df, st.session_state.balance)
                show_bar_chart(
                    chart_df, monthly=True,
                    goal=st.session_state.goal,
                    goal_name=st.session_state.item_name
                )
                table = df.copy()
                table.index = table.index.strftime("%m/%Y")
                table["คงเหลือ"] = table["รายรับ"] - table["รายจ่าย"]
                st.dataframe(table, use_container_width=True)
        else:
            days = 7 if period == "7 วัน" else 30
            df = load_daily_range(uid, days)

            total_in = df["รายรับ"].sum()
            total_out = df["รายจ่าย"].sum()

            c1, c2, c3 = st.columns(3)
            c1.metric("รายรับรวม", f"{total_in:,.2f}")
            c2.metric("รายจ่ายรวม", f"{total_out:,.2f}")
            c3.metric("สุทธิ", f"{total_in - total_out:,.2f}")

            if total_in == 0 and total_out == 0:
                st.info(f"ใน {days} วันที่ผ่านมายังไม่มีการบันทึก")
            else:
                chart_df = add_balance_daily(df, st.session_state.balance)
                show_bar_chart(
                    chart_df,
                    goal=st.session_state.goal,
                    goal_name=st.session_state.item_name
                )

    except Exception as e:
        st.error(f"โหลดกราฟไม่สำเร็จ: {e}")

# ------------------------------------------
# MENU: Money Line
# ------------------------------------------
elif menu == "💰 Money Line":
    st.subheader("💰 Money Line: วางแผนการเงินเพื่อเป้าหมาย")

    # ช่องรับข้อมูลเป้าหมายเฉพาะเจาะจง
    item = st.text_input(
        "คุณกำลังเก็บเงินไปเพื่อซื้ออะไร? (เช่น หูฟัง, เกม):",
        value=st.session_state.item_name
    )
    target_goal = st.number_input(
        "ของชิ้นนั้นราคากี่บาท?:",
        min_value=0.0,
        value=st.session_state.goal,
        step=100.0
    )

    if st.button("บันทึกเป้าหมายการซื้อของ"):
        try:
            supabase.table("player_data").update({
                "item": item,
                "goal": str(target_goal)
            }).eq(
                "user_id", st.session_state["user_id"]
            ).execute()

            st.session_state.item_name = item
            st.session_state.goal = target_goal

            st.success("บันทึกข้อมูลเป้าหมายใหม่เรียบร้อยแล้ว!")

        except Exception as e:
            st.error(f"บันทึกเป้าหมายไม่สำเร็จ: {e}")
    
    st.write("---")
    st.write("### บันทึกรายรับ-รายจ่าย")

    today = datetime.now(timezone(timedelta(hours=7))).date()  # เวลาไทย
    record_date = st.date_input(
        "วันที่",
        value=today,
        min_value=today - timedelta(days=30),
        max_value=today
    )
    income = st.number_input("ได้เงินกี่บาท💰:", min_value=0.0, value=0.0)
    expense = st.number_input("ใช้จ่ายกี่บาท💸:", min_value=0.0, value=0.0)

    if st.button("คำนวณและบันทึกยอดเงิน"):
        if income == 0 and expense == 0:
            st.warning("กรุณากรอกรายรับหรือรายจ่ายอย่างน้อยหนึ่งช่อง")
        else:
            try:
                uid = st.session_state["user_id"]

                # 1) บันทึกลง daily_records (ถ้ามีวันนั้นอยู่แล้วให้บวกทบ)
                existing = (
                    supabase.table("daily_records")
                    .select("income, expense")
                    .eq("user_id", uid)
                    .eq("record_date", record_date.isoformat())
                    .execute()
                )

                old_income = float(existing.data[0]["income"]) if existing.data else 0.0
                old_expense = float(existing.data[0]["expense"]) if existing.data else 0.0

                supabase.table("daily_records").upsert({
                    "user_id": uid,
                    "record_date": record_date.isoformat(),
                    "income": old_income + income,
                    "expense": old_expense + expense
                }).execute()

                # 2) อัปเดตยอดเงินเก็บปัจจุบัน
                new_balance = st.session_state.balance + income - expense

                supabase.table("player_data").update({
                    "balance": new_balance
                }).eq("user_id", uid).execute()

                st.session_state.balance = new_balance

                st.success(
                    "บันทึกเรียบร้อยแล้ว! "
                    "ลองกลับไปดูหน้าแรกเพื่อเช็กยอดเงิน"
                )

            except Exception as e:
                st.error(f"บันทึกยอดเงินไม่สำเร็จ: {e}")


    st.write("---")
    st.subheader("🧹 จัดการเงินเก็บ")

    if st.button("ล้างเงินเก็บ", key="reset_balance"):
        st.session_state["show_reset_balance_confirm"] = True					

    if st.session_state.get("show_reset_balance_confirm", False):
        st.warning(
            "⚠️ คุณกำลังจะตั้งยอดเงินเก็บเป็น 0 บาท และล้างประวัติรายรับ-รายจ่าย "
            "(รวมกราฟ) ทั้งหมด การดำเนินการนี้ไม่สามารถย้อนกลับได้ "
            "แต่ชื่อเป้าหมายและราคาเป้าหมายจะไม่ถูกลบ"
        )

        confirm_col, cancel_col = st.columns(2)

        with confirm_col:
            if st.button("ยืนยันล้างเงินเก็บ", key="btn_confirm_reset_balance"):
                try:
                    uid = st.session_state["user_id"]

                    # ล้างประวัติก่อน เพื่อให้เส้นเงินเก็บเริ่มนับใหม่จาก 0
                    supabase.table("daily_records").delete().eq("user_id", uid).execute()
                    supabase.table("monthly_records").delete().eq("user_id", uid).execute()

                    supabase.table("player_data").update({
                        "balance": 0
                    }).eq("user_id", uid).execute()

                    st.session_state.balance = 0.0
                    st.session_state["show_reset_balance_confirm"] = False
                    st.success("ล้างเงินเก็บเรียบร้อยแล้ว!")
                    st.rerun()

                except Exception as e:
                    st.error(f"ล้างเงินเก็บไม่สำเร็จ: {e}")

        with cancel_col:
            if st.button("ยกเลิก", key="btn_cancel_reset_balance"):
                st.session_state["show_reset_balance_confirm"] = False
                st.rerun()

    st.caption(
        "หมายเหตุ: ปุ่มนี้จะล้างยอดเงินเก็บและประวัติรายรับ-รายจ่ายของบัญชีที่เข้าสู่ระบบ "
        "ไม่ลบชื่อสิ่งของหรือราคาเป้าหมาย"
    )


    
# ------------------------------------------
# MENU: Health Line
# ------------------------------------------
elif menu == "💪 Health Line":
    st.subheader("เช็คลิสต์ร่างกายประจำวัน")
    st.write("🌱 สุขภาพที่ดีเริ่มจากสิ่งเล็ก ๆ ที่คุณทำในทุกวัน มาเช็คไปพร้อมกันเลย !😁")
    
        # ฟังก์ชันสุ่มข้อความและแสดงสถานะภารกิจ
    def show_health_status(key, done, total, messages, success):
        if done == total:
            st.success(success)
        else:
            if key not in st.session_state:
                st.session_state[key] = random.choice(messages)

            st.markdown(
                f"<p style='color:#e05252; font-size:12px;'>"
                f"💬 {st.session_state[key]}</p>",
                unsafe_allow_html=True
            )

        st.caption(f"ความคืบหน้า: {done}/{total}")
        st.progress(done / total)


    # 1. ภารกิจดื่มน้ำ
    with st.expander("💧 ภารกิจที่ 1: วันนี้ดื่มน้ำครบ 8 แก้วหรือยัง?"):
        st.write("เติมพลังให้ร่างกาย จิบน้ำให้เหมาะกับความต้องการของตัวเอง!")

        water_cols = st.columns(4)
        water_done = []

        for i in range(8):
            with water_cols[i % 4]:
                checked = st.checkbox(
                    f"แก้วที่ {i + 1}",
                    key=f"water_{i + 1}"
                )
                water_done.append(checked)

        water_count = sum(water_done)

        # เลือกข้อความตามจำนวนแก้ว
        if water_count == 0:
            water_message = "วันนี้คุณยังไม่ได้เช็กการดื่มน้ำเลยนะ 💧"

        elif water_count <= 3:
            water_message = "ปากแห้งเป็นทะเลทรายแล้วมั้งเนี่ย 🏜️"

        elif water_count < 8:
            # สุ่มใหม่เมื่อจำนวนแก้วเปลี่ยน
            previous_count = st.session_state.get(
                "previous_water_count", -1
            )

            if water_count != previous_count:
                st.session_state["water_tip"] = random.choice([
                    "พักแล้วจิบน้ำสักหน่อยมั้ยย 💧",
                    "น้ำช่วยให้ร่างกายทำงานได้ดีตามปกตินะ อย่าลืมล่ะ!",
                    "ไม่ต้องรีบดื่มรวดเดียว ค่อย ๆ จิบระหว่างวันเอานะ 😉😉"
                ])

            water_message = st.session_state.get(
                "water_tip",
                "พักแล้วจิบน้ำสักหน่อยมั้ยย 💧"
            )

        else:
            water_message = None

        
        # แสดงข้อความตามจำนวนแก้วและเปลี่ยนสี
        if water_count == 8:
            st.success("ภารกิจเช็กการดื่มน้ำครบแล้ว! เยี่ยมเลย 💧")

        elif water_count == 0:
            st.markdown(
                "<p style='color:#E53935; font-size:12px;'>"
                "💬 วันนี้คุณยังไม่ได้เช็กการดื่มน้ำเลยนะ 💧</p>",
                unsafe_allow_html=True
            )

        elif water_count <= 3:
            st.markdown(
                f"<p style='color:#F39C12; font-size:12px;'>"
                f"💬 {water_message}</p>",
                unsafe_allow_html=True
            )


        else:
            st.markdown(
                f"<p style='color:#3498DB; font-size:12px;'>"
                f"💬 {water_message}</p>",
                unsafe_allow_html=True
            )


        st.session_state["previous_water_count"] = water_count

        st.caption(f"ความคืบหน้า: {water_count}/8")
        st.progress(water_count / 8)



    # 2. ภารกิจรับประทานอาหาร
    with st.expander("🍚 ภารกิจที่ 2: วันนี้กินอาหารครบ 3 มื้อหรือยัง?"):
        st.write("เติมพลังงานให้ร่างกายด้วยมื้ออาหารที่หลากหลาย")

        breakfast = st.checkbox("🌅 มื้อเช้า", key="meal_breakfast")
        lunch = st.checkbox("🌄 มื้อกลางวัน", key="meal_lunch")
        dinner = st.checkbox("🌆 มื้อเย็น", key="meal_dinner")

        meal_done = [breakfast, lunch, dinner]
        meal_count = sum(meal_done)
             
        # เลือกข้อความตามจำนวนมื้อ
        if meal_count == 0:
            meal_message = "วันนี้คุณยังไม่ได้กินอะไรเลยนะ 🫩"

        elif meal_count == 1:
            meal_message = "อาหารที่หลากหลายช่วยให้ร่างกายได้รับสารอาหารที่จำเป็นนะ! 💪"

        elif meal_count == 2:
            # สุ่มใหม่เมื่อจำนวนมื้อเปลี่ยน
            previous_count = st.session_state.get(
                "previous_meal_count", -1
            )

            if meal_count != previous_count:
                st.session_state["meal_tip"] = random.choice([
                    "อีกมื้อเดียวก็ครบแล้วนะ",
                    "อย่าลืมกินอาหารให้ครบ 5 หมู่ด้วยหล่ะ 😌",
                    "อย่าลืมหาเวลากินมื้อที่เหลือนะ 😉😉"
                ])

            meal_message = st.session_state.get(
                "meal_tip",
                "อย่าลืมกินอาหารให้ครบ 5 หมู่ด้วยหล่ะ 😌"
            )

        else:
            meal_message = None


                 # แสดงข้อความตามจำนวนมื้อท่ีกินและเปลี่ยนสี
        if meal_count == 3:
            st.success("บันทึกมื้ออาหารครบทั้ง 3 มื้อแล้ว! เก่งมาก 🍚")


        elif meal_count == 0:
            st.markdown(
                "<p style='color:#E53935; font-size:12px;'>"
                "💬 วันนี้คุณยังไม่ได้กินอะไรเลยนะ 🍚</p>",
                unsafe_allow_html=True
            )

        elif meal_count == 1:
            st.markdown(
                f"<p style='color:#F39C12; font-size:12px;'>"
                f"💬 {meal_message}</p>",
                unsafe_allow_html=True
            )


        else:
            st.markdown(
                f"<p style='color:#3498DB; font-size:12px;'>"
                f"💬 {meal_message}</p>",
                unsafe_allow_html=True
            )


        st.session_state["previous_meal_count"] = meal_count

        st.caption(f"ความคืบหน้า: {meal_count}/3 มื้อ")
        st.progress(meal_count / 3)



    # 3. ภารกิจกินอาหารให้สม่ำเสมอ
    with st.expander("⏰ ภารกิจที่ 3: วันนี้ได้พักกินข้าวเป็นเวลาหรือยัง?"):
        st.write("หาเวลาพักกินอาหาร ไม่ปล่อยให้กิจกรรมต่าง ๆ เบียดเวลามื้ออาหาร")

        breakfast_time = st.checkbox(
            "จัดเวลามื้อเช้าได้เหมาะสม",
            key="time_breakfast"
        )
        lunch_time = st.checkbox(
            "มีเวลาพักกินมื้อกลางวัน",
            key="time_lunch"
        )
        dinner_time = st.checkbox(
            "จัดเวลามื้อเย็นได้เหมาะสม",
            key="time_dinner"
        )

        time_count = sum([
            breakfast_time,
            lunch_time,
            dinner_time
        ])

        show_health_status(
            "time_tip",
            time_count,
            3,
            [
                "ภารกิจในเกมรอได้ แต่ท้องร้องนี่สิไม่ยอมรอ 😂",
                "อย่าลืมพักจากการเรียนหรือเล่นเกมมากินข้าวนะ!",
                "การกินอาหารสม่ำเสมอช่วยให้จัดกิจวัตรได้ดีขึ้น 🍱"
            ],
            "วันนี้จัดเวลามื้ออาหารได้ครบแล้ว! ⏰"
        )

    # 4. ภารกิจการนอน
    with st.expander("🛌 ภารกิจที่ 4: วันนี้พักผ่อนเพียงพอหรือยัง?"):
        st.write("การนอนช่วยให้ร่างกายและสมองได้พักฟื้น")

        sleep_enough = st.checkbox(
            "เมื่อคืนได้นอนเพียงพอสำหรับตัวเอง",
            key="sleep_enough"
        )
        sleep_schedule = st.checkbox(
            "พยายามเข้านอนและตื่นให้เป็นเวลา",
            key="sleep_schedule"
        )
        screen_break = st.checkbox(
            "เตรียมตัวพักจากหน้าจอก่อนนอน",
            key="sleep_screen"
        )

        sleep_count = sum([
            sleep_enough,
            sleep_schedule,
            screen_break
        ])

        show_health_status(
            "sleep_tip",
            sleep_count,
            3,
            [
                "ตัวละครยังต้องพักฟื้น แล้วคุณล่ะ? 😂",
                "นอนดึกทุกคืน เดี๋ยวพรุ่งนี้สมองขอโหลดช้านะ 💤",
                "วัยรุ่นส่วนใหญ่มักต้องการนอนประมาณ 8–10 ชั่วโมงต่อคืน",
                "ลองวางมือถือก่อนนอน แล้วให้สมองได้พักบ้างนะ 📱"
            ],
            "ภารกิจดูแลการนอนครบแล้ว ขอให้พักผ่อนเต็มที่! 💤"
        )

    # 5. ภารกิจเคลื่อนไหวร่างกาย
    with st.expander("🚶 ภารกิจที่ 5: วันนี้ได้ขยับร่างกายหรือยัง?"):
        st.write("ไม่จำเป็นต้องออกกำลังหนัก เริ่มจากการเคลื่อนไหวที่เหมาะกับตัวเองได้")

        walk = st.checkbox(
            "🚶 เดินหรือขยับร่างกายระหว่างวัน",
            key="move_walk"
        )
        stretch = st.checkbox(
            "🙆 ยืดเหยียดร่างกาย",
            key="move_stretch"
        )
        activity = st.checkbox(
            "⚽ ทำกิจกรรมที่ชอบ เช่น เล่นกีฬา",
            key="move_activity"
        )

        move_count = sum([walk, stretch, activity])

        show_health_status(
            "move_tip",
            move_count,
            3,
            [
                "อย่านั่งนิ่งจนรากงอกเหมือนต้นไม้สิ 😂",
                "ลุกมายืดเส้นสักนิด ร่างกายจะได้เปลี่ยนอิริยาบถ!",
                "การเคลื่อนไหวสม่ำเสมอดีต่อสุขภาพนะ ไม่จำเป็นต้องหักโหม 💪"
            ],
            "ภารกิจขยับร่างกายครบแล้ว เยี่ยมมาก! 🚶"
        )

    # 6. ภารกิจพักใจ
    with st.expander("💚 ภารกิจที่ 6: วันนี้ได้ดูแลความรู้สึกตัวเองหรือยัง?"):
        st.write("การพักใจเป็นส่วนหนึ่งของการดูแลตัวเองเหมือนกันนะ")

        relax = st.checkbox(
            "หาเวลาพักจากสิ่งที่ทำอยู่",
            key="mind_relax"
        )
        enjoy = st.checkbox(
            "ทำกิจกรรมที่ทำให้ตัวเองมีความสุข",
            key="mind_enjoy"
        )
        connect = st.checkbox(
            "พูดคุยกับคนที่ไว้ใจเมื่ออยากระบาย",
            key="mind_connect"
        )

        mind_count = sum([relax, enjoy, connect])

        show_health_status(
            "mind_tip",
            mind_count,
            3,
            [
                "คุณไม่ใช่หุ่นยนต์นะ พักบ้างก็ได้ 🤖",
                "ไม่จำเป็นต้องเก่งทุกนาที แค่วันนี้ดูแลตัวเองได้ก็ดีแล้ว 💚",
                "พักใจสักนิด ไม่ใช่การแพ้ แต่เป็นการให้เวลากับตัวเอง"
            ],
            "ภารกิจดูแลใจสำเร็จแล้ว อย่าลืมใจดีกับตัวเองนะ 💚"
        )

    st.write("---")
    st.caption("💚 เช็กลิสต์นี้มีไว้ช่วยติดตามการดูแลตัวเอง การทำได้ครบทุกข้อเป็นเรื่องดี แต่สิ่งสำคัญคือการดูแลตัวเองอย่างเหมาะสมและสม่ำเสมอในทุก ๆ วันนะ!")
    
    
    if st.button("บันทึกคะแนนสุขภาพประจำวัน"):
        st.success("บันทึกพฤติกรรมเรียบร้อย! รักษาวินัยแบบนี้ในทุกๆ วันนะครับ")



# ------------------------------------------
# MENU: Studdy
# ------------------------------------------

elif menu == "📚 Study Line":
    st.subheader("📚 Study Line")
    st.info("หน้านี้กำลังพัฒนา เร็วๆ นี้")

# ==========================================
# 🧹 เมนูจัดการบัญชีและรีเซ็ตข้อมูล
# ==========================================

st.sidebar.write("---")

# แสดงบัญชีที่กำลังใช้งาน
_email = html.escape(str(st.session_state.get("user_email", "ผู้เล่น")))
st.sidebar.markdown(
    "<p style='font-size:13px; color:#5b6b82; margin:0 0 10px 0; "
    "word-break:break-all;'>บัญชีที่เข้าสู่ระบบ:<br>"
    f"<b style='color:#14213d;'>{_email}</b></p>",
    unsafe_allow_html=True
)

# ปุ่มรีเซ็ตข้อมูลทั้งหมด
if st.sidebar.button(
    "🧹 รีเซ็ตข้อมูลทั้งหมด",
    use_container_width=True
):
    st.session_state["confirm_reset_all"] = True

if st.session_state.get("confirm_reset_all", False):
    st.sidebar.warning(
        "ต้องการรีเซ็ตข้อมูลในบัญชีนี้หรือไม่? "
        "จะล้างเงินเก็บ เป้าหมาย ประวัติรายรับ-รายจ่ายทั้งหมด "
        "และกราฟ จะย้อนกลับไม่ได้"
    )

    confirm_col, cancel_col = st.sidebar.columns(2)

    with confirm_col:
        if st.button("ยืนยันรีเซ็ต", key="confirm_all_reset"):
            try:
                uid = st.session_state["user_id"]

                # 1) ล้างประวัติรายรับ-รายจ่ายก่อน (ถ้าพลาด จะยังไม่รีเซ็ตส่วนอื่น)
                supabase.table("daily_records").delete().eq("user_id", uid).execute()
                supabase.table("monthly_records").delete().eq("user_id", uid).execute()

                # 2) รีเซ็ตเงินเก็บและเป้าหมาย
                supabase.table("player_data").update({
                    "balance": 0,
                    "goal": "0",
                    "item": "สิ่งที่อยากได้"
                }).eq("user_id", uid).execute()

                st.session_state.balance = 0.0
                st.session_state.goal = 0.0
                st.session_state.item_name = "สิ่งที่อยากได้"
                st.session_state["confirm_reset_all"] = False

                st.sidebar.success("รีเซ็ตข้อมูลสำเร็จ")
                st.rerun()

            except Exception as e:
                st.sidebar.error(f"รีเซ็ตไม่สำเร็จ: {e}")

    with cancel_col:
        if st.button("ยกเลิก", key="cancel_all_reset"):
            st.session_state["confirm_reset_all"] = False
            st.rerun()

# ปุ่มออกจากระบบ
if st.sidebar.button("🚪 ออกจากระบบ", use_container_width=True):
    try:
        cookie_token = cookie_controller.get("gq_session")

        if cookie_token:
            token_hash = hashlib.sha256(
                cookie_token.encode()
            ).hexdigest()

            session_supabase.table("user_sessions") \
                .delete() \
                .eq("token_hash", token_hash) \
                .execute()

        cookie_controller.remove("gq_session")
        supabase.auth.sign_out()

    except Exception:
        pass

    for key in [
        "access_token",
        "refresh_token",
        "user_id",
        "user_email",
        "player_data_loaded",
        "balance",
        "goal",
        "item_name",
    ]:
        st.session_state.pop(key, None)
    time.sleep(1)
    st.rerun()
