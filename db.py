"""Korvian: ฐานข้อมูล (Supabase), ล็อกอินค้าง และฟังก์ชันดึงข้อมูลสำหรับกราฟ

สำคัญ: ห้ามเก็บ client ของผู้ใช้ไว้ในตัวแปรระดับไฟล์ (module level)
ไฟล์ที่ถูก import แล้วจะถูกใช้ร่วมกันทุกผู้ใช้ ถ้าเก็บ session ไว้ตรงนั้น
ข้อมูลของคนหนึ่งอาจไปปนกับอีกคน จึงเก็บใน st.session_state (แยกตามผู้ใช้) เท่านั้น
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st
from supabase import create_client

COOKIE_NAME = "gq_session"
SESSION_DAYS = 30
TH_TZ = timezone(timedelta(hours=7))  # เวลาไทย


def today_th():
    return datetime.now(TH_TZ).date()


# ==========================================
# Supabase clients
# ==========================================

@st.cache_resource
def admin_client():
    """service role: ไม่มี session ผู้ใช้ติดอยู่ จึงใช้ร่วมกันได้อย่างปลอดภัย"""
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SERVICE_ROLE_KEY"],
    )


def user_client():
    """client ของผู้ใช้ เก็บแยกตาม session ของแต่ละคน"""
    if "_user_client" not in st.session_state:
        st.session_state["_user_client"] = create_client(
            st.secrets["SUPABASE_URL"],
            st.secrets["SUPABASE_KEY"],
        )
    return st.session_state["_user_client"]


def clear_session_state():
    """ล้างทุกอย่างใน session (ใช้ตอนออกจากระบบ กันข้อมูลคนก่อนค้างอยู่)"""
    for key in list(st.session_state.keys()):
        try:
            del st.session_state[key]
        except Exception:
            pass


# ==========================================
# ล็อกอินและล็อกอินค้าง (คุกกี้ + ตาราง user_sessions)
# ==========================================

def store_login(result):
    """เก็บผลการล็อกอิน/สมัครสมาชิกลง session_state"""
    st.session_state["user_id"] = result.user.id
    st.session_state["user_email"] = result.user.email or ""
    st.session_state["access_token"] = result.session.access_token
    st.session_state["refresh_token"] = result.session.refresh_token


def save_persistent_session(cookie_controller, user_id, access_token, refresh_token):
    try:
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)

        admin_client().table("user_sessions").insert({
            "user_id": user_id,
            "token_hash": token_hash,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires.isoformat(),
        }).execute()

        cookie_controller.set(
            COOKIE_NAME,
            token,
            max_age=SESSION_DAYS * 24 * 60 * 60,
            secure=True,
            same_site="none",
        )
    except Exception as e:
        st.error(f"บันทึก session ไม่สำเร็จ: {e}")


def restore_login(cookie_controller):
    """ถ้ายังไม่ได้ล็อกอินแต่มีคุกกี้ ให้คืนสถานะล็อกอินและต่ออายุ token"""
    cookie_token = cookie_controller.get(COOKIE_NAME)
    if "user_id" in st.session_state or not cookie_token:
        return

    try:
        token_hash = hashlib.sha256(cookie_token.encode()).hexdigest()

        response = (
            admin_client().table("user_sessions")
            .select("*")
            .eq("token_hash", token_hash)
            .gt("expires_at", datetime.now(timezone.utc).isoformat())
            .maybe_single()
            .execute()
        )
        saved = response.data if response else None
        if not saved:
            return

        # ใช้ refresh token ขอ token ชุดใหม่ แล้วเก็บทับลงตาราง
        refreshed = user_client().auth.refresh_session(saved["refresh_token"])
        if refreshed.session and refreshed.user:
            admin_client().table("user_sessions").update({
                "access_token": refreshed.session.access_token,
                "refresh_token": refreshed.session.refresh_token,
            }).eq("token_hash", token_hash).execute()

            store_login(refreshed)
    except Exception:
        pass


def delete_saved_session(cookie_token):
    token_hash = hashlib.sha256(cookie_token.encode()).hexdigest()
    admin_client().table("user_sessions") \
        .delete() \
        .eq("token_hash", token_hash) \
        .execute()


def apply_session():
    """ใส่ session ของผู้ใช้ให้ client ทุกครั้งที่หน้าเว็บรันใหม่"""
    s = st.session_state
    if all(k in s for k in ("user_id", "access_token", "refresh_token")):
        try:
            user_client().auth.set_session(s["access_token"], s["refresh_token"])
        except Exception:
            pass


# ==========================================
# ข้อมูลผู้เล่น
# ==========================================

def load_player_data():
    """โหลดข้อมูลผู้เล่นเข้า session_state (ทำครั้งเดียวต่อการล็อกอิน)
    ถ้าพลาด จะ raise error ให้ฝั่งเรียกใช้แสดงข้อความ"""
    if "player_data_loaded" in st.session_state:
        return

    uid = st.session_state["user_id"]
    sb = user_client()

    response = sb.table("player_data").select("*").eq("user_id", uid).execute()

    if response.data:
        player = response.data[0]
    else:
        player = {
            "user_id": uid,
            "balance": 0,
            "goal": "0",
            "item": "สิ่งที่อยากได้",
        }
        sb.table("player_data").insert(player).execute()

    st.session_state.balance = float(player["balance"])
    st.session_state.goal = float(player["goal"])
    st.session_state.item_name = player["item"]
    st.session_state.player_data_loaded = True

    # รวมยอดเก่าเข้ารายเดือน (ทำครั้งเดียวตอนเปิดแอป)
    try:
        compact_old_records(uid)
    except Exception as e:
        st.warning(f"รวมยอดข้อมูลเก่าไม่สำเร็จ: {e}")


def clear_history(uid):
    """ล้างประวัติรายรับ-รายจ่ายทั้งหมด (รายวัน + รายเดือน)"""
    sb = user_client()
    sb.table("daily_records").delete().eq("user_id", uid).execute()
    sb.table("monthly_records").delete().eq("user_id", uid).execute()


# ==========================================
# รายรับ-รายจ่าย
# ==========================================

def compact_old_records(uid):
    """รวมยอดรายวันที่เก่ากว่า 30 วันเข้ารายเดือน แล้วลบแถวรายวันทิ้ง"""
    sb = user_client()
    cutoff = today_th() - timedelta(days=30)

    old = (
        sb.table("daily_records")
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
            sb.table("monthly_records")
            .select("income, expense")
            .eq("user_id", uid)
            .eq("month", month_key)
            .execute()
        )
        old_inc = float(existing.data[0]["income"]) if existing.data else 0.0
        old_exp = float(existing.data[0]["expense"]) if existing.data else 0.0

        sb.table("monthly_records").upsert({
            "user_id": uid,
            "month": month_key,
            "income": old_inc + t["income"],
            "expense": old_exp + t["expense"],
        }).execute()

    # ลบแถวรายวันที่รวมแล้ว (ลบหลังรวมสำเร็จเท่านั้น)
    sb.table("daily_records") \
        .delete() \
        .eq("user_id", uid) \
        .lt("record_date", cutoff.isoformat()) \
        .execute()


def load_daily_range(uid, days):
    """ดึงรายรับ-รายจ่ายรายวันย้อนหลัง days วัน (วันที่ไม่มีข้อมูลเป็น 0)"""
    today = today_th()
    start = today - timedelta(days=days - 1)

    res = (
        user_client().table("daily_records")
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
        user_client().table("monthly_records")
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
        user_client().table("daily_records")
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
