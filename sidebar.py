"""Korvian: sidebar (เมนูการ์ด, เลื่อนเข้า-ออก, ปุ่มบัญชี) และโลโก้

เพิ่มเมนูใหม่: เติมรายการใน MENU_ITEMS ที่นี่ + เติมใน PAGES ที่ app.py
"""
import html
import time

import streamlit as st
import streamlit.components.v1 as components

import db


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


# ชื่อเมนู, คำอธิบายใต้ชื่อ, สีพื้นกล่องไอคอน, ไอคอน SVG (เข้ารหัสสำหรับใส่ใน CSS)
MENU_ITEMS = [
    (
        "🎯สรุปผล", "ดูภาพรวมเป้าหมายของคุณ", "#cfe3ff",
        "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%232f6fd6' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M4 20h16M7 20v-6M12 20V8M17 20v-9'/%3E%3C/svg%3E",
    ),
    (
        "💰 Money Line", "วางแผนเงินเก็บของคุณ", "#fff0bf",
        "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23d99a00' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect x='3' y='7' width='18' height='13' rx='3'/%3E%3Cpath d='M5 7l10-3v3'/%3E%3Crect x='14' y='11' width='7' height='5' rx='2.5'/%3E%3Cpath d='M17.5 13.5h.01'/%3E%3C/svg%3E",
    ),
    (
        "💪 Health Line", "ติดตามการดูแลตัวเอง", "#d3f4e2",
        "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%231f9d6b' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M12 20s-8-5-8-11a4.5 4.5 0 018-2.8A4.5 4.5 0 0120 9c0 6-8 11-8 11z'/%3E%3C/svg%3E",
    ),
    (
        "📚 Study Line", "เร็วๆ นี้", "#e6dcfb",
        "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%237c4dcc' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M12 6c-2-1.5-5-2-8-2v13c3 0 6 .5 8 2 2-1.5 5-2 8-2V4c-3 0-6 .5-8 2zM12 6v13'/%3E%3C/svg%3E",
    ),
]


# ==========================================
# CSS
# ==========================================

_BASE_CSS = """
section[data-testid="stSidebar"] { background: #f1f5fb; }

/* ===== แถบชื่อด้านบน ===== */
.gq-banner {
    background: #06060a; border-radius: 14px;
    padding: 14px 16px; margin: 0 0 18px 0;
    width: 100% !important; box-sizing: border-box !important;
}
.gq-row { display: flex; align-items: center; gap: 10px; }
.gq-banner b { color: #fff !important; font-size: 20px; }
.gq-banner span { color: #dbe6f7 !important; font-size: 13px; display: block; margin-top: 4px; }
.gq-title {
    font-size: 20px !important; font-weight: 300 !important;
    color: #050b1a !important; opacity: 1 !important;
    letter-spacing: 2px; line-height: 1.1; margin: 0 0 6px 0;
}
.gq-sub { font-size: 14px; color: #5b6b82 !important; margin-bottom: 10px; }

/* ===== ให้ทุกชั้นที่ครอบเมนูยืดเต็มความกว้าง ===== */
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"],
section[data-testid="stSidebar"] [data-testid="stElementContainer"],
section[data-testid="stSidebar"] [data-testid="stRadio"],
section[data-testid="stSidebar"] [data-testid="stRadio"] > div,
section[data-testid="stSidebar"] div[role="radiogroup"] {
    width: 100% !important;
    max-width: 100% !important;
}
section[data-testid="stSidebar"] div[role="radiogroup"] {
    display: flex !important;
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 10px;
}

/* ===== การ์ดเมนู ===== */
section[data-testid="stSidebar"] div[role="radiogroup"] label {
    display: flex !important; align-items: center !important;
    width: 100% !important; box-sizing: border-box !important;
    margin-left: 0 !important; margin-right: 0 !important;
    min-height: 76px !important; padding: 12px 14px !important;
    background: #fff !important;
    border: 1px solid #e3eaf4 !important;
    border-radius: 14px !important;
    transition: background-color .2s, border-color .2s;
    cursor: pointer;
}
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
    border-color: #75baff !important;
}

/* ไฮไลต์หน้าที่เลือกอยู่ (แยกเป็น 2 กฎ ไม่ให้เบราว์เซอร์ทิ้งทั้งกฎ) */
section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
    background: #dbeafe !important;
    border-color: #4b91e6 !important;
}
section[data-testid="stSidebar"] label[data-testid="stRadioOption"][data-selected="true"] {
    background: #dbeafe !important;
    border-color: #4b91e6 !important;
}

/* ซ่อนวงกลมของ radio */
section[data-testid="stSidebar"] label[data-testid="stRadioOption"] > div > div:first-child,
section[data-testid="stSidebar"] label[data-baseweb="radio"] > div:first-child {
    display: none !important;
}

/* กล่องไอคอนด้านซ้าย (สี/รูปของแต่ละใบมาจาก MENU_ITEMS) */
section[data-testid="stSidebar"] div[role="radiogroup"] label::before {
    content: ""; flex: none;
    width: 50px !important; height: 50px !important;
    margin-right: 14px; border-radius: 12px;
    background-repeat: no-repeat; background-position: center;
    background-size: 28px !important;
}

/* ลูกศรด้านขวา */
section[data-testid="stSidebar"] div[role="radiogroup"] label::after {
    content: "›"; margin-left: auto; font-size: 26px; color: #7a8aa3;
}

/* ชื่อเมนู + คำอธิบายบรรทัดที่สอง */
section[data-testid="stSidebar"] div[role="radiogroup"] label p {
    font-size: 18px !important; font-weight: 700 !important;
    margin: 0 !important; color: #14213d;
}
section[data-testid="stSidebar"] div[role="radiogroup"] label p::after {
    display: block; font-size: 14px !important; font-weight: 400; color: #5b6b82;
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

/* ตอนขยายเต็มจอ: เว้นขอบที่ตัวครอบ (ไม่ใช่ที่ตัวการ์ด) ทุกอันจึงกว้างเท่ากัน */
section[data-testid="stSidebar"].gq-full [data-testid="stSidebarUserContent"] {
    padding-left: 5vw !important;
    padding-right: 5vw !important;
}

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
"""


