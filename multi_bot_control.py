import discum
import threading
import time
import os
import random
from flask import Flask, request, render_template_string
from dotenv import load_dotenv

load_dotenv()

main_token = os.getenv("MAIN_TOKEN")
tokens = os.getenv("TOKENS").split(",")

main_channel_id = "1386973916563767396"
other_channel_id = "1387406577040101417"
ktb_channel_id = "1376777071279214662"

karuta_id = "646937666251915264"
bots = []
main_bot = None
auto_grab_enabled = False

def create_bot(token, is_main=False):
    bot = discum.Client(token=token, log=False)

    @bot.gateway.command
    def on_ready(resp):
        if resp.event.ready:
            try:
                user_id = resp.raw["user"]["id"]
                print(f"Đã đăng nhập: {user_id} {'(Acc chính)' if is_main else ''}")
            except Exception as e:
                print(f"Lỗi lấy user_id: {e}")

    @bot.gateway.command
    def on_message(resp):
        global auto_grab_enabled

        if resp.event.message:
            msg = resp.parsed.auto()
            author = msg.get("author", {}).get("id")
            content = msg.get("content", "")
            channel = msg.get("channel_id")
            mentions = msg.get("mentions", [])

            if author == karuta_id and channel == main_channel_id:

                # Trường hợp tự drop: không có "is dropping 3 cards!" và mentions rỗng
                if "is dropping" not in content and not mentions and auto_grab_enabled:
                    emoji = random.choice(["1️⃣", "2️⃣", "3️⃣"])
                    delay = {"1️⃣": 1.3, "2️⃣": 2.3, "3️⃣": 3}[emoji]
                    print(f"Phát hiện tự drop → Chọn emoji {emoji} → Grab sau {delay}s")

                    def grab():
                        try:
                            bot.addReaction(channel, msg["id"], emoji)
                            print("Đã thả emoji grab!")
                            bot.sendMessage(ktb_channel_id, "kt b")
                            print("Đã nhắn 'kt b'!")
                        except Exception as e:
                            print(f"Lỗi khi grab hoặc nhắn kt b: {e}")

                    threading.Timer(delay, grab).start()

    threading.Thread(target=bot.gateway.run, daemon=True).start()
    return bot

main_bot = create_bot(main_token, is_main=True)

for token in tokens:
    bots.append(create_bot(token))

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
<h3>Tự grab khi Karuta tự drop</h3>
<form method="POST">
    <button name="toggle" value="on" type="submit">Bật</button>
    <button name="toggle" value="off" type="submit">Tắt</button>
</form>
<p>Trạng thái hiện tại: <b>{status}</b></p>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    global auto_grab_enabled
    msg_status = ""

    if request.method == "POST":
        msg = request.form.get("message")
        quickmsg = request.form.get("quickmsg")
        toggle = request.form.get("toggle")

        if msg:
            for idx, bot in enumerate(bots):
                try:
                    threading.Timer(2 * idx, bot.sendMessage, args=(other_channel_id, msg)).start()
                except Exception as e:
                    print(f"Lỗi gửi tin nhắn: {e}")
            msg_status = "Đã gửi thủ công thành công!"

        if quickmsg:
            for idx, bot in enumerate(bots):
                try:
                    threading.Timer(2 * idx, bot.sendMessage, args=(other_channel_id, quickmsg)).start()
                except Exception as e:
                    print(f"Lỗi gửi tin nhắn: {e}")
            msg_status = f"Đã gửi lệnh {quickmsg} thành công!"

        if toggle:
            auto_grab_enabled = toggle == "on"
            msg_status = f"Tự grab {'đã bật' if auto_grab_enabled else 'đã tắt'}"

    status = "Đang bật" if auto_grab_enabled else "Đang tắt"
    return HTML.format(status=status) + (f"<p>{msg_status}</p>" if msg_status else "")

def keep_alive():
    app.run(host="0.0.0.0", port=8080)

threading.Thread(target=keep_alive, daemon=True).start()

while True:
    time.sleep(60)
