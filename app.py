import streamlit as st
import os
import random

# ตั้งค่าหน้าตาของเว็บไซต์ให้น่ารักและจัดกึ่งกลาง
st.set_page_config(page_title="Goal Quest", page_icon="⚔️", layout="centered")
st.title("⚔️ Goal Quest ⚔️")
st.caption("Your Future Depends on What You Do Today (beta)")
st.write("---")

# ==========================================
# 💾 ระบบหลังบ้าน: โหลดข้อมูลจากไฟล์ .txt
# ==========================================
if "balance" not in st.session_state:
    try:
        with open("money.txt", "r", encoding="utf-8") as file:
            st.session_state.balance = float(file.read())
    except FileNotFoundError:
        st.session_state.balance = 0.0

if "goal" not in st.session_state:
    try:
        with open("goal.txt", "r", encoding="utf-8") as file:
            st.session_state.goal = float(file.read())
    except FileNotFoundError:
        st.session_state.goal = 0.0

if "item_name" not in st.session_state:
    try:
        with open("item.txt", "r", encoding="utf-8") as file:
            st.session_state.item_name = file.read()
    except FileNotFoundError:
        st.session_state.item_name = "สิ่งที่อยากได้"

# ==========================================
# 🧭 ระบบเมนูหลัก (Sidebar ด้านข้าง)
# ==========================================
menu = st.sidebar.radio("Quest", ["🎯สรุปผล", "💰 Money Line", "💪 Health Line"])

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
                f"เอ้าท่องพร้อมกันนน เพื่อ **{st.session_state.item_name}** เพื่อ **{st.session_state.item_name}** 😀",
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

