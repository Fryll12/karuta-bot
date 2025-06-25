import discum
import threading
import time
import os
from flask import Flask, request, render_template_string
from dotenv import load_dotenv

load_dotenv()

tokens = os.getenv("TOKENS").split(",")

channel_id = "1387406577040101417"
bots = []

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
"""

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        msg = request.form.get("message")
        quickmsg = request.form.get("quickmsg")

        if msg:
            for idx, bot in enumerate(bots):
                try:
                    threading.Timer(2 * idx, bot.sendMessage, args=(channel_id, msg)).start()
                except Exception as e:
                    print(f"Lỗi gửi tin nhắn: {e}")
            return HTML + "<p>Đã gửi thủ công thành công!</p>"

        if quickmsg:
            for idx, bot in enumerate(bots):
                try:
                    threading.Timer(2 * idx, bot.sendMessage, args=(channel_id, quickmsg)).start()
                except Exception as e:
                    print(f"Lỗi gửi tin nhắn: {e}")
            return HTML + f"<p>Đã gửi lệnh {quickmsg} thành công!</p>"

    return HTML

def keep_alive():
    app.run(host="0.0.0.0", port=8080)

threading.Thread(target=keep_alive, daemon=True).start()

while True:
    time.sleep(5)
