import discum
import time
import os

accounts = [
    {"token": os.getenv("TOKEN1"), "channel_id": os.getenv("CHANNEL_ID")},
    {"token": os.getenv("TOKEN2"), "channel_id": os.getenv("CHANNEL_ID")},
    {"token": os.getenv("TOKEN3"), "channel_id": os.getenv("CHANNEL_ID")},
    {"token": os.getenv("TOKEN4"), "channel_id": os.getenv("CHANNEL_ID")},
    {"token": os.getenv("TOKEN5"), "channel_id": os.getenv("CHANNEL_ID")},
    {"token": os.getenv("TOKEN6"), "channel_id": os.getenv("CHANNEL_ID")},
]

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

if __name__ == "__main__":
    drop_loop()
