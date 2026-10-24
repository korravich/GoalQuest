"""Korvian: ไฟล์หลัก (จุดเริ่มต้นของแอป)

โครงสร้างไฟล์:
  app.py      ตั้งค่าหน้าเว็บ, หน้าล็อกอิน, เลือกหน้าที่จะแสดง   <- ไฟล์นี้
  db.py       Supabase, ล็อกอินค้าง, ดึงข้อมูลรายรับ-รายจ่าย
  sidebar.py  เมนูด้านข้าง, โลโก้, ปุ่มบัญชี
  views.py    เนื้อหาของแต่ละหน้า + กราฟ
"""
import os
import time

import streamlit as st
from PIL import Image
from streamlit_cookies_controller import CookieController

import db
import sidebar
import views

# ไอคอนแท็บเบราว์เซอร์ (ถ้าหาไฟล์ไม่เจอ ใช้อิโมจิแทน)
try:
    _icon = Image.open(os.path.join(os.path.dirname(__file__), "korvian_icon.png"))
except Exception:
    _icon = "🌀"

# ต้องเป็นคำสั่ง Streamlit คำสั่งแรกของแอป
st.set_page_config(
    page_title="Korvian",
    page_icon=_icon,
    layout="wide",
    initial_sidebar_state="expanded"
)
st.markdown(
    "<style>[data-testid='stMainBlockContainer'], .block-container "
    "{ padding-bottom: 4rem !important; }</style>",
    unsafe_allow_html=True
)

# เมนูแต่ละอันไปที่ฟังก์ชันไหน (ชื่อต้องตรงกับ MENU_ITEMS ใน sidebar.py)
PAGES = {
    "🎯สรุปผล": views.summary_page,
    "💰 Money Line": views.money_page,
    "💪 Health Line": views.health_page,
    "📚 Study Line": views.study_page,
}


# ==========================================
# หน้าสมัครสมาชิก / เข้าสู่ระบบ
# ==========================================

def _finish_login(cookie_controller, result):
    """เก็บผลล็อกอิน + จำการล็อกอินไว้ในคุกกี้ แล้วรีเฟรชหน้า"""
    db.store_login(result)
    db.save_persistent_session(
        cookie_controller,
        result.user.id,
        result.session.access_token,
        result.session.refresh_token
    )


def login_screen(cookie_controller):
    st.markdown(
        "<div style='display:flex;align-items:center;gap:14px;margin-bottom:4px;'>"
        "<div style='background:#06060a;border-radius:16px;padding:10px;display:flex;'>"
        + sidebar.korvian_logo_svg(44) +
        "</div>"
        "<span style='font-size:44px;font-weight:800;letter-spacing:2px;'>Korvian</span>"
        "</div>",
        unsafe_allow_html=True
    )
    st.caption("Your Future Depends on What You Do Today (v1.1)")
    st.subheader("Start your goals")

    login_tab, signup_tab = st.tabs(["เข้าสู่ระบบ", "สมัครสมาชิก"])

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
                result = db.user_client().auth.sign_in_with_password({
                    "email": login_email.strip(),
                    "password": login_password
                })

                if result.user and result.session:
                    _finish_login(cookie_controller, result)
                    time.sleep(1)
                    st.rerun()

            except Exception:
                st.error("เข้าสู่ระบบไม่สำเร็จ โปรดตรวจสอบอีเมล รหัสผ่าน หรือการยืนยันอีเมล")

    with signup_tab:
        with st.form("signup_form"):
            signup_email = st.text_input("อีเมลสำหรับสมัคร")
            signup_password = st.text_input("ตั้งรหัสผ่าน", type="password")
            signup_password_again = st.text_input("ยืนยันรหัสผ่าน", type="password")
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
                    result = db.user_client().auth.sign_up({
                        "email": signup_email.strip(),
                        "password": signup_password
                    })

                    if result.session and result.user:
                        _finish_login(cookie_controller, result)
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


# ==========================================
# ลำดับการทำงานของแอป
# ==========================================

cookie_controller = CookieController()

db.restore_login(cookie_controller)   # มีคุกกี้ -> คืนสถานะล็อกอิน
db.apply_session()

if "user_id" not in st.session_state:
    login_screen(cookie_controller)
    st.stop()   # ยังไม่ล็อกอิน ห้ามแสดงส่วนเกมด้านล่าง

try:
    db.load_player_data()
except Exception as e:
    st.error(f"โหลดข้อมูลไม่สำเร็จ: {e}")
    st.stop()

menu = sidebar.render_menu()
PAGES[menu]()
sidebar.render_account(cookie_controller)