def _menu_item_css():
    """สร้าง CSS ไอคอน + คำอธิบายของการ์ดแต่ละใบจาก MENU_ITEMS
    (เขียนสองรูปแบบ selector เพื่อรองรับโครงสร้างของ Streamlit ทั้งสองแบบ)"""
    rules = []
    for i, (_name, desc, icon_bg, icon_svg) in enumerate(MENU_ITEMS, start=1):
        a = f'section[data-testid="stSidebar"] div[role="radiogroup"] > label:nth-child({i})'
        b = f'section[data-testid="stSidebar"] div[role="radiogroup"] > *:nth-child({i}) label'
        rules.append(
            f'{a}::before, {b}::before {{ '
            f'background-color: {icon_bg}; '
            f'background-image: url("data:image/svg+xml,{icon_svg}"); }}'
        )
        rules.append(f'{a} p::after, {b} p::after {{ content: "{desc}"; }}')
    return "\n".join(rules)


def _style_block():
    return f"<style>{_BASE_CSS}\n{_menu_item_css()}\n</style>"


# ==========================================
# JavaScript: sidebar เลื่อนเข้า-ออกเอง + ขยายเต็มจอตอนเปลี่ยนหน้า
# ==========================================

_JS = """
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
"""


# ==========================================
# ส่วนที่ app.py เรียกใช้
# ==========================================

def render_menu():
    """วาด sidebar (สไตล์ + แถบชื่อ + เมนู) แล้วคืนชื่อเมนูที่เลือก"""
    st.sidebar.markdown(_style_block(), unsafe_allow_html=True)

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
        [item[0] for item in MENU_ITEMS],
        label_visibility="collapsed"
    )
    components.html(_JS, height=0)
    return menu


def render_account(cookie_controller):
    """ส่วนล่างของ sidebar: บัญชีที่ล็อกอิน, รีเซ็ตข้อมูล, ออกจากระบบ"""
    st.sidebar.write("---")

    email = html.escape(str(st.session_state.get("user_email", "ผู้เล่น")))
    st.sidebar.markdown(
        "<p style='font-size:13px; color:#5b6b82; margin:0 0 10px 0; "
        "word-break:break-all;'>บัญชีที่เข้าสู่ระบบ:<br>"
        f"<b style='color:#14213d;'>{email}</b></p>",
        unsafe_allow_html=True
    )

    # ----- รีเซ็ตข้อมูลทั้งหมด -----
    if st.sidebar.button("🧹 รีเซ็ตข้อมูลทั้งหมด", use_container_width=True):
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

                    # ล้างประวัติก่อน (ถ้าพลาด จะยังไม่รีเซ็ตส่วนอื่น)
                    db.clear_history(uid)

                    db.user_client().table("player_data").update({
                        "balance": 0,
                        "goal": "0",
                        "item": "สิ่งที่อยากได้",
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

    # ----- ออกจากระบบ -----
    if st.sidebar.button("🚪 ออกจากระบบ", use_container_width=True):
        try:
            cookie_token = cookie_controller.get(db.COOKIE_NAME)
            if cookie_token:
                db.delete_saved_session(cookie_token)

            cookie_controller.remove(db.COOKIE_NAME)
            db.user_client().auth.sign_out()
        except Exception:
            pass

        # ล้างทุกอย่างใน session รวมถึงช่องติ๊กสุขภาพ กันข้อมูลคนก่อนค้างอยู่
        db.clear_session_state()
        time.sleep(1)
        st.rerun()
