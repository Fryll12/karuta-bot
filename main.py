import discum
import threading
import time
import os
from keep_alive import keep_alive

accounts = [
    {"token": os.getenv("TOKEN1"), "channel_id": os.getenv("CHANNEL_ID")},
    {"token": os.getenv("TOKEN2"), "channel_id": os.getenv("CHANNEL_ID")},
    {"token": os.getenv("TOKEN3"), "channel_id": os.getenv("CHANNEL_ID")},
    {"token": os.getenv("TOKEN4"), "channel_id": os.getenv("CHANNEL_ID")},
    {"token": os.getenv("TOKEN5"), "channel_id": os.getenv("CHANNEL_ID")},
    {"token": os.getenv("TOKEN6"), "channel_id": os.getenv("CHANNEL_ID")},
]

karuta_id = "646937666251915264"
fixed_emojis = ["1️⃣", "2️⃣", "3️⃣", "1️⃣", "2️⃣", "3️⃣"]

def create_bot(account, emoji):
    bot = discum.Client(token=account["token"], log=False)

    @bot.gateway.command
    def on_ready(resp):
        if resp.event.ready:
            try:
                user_id = resp.raw["user"]["id"]
                print(f"[{account['channel_id']}] → Đăng nhập với user_id: {user_id}")
            except Exception as e:
                print(f"Lỗi lấy user_id từ ready: {e}")

    @bot.gateway.command
    def on_message(resp):
        if resp.event.message:
            msg = resp.parsed.auto()
            author = msg.get("author", {}).get("id")
            content = msg.get("content", "")
            if author == karuta_id and "is dropping 3 cards!" in content:
                if msg.get("channel_id") == str(account["channel_id"]):
                    time.sleep(3.6)
                    bot.addReaction(msg["channel_id"], msg["id"], emoji)
                    print(f"[{account['channel_id']}] → Thả reaction {emoji}")
                    try:
                        bot.sendMessage(str(account["channel_id"]), "kt b")
                        print(f"[{account['channel_id']}] → Nhắn 'kt b' sau khi nhặt")
                    except Exception as e:
                        print(f"[{account['channel_id']}] → Lỗi nhắn kt b: {e}")

    threading.Thread(target=bot.gateway.run, daemon=True).start()

def drop_loop():
    acc_count = len(accounts)
    i = 0
    while True:
        acc = accounts[i % acc_count]
        try:
            bot = discum.Client(token=acc["token"], log=False)
            bot.sendMessage(str(acc["channel_id"]), "k!d")
            print(f"[{acc['channel_id']}] → Gửi lệnh k!d từ acc thứ {i % acc_count + 1}")
            bot.gateway.close()
        except Exception as e:
            print(f"[{acc['channel_id']}] → Drop lỗi: {e}")
        i += 1
        time.sleep(305)

keep_alive()

for i, acc in enumerate(accounts):
    emoji = fixed_emojis[i % len(fixed_emojis)]
    create_bot(acc, emoji)

threading.Thread(target=drop_loop, daemon=True).start()

while True:
    time.sleep(60)