# ------------------------------------------
# MENU: Money Line
# ------------------------------------------
elif menu == "💰 Money Line":
    st.subheader("💰 Money Line: วางแผนการเงินเพื่อเป้าหมาย")
    
    # ช่องรับข้อมูลเป้าหมายเฉพาะเจาะจง
    item = st.text_input("คุณกำลังเก็บเงินไปเพื่อซื้ออะไร? (เช่น หูฟัง, เกม):", value=st.session_state.item_name)
    target_goal = st.number_input("ของชิ้นนั้นราคากี่บาท?:", min_value=0.0, value=st.session_state.goal, step=100.0)
    
    if st.button("บันทึกเป้าหมายการซื้อของ"):
        st.session_state.item_name = item
        st.session_state.goal = target_goal
        with open("item.txt", "w", encoding="utf-8") as file:
            file.write(item)
        with open("goal.txt", "w", encoding="utf-8") as file:
            file.write(str(target_goal))
        st.success("บันทึกข้อมูลเป้าหมายใหม่เรียบร้อยแล้ว!")
    
    st.write("---")
    st.write("### บันทึกรายรับ-รายจ่ายของวันนี้")
    income = st.number_input("วันนี้ได้เงินกี่บาท💰:", min_value=0.0, value=0.0)
    expense = st.number_input("วันนี้ใช้จ่ายกี่บาท💸:", min_value=0.0, value=0.0)
    
    if st.button("คำนวณและบันทึกยอดเงินวันนี้"):
        # ตรรกะบวกสมุดบัญชีเดิมของคุณ
        st.session_state.balance = st.session_state.balance + income - expense
        with open("money.txt", "w", encoding="utf-8") as file:
            file.write(str(st.session_state.balance))
            
        st.success("อัปเดตกระเป๋าเงินออนไลน์เรียบร้อยแล้ว! ลองกลับไปดูหน้าแรกเพื่อเช็คสถานะเป้าหมาย")

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

        
# 1. ภารกิจดื่มน้ำ
with st.expander("💧 ภารกิจที่ 1: วันนี้ดื่มน้ำครบ 8 แก้วหรือยัง?"):
    st.write("เติมพลังให้ร่างกาย จิบน้ำให้เหมาะกับความต้องการของตัวเอง!")

    # สร้างช่องเช็กและแบ่งเป็น 4 คอลัมน์
    water_cols = st.columns(4)
    water_done = []

    for i in range(8):
        with water_cols[i % 4]:
            checked = st.checkbox(
                f"แก้วที่ {i + 1}",
                key=f"water_{i + 1}",
                on_change=lambda: st.session_state.update(
                    water_tip=random.choice([
                        "พักแล้วจิบน้ำสักหน่อยมั้ยย 💧",
                        "น้ำช่วยให้ร่างกายทำงานได้ดีตามปกตินะ อย่าลืมล่ะ!",
                        "ไม่ต้องรีบดื่มรวดเดียว ค่อย ๆ จิบระหว่างวันเอานะ 😉😉"
                    ])
                )
            )
            water_done.append(checked)

    water_count = sum(water_done)

    if water_count == 0:
        st.markdown(
            "<p style='color:#e05252; font-size:12px;'>"
            "💬 วันนี้คุณยังไม่ได้ดื่มน้ำเลยนะ 💧</p>",
            unsafe_allow_html=True
        )

    elif water_count <= 3:
        st.markdown(
            "<p style='color:#e05252; font-size:12px;'>"
            "💬 ปากแห้งเป็นทะเลทรายแล้วมั้งเนี่ย 🏜️</p>",
            unsafe_allow_html=True
        )

    elif water_count < 8:
        if "water_tip" not in st.session_state:
            st.session_state.water_tip = random.choice([
                "พักแล้วจิบน้ำสักหน่อยมั้ยย 💧",
                "น้ำช่วยให้ร่างกายทำงานได้ดีตามปกตินะ อย่าลืมล่ะ!",
                "ไม่ต้องรีบดื่มรวดเดียว ค่อย ๆ จิบระหว่างวันเอานะ 😉😉"
            ])

        st.markdown(
            f"<p style='color:#e05252; font-size:12px;'>"
            f"💬 {st.session_state.water_tip}</p>",
            unsafe_allow_html=True
        )

    else:
        st.success("ภารกิจเช็กการดื่มน้ำครบแล้ว! เยี่ยมเลย 💧")

    st.caption(f"ความคืบหน้า: {water_count}/8")
    st.progress(water_count / 8)


    # 2. ภารกิจรับประทานอาหาร
    with st.expander("🍚 ภารกิจที่ 2: วันนี้กินอาหารครบหรือยัง?"):
        st.write("เติมพลังงานให้ร่างกายด้วยมื้ออาหารที่หลากหลาย")

        breakfast = st.checkbox("🌅 มื้อเช้า", key="meal_breakfast")
        lunch = st.checkbox("☀️ มื้อกลางวัน", key="meal_lunch")
        dinner = st.checkbox("🌙 มื้อเย็น", key="meal_dinner")

        meal_count = sum([breakfast, lunch, dinner])

        show_health_status(
            "meal_tip",
            meal_count,
            3,
            [
                "ร่างกายไม่ใช่เครื่องเกมที่ใช้พลังงานฟรีนะ 😂",
                "อย่าปล่อยให้ความหิวเป็นบอสใหญ่ประจำวัน 🍚",
                "อาหารที่หลากหลายช่วยให้ร่างกายได้รับสารอาหารที่จำเป็นนะ!",
                "ยุ่งแค่ไหนก็หาเวลาดูแลท้องตัวเองด้วยนะ 🍱"
            ],
            "บันทึกมื้ออาหารครบทั้ง 3 มื้อแล้ว! เก่งมาก 🍚"
        )

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
# 🧹 ปุ่มล้างข้อมูลทั้งหมด (เมนูด้านซ้ายล่าง)
# ------------------------------------------
st.sidebar.write("---")
if st.sidebar.button("🧹 รีเซ็ตข้อมูลทั้งหมด"):
    for f in ["money.txt", "goal.txt", "item.txt"]:
        if os.path.exists(f):
            os.remove(f)
    st.session_state.balance = 0.0
    st.session_state.goal = 0.0
    st.session_state.item_name = "สิ่งที่อยากได้"
    st.sidebar.warning("ล้างข้อมูลเรียบร้อยแล้ว!")
    st.rerun()