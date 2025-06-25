import discum
import threading
import time
import os
import random
from flask import Flask, request, render_template_string
from dotenv import load_dotenv

load_dotenv()

tokens = os.getenv("TOKENS").split(",")
main_token = os.getenv("MAIN_TOKEN")
channel_id = "1387406577040101417"  # Channel của acc phụ
main_channel_id = "1386973916563767396"  # Channel acc chính grab
ktb_channel_id = "1376777071279214662"  # Kênh nhắn kt b sau khi grab

bots = []
main_bot = None
emoji_grab_times = {"1️⃣": 1.3, "2️⃣": 2.3, "3️⃣": 3.0}

# Công tắc bật/tắt tự grab acc chính
auto_grab = False

app = Flask(__name__)

HTML = """
<h2>Điều khiển bot nhắn tin</h2>
<form method="POST">
    <input type="text" name="message" placeholder="Nhập nội dung..." style="width:300px">
    <button type="submit">Gửi thủ công</button>
</form>
<hr>
<h3>Menu nhanh</h3>
<form method="POST">
    <select name="quickmsg">
        <option value="kc o:w">kc o:w</option>
        <option value="kc o:ef">kc o:ef</option>
        <option value="kc o:p">kc o:p</option>
        <option value="kc e:1">kc e:1</option>
        <option value="kc e:2">kc e:2</option>
        <option value="kc e:3">kc e:3</option>
        <option value="kc e:4">kc e:4</option>
        <option value="kc e:5">kc e:5</option>
        <option value="kc e:6">kc e:6</option>
        <option value="kc e:7">kc e:7</option>
    </select>
    <button type="submit">Gửi</button>
</form>
<hr>
<h3>Công tắc tự grab acc chính</h3>
<form method="POST">
    <button type="submit" name="toggle" value="1">Bật/Tắt</button>
</form>
<p>Trạng thái hiện tại: {}</p>
"""

def create_bot(token):
    bot = discum.Client(token=token, log=False)

    @bot.gateway.command
    def on_ready(resp):
        if resp.event.ready:
            try:
                user_id = resp.raw["user"]["id"]
                print(f"Đã đăng nhập: {user_id}")
            except Exception as e:
                print(f"Lỗi lấy user_id: {e}")

    threading.Thread(target=bot.gateway.run, daemon=True).start()
    return bot

# Tạo bot acc phụ
for token in tokens:
    bots.append(create_bot(token))

# Bot acc chính
def create_main_bot():
    global main_bot
    main_bot = discum.Client(token=main_token, log=False)

    @main_bot.gateway.command
    def on_ready(resp):
        if resp.event.ready:
            try:
                user_id = resp.raw["user"]["id"]
                print(f"Acc chính đã đăng nhập: {user_id}")
            except Exception as e:
                print(f"Lỗi lấy user_id acc chính: {e}")

    @main_bot.gateway.command
    def on_message(resp):
        global auto_grab
        if resp.event.message and auto_grab:
            msg = resp.parsed.auto()
            author = msg.get("author", {}).get("id")
            content = msg.get("content", "")
            mentions = msg.get("mentions", [])
            if author == "646937666251915264" and "is dropping 3 cards!" in content:
                if msg.get("channel_id") == main_channel_id and not mentions:
                    emoji = random.choice(list(emoji_grab_times.keys()))
                    time.sleep(emoji_grab_times[emoji])
                    main_bot.addReaction(msg["channel_id"], msg["id"], emoji)
                    print(f"[Acc chính] → Thả reaction {emoji}")
                    try:
                        main_bot.sendMessage(ktb_channel_id, "kt b")
                        print("[Acc chính] → Nhắn 'kt b' sau khi grab")
                    except Exception as e:
                        print(f"Lỗi nhắn kt b: {e}")

    threading.Thread(target=main_bot.gateway.run, daemon=True).start()

create_main_bot()

@app.route("/", methods=["GET", "POST"])
def index():
    global auto_grab
    msg = request.form.get("message")
    quickmsg = request.form.get("quickmsg")
    toggle = request.form.get("toggle")

    if msg:
        for idx, bot in enumerate(bots):
            try:
                threading.Timer(2 * idx, bot.sendMessage, args=(channel_id, msg)).start()
            except Exception as e:
                print(f"Lỗi gửi tin nhắn: {e}")
        return HTML.format("Bật" if auto_grab else "Tắt") + "<p>Đã gửi thủ công thành công!</p>"

    if quickmsg:
        for idx, bot in enumerate(bots):
            try:
                threading.Timer(2 * idx, bot.sendMessage, args=(channel_id, quickmsg)).start()
            except Exception as e:
                print(f"Lỗi gửi tin nhắn: {e}")
        return HTML.format("Bật" if auto_grab else "Tắt") + f"<p>Đã gửi lệnh {quickmsg} thành công!</p>"

    if toggle:
        auto_grab = not auto_grab
        print(f"Tự grab acc chính: {'Bật' if auto_grab else 'Tắt'}")
        return HTML.format("Bật" if auto_grab else "Tắt") + "<p>Đã đổi trạng thái tự grab acc chính!</p>"

    return HTML.format("Bật" if auto_grab else "Tắt")

def keep_alive():
    app.run(host="0.0.0.0", port=8080)

threading.Thread(target=keep_alive, daemon=True).start()

while True:
    time.sleep(5)
