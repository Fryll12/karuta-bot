import discum
import threading
import time
import os
import json
import requests
from flask import Flask, request, render_template_string, jsonify
from dotenv import load_dotenv
from keep_alive import keep_alive

load_dotenv()

# === CẤU HÌNH GLOBAL ===
karuta_id = "646937666251915264"
fixed_emojis = ["1️⃣", "2️⃣", "3️⃣", "1️⃣", "2️⃣", "3️⃣"]
grab_times = [1.3, 2.3, 3.2, 1.3, 2.3, 3.2]

# Tokens từ environment
all_tokens = []
for i in range(1, 31):  # Hỗ trợ tối đa 30 acc
    token = os.getenv(f"TOKEN{i}")
    if token:
        all_tokens.append(token)

# === BIẾN TRẠNG THÁI ===
groups = {}  # {'Group A': [0, 1, 2, 3, 4, 5]}
farms = []   # [{'name': 'Farm 1', 'group': 'Group A', 'kd_channel': '123', 'ktb_channel': '456', 'enabled': True}]
active_bots = {}  # {'farm_id': [bot1, bot2, ...]}
bots_lock = threading.Lock()
drop_timers = {}  # {'farm_id': timer_object}

# === LƯU/TẢI CÀI ĐẶT ===
def save_settings():
    api_key = os.getenv("JSONBIN_API_KEY")
    bin_id = os.getenv("JSONBIN_BIN_ID")
    if not api_key or not bin_id:
        return
    
    settings = {
        'groups': groups,
        'farms': farms
    }
    
    headers = {'Content-Type': 'application/json', 'X-Master-Key': api_key}
    url = f"https://api.jsonbin.io/v3/b/{bin_id}"
    
    try:
        response = requests.put(url, json=settings, headers=headers, timeout=10)
        if response.status_code == 200:
            print("[Settings] Đã lưu cài đặt.", flush=True)
    except Exception as e:
        print(f"[Settings] Lỗi khi lưu: {e}", flush=True)

def load_settings():
    global groups, farms
    api_key = os.getenv("JSONBIN_API_KEY")
    bin_id = os.getenv("JSONBIN_BIN_ID")
    if not api_key or not bin_id:
        return
    
    headers = {'X-Master-Key': api_key}
    url = f"https://api.jsonbin.io/v3/b/{bin_id}/latest"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json().get("record", {})
            groups = data.get('groups', {})
            farms = data.get('farms', [])
            print(f"[Settings] Đã tải {len(groups)} groups và {len(farms)} farms.", flush=True)
    except Exception:
        groups = {}
        farms = []

# === LOGIC BOT ===
def create_farm_bot(token, account_index, farm_config):
    """Tạo bot cho farm với token và cấu hình cụ thể"""
    bot = discum.Client(token=token, log=False)
    
    emoji = fixed_emojis[account_index % len(fixed_emojis)]
    grab_time = grab_times[account_index % len(grab_times)]
    
    @bot.gateway.command
    def on_ready(resp):
        if resp.event.ready:
            try:
                user_id = resp.raw["user"]["id"]
                print(f"[{farm_config['name']} - Bot {account_index}] Đăng nhập: {user_id}")
            except Exception as e:
                print(f"[{farm_config['name']} - Bot {account_index}] Lỗi ready: {e}")

    @bot.gateway.command
    def on_message(resp):
        if resp.event.message:
            msg = resp.parsed.auto()
            author = msg.get("author", {}).get("id")
            content = msg.get("content", "")
            
            if (author == karuta_id and 
                "is dropping 3 cards!" in content and 
                msg.get("channel_id") == str(farm_config['kd_channel'])):
                
                def react_and_ktb():
                    time.sleep(grab_time)
                    try:
                        bot.addReaction(msg["channel_id"], msg["id"], emoji)
                        print(f"[{farm_config['name']} - Bot {account_index}] Reaction {emoji}")
                    except Exception as e:
                        print(f"[{farm_config['name']} - Bot {account_index}] Lỗi reaction: {e}")
                    
                    time.sleep(2)
                    try:
                        bot.sendMessage(str(farm_config['ktb_channel']), "kt b")
                        print(f"[{farm_config['name']} - Bot {account_index}] Gửi kt b")
                    except Exception as e:
                        print(f"[{farm_config['name']} - Bot {account_index}] Lỗi kt b: {e}")
                
                threading.Thread(target=react_and_ktb).start()
    
    return bot

def start_farm_bots(farm_config):
    """Khởi tạo 6 bots cho một farm"""
    farm_id = farm_config['id']
    group_name = farm_config['group']
    
    if group_name not in groups or len(groups[group_name]) != 6:
        print(f"[{farm_config['name']}] Group không hợp lệ hoặc không đủ 6 acc")
        return
    
    with bots_lock:
        # Dừng bots cũ nếu có
        if farm_id in active_bots:
            stop_farm_bots(farm_id)
        
        active_bots[farm_id] = []
        account_indices = groups[group_name]
        
        for i, acc_index in enumerate(account_indices):
            if acc_index < len(all_tokens):
                token = all_tokens[acc_index]
                bot = create_farm_bot(token, i, farm_config)
                active_bots[farm_id].append(bot)
                
                # Chạy bot trong thread riêng với auto-reconnect
                def run_bot_with_reconnect(bot, farm_name, bot_index):
                    while farm_id in active_bots:  # Chỉ chạy khi farm còn active
                        try:
                            bot.gateway.run(auto_reconnect=True)
                        except Exception as e:
                            if farm_id in active_bots:  # Chỉ log nếu farm còn active
                                print(f"[{farm_name} - Bot {bot_index}] Kết nối lại: {e}")
                        time.sleep(5)
                
                threading.Thread(
                    target=run_bot_with_reconnect, 
                    args=(bot, farm_config['name'], i), 
                    daemon=True
                ).start()

def stop_farm_bots(farm_id):
    """Dừng tất cả bots của một farm"""
    with bots_lock:
        if farm_id in active_bots:
            for bot in active_bots[farm_id]:
                try:
                    bot.gateway.close()
                except:
                    pass
            del active_bots[farm_id]
    
    # Dừng drop timer
    if farm_id in drop_timers:
        drop_timers[farm_id].cancel()
        del drop_timers[farm_id]

def start_drop_cycle(farm_config):
    """Bắt đầu chu kỳ drop cho farm"""
    farm_id = farm_config['id']
    
    if not farm_config.get('enabled', False):
        return
    
    with bots_lock:
        if farm_id not in active_bots or not active_bots[farm_id]:
            return
        
        bots_list = active_bots[farm_id]
    
    def drop_loop():
        i = 0
        while farm_id in active_bots and farm_config.get('enabled', False):
            try:
                bot_index = i % len(bots_list)
                bot = bots_list[bot_index]
                bot.sendMessage(str(farm_config['kd_channel']), "kd")
                print(f"[{farm_config['name']}] Drop từ bot {bot_index}")
                i += 1
                time.sleep(305)  # 5 phút 5 giây
            except Exception as e:
                print(f"[{farm_config['name']}] Lỗi drop: {e}")
                time.sleep(10)
    
    # Dừng timer cũ nếu có
    if farm_id in drop_timers:
        drop_timers[farm_id].cancel()
    
    # Bắt đầu drop cycle
    drop_thread = threading.Thread(target=drop_loop, daemon=True)
    drop_thread.start()
    drop_timers[farm_id] = drop_thread

# === FLASK APP ===
app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Karuta Drop Farm Control</title>
    <style>
        :root {
            --primary-bg: #0a0a0a; --secondary-bg: #1a1a1a; --panel-bg: #111111; 
            --border-color: #333333; --blood-red: #8b0000; --necro-green: #228b22; 
            --text-primary: #f0f0f0; --text-secondary: #cccccc; --hot-pink: #FF69B4;
        }
        body { font-family: 'Courier New', monospace; background: var(--primary-bg); 
               color: var(--text-primary); margin: 0; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .title { font-size: 2.5rem; color: var(--hot-pink); text-shadow: 0 0 15px var(--hot-pink); }
        .panel { background: #111; border: 1px solid var(--border-color); 
                 border-radius: 10px; padding: 20px; margin-bottom: 20px; }
        .panel h2 { color: var(--text-secondary); border-bottom: 1px solid var(--border-color); 
                    padding-bottom: 10px; margin-top: 0; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .input-group { display: flex; align-items: stretch; gap: 5px; margin-bottom: 10px; }
        .input-group label { padding: 8px; background: #222; border: 1px solid var(--border-color); 
                             border-radius: 5px 0 0 5px; white-space: nowrap; }
        .input-group input, .input-group select { flex: 1; background: #000; 
                                                  border: 1px solid var(--border-color); 
                                                  color: var(--text-primary); padding: 8px; 
                                                  border-radius: 0 5px 5px 0; }
        .btn { background: var(--secondary-bg); border: 1px solid var(--border-color); 
               color: var(--text-primary); padding: 8px 12px; border-radius: 4px; 
               cursor: pointer; margin: 2px; }
        .btn:hover { filter: brightness(1.2); }
        .btn-success { border-color: var(--necro-green); color: var(--necro-green); }
        .btn-success:hover { background: var(--necro-green); color: var(--primary-bg); }
        .btn-danger { border-color: var(--blood-red); color: var(--blood-red); }
        .btn-danger:hover { background: var(--blood-red); color: var(--primary-bg); }
        .group-container { border: 1px solid var(--hot-pink); padding: 15px; 
                           border-radius: 8px; margin-bottom: 15px; }
        .account-grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 5px; margin: 10px 0; }
        .account-slot { background: #222; padding: 8px; border-radius: 4px; text-align: center; 
                        border: 2px solid transparent; cursor: pointer; }
        .account-slot.selected { border-color: var(--necro-green); }
        .farm-item { background: #1a1a1a; padding: 15px; border-radius: 8px; margin-bottom: 10px; }
        .farm-header { display: flex; justify-content: between; align-items: center; margin-bottom: 10px; }
        .status-indicator { width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; }
        .status-online { background: var(--necro-green); }
        .status-offline { background: var(--blood-red); }
        .msg-status { text-align: center; color: var(--necro-green); padding: 10px; 
                      background: rgba(34, 139, 34, 0.1); border-radius: 4px; 
                      margin-bottom: 20px; display: none; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="title">KARUTA DROP FARM CONTROL</h1>
        </div>
        
        <div id="msg-status" class="msg-status"></div>
        
        <!-- Group Management -->
        <div class="panel">
            <h2>Group Management (6 Accounts Each)</h2>
            <div class="input-group" style="width: 40%;">
                <input type="text" id="new-group-name" placeholder="Tên group...">
                <button id="add-group-btn" class="btn btn-success">Thêm Group</button>
            </div>
            
            <div id="available-accounts" style="margin: 15px 0;">
                <h4>Available Accounts: {{ available_count }}/{{ total_count }}</h4>
                <div class="account-grid">
                    {% for i in range(total_count) %}
                    <div class="account-slot" data-index="{{ i }}">
                        ACC {{ i + 1 }}
                        {% if i in used_accounts %}
                        <br><small>(Used)</small>
                        {% endif %}
                    </div>
                    {% endfor %}
                </div>
            </div>
            
            <div id="groups-container">
                {% for group_name, accounts in groups.items() %}
                <div class="group-container" data-group="{{ group_name }}">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h3>{{ group_name }} ({{ accounts|length }}/6)</h3>
                        <button class="btn btn-danger delete-group-btn">Xóa Group</button>
                    </div>
                    <div class="account-grid">
                        {% for acc_index in accounts %}
                        <div class="account-slot selected">ACC {{ acc_index + 1 }}</div>
                        {% endfor %}
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        
        <!-- Farm Management -->
        <div class="panel">
            <h2>Farm Management</h2>
            <div class="input-group" style="width: 40%;">
                <input type="text" id="new-farm-name" placeholder="Tên farm...">
                <button id="add-farm-btn" class="btn btn-success">Thêm Farm</button>
            </div>
            
            <div class="grid">
                {% for farm in farms %}
                <div class="farm-item" data-farm-id="{{ farm.id }}">
                    <div class="farm-header">
                        <div style="display: flex; align-items: center;">
                            <div class="status-indicator {{ 'status-online' if farm.enabled else 'status-offline' }}"></div>
                            <h4>{{ farm.name }}</h4>
                        </div>
                        <div>
                            <button class="btn toggle-farm-btn {{ 'btn-danger' if farm.enabled else 'btn-success' }}">
                                {{ 'TẮT' if farm.enabled else 'BẬT' }}
                            </button>
                            <button class="btn btn-danger delete-farm-btn">Xóa</button>
                        </div>
                    </div>
                    
                    <div class="input-group">
                        <label>Group</label>
                        <select class="farm-group-select">
                            <option value="">Chọn group...</option>
                            {% for group_name in groups.keys() %}
                            <option value="{{ group_name }}" {% if farm.group == group_name %}selected{% endif %}>
                                {{ group_name }}
                            </option>
                            {% endfor %}
                        </select>
                    </div>
                    
                    <div class="input-group">
                        <label>KD Channel</label>
                        <input type="text" class="farm-kd-channel" value="{{ farm.kd_channel or '' }}" placeholder="Channel ID...">
                    </div>
                    
                    <div class="input-group">
                        <label>KTB Channel</label>
                        <input type="text" class="farm-ktb-channel" value="{{ farm.ktb_channel or '' }}" placeholder="Channel ID...">
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
    </div>

    <script>
        const msgStatus = document.getElementById('msg-status');
        
        function showMessage(msg) {
            msgStatus.textContent = msg;
            msgStatus.style.display = 'block';
            setTimeout(() => msgStatus.style.display = 'none', 4000);
        }
        
        async function postData(url, data) {
            try {
                const response = await fetch(url, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                const result = await response.json();
                showMessage(result.message);
                if (result.reload) location.reload();
                return result;
            } catch (error) {
                showMessage('Lỗi kết nối server');
            }
        }
        
        // Group Management
        document.getElementById('add-group-btn').addEventListener('click', () => {
            const name = document.getElementById('new-group-name').value.trim();
            if (name) {
                postData('/api/group/add', {name});
            }
        });
        
        document.addEventListener('click', (e) => {
            if (e.target.matches('.delete-group-btn')) {
                const groupName = e.target.closest('.group-container').dataset.group;
                if (confirm(`Xóa group "${groupName}"?`)) {
                    postData('/api/group/delete', {name: groupName});
                }
            }
            
            if (e.target.matches('.delete-farm-btn')) {
                const farmId = e.target.closest('.farm-item').dataset.farmId;
                if (confirm('Xóa farm này?')) {
                    postData('/api/farm/delete', {farm_id: farmId});
                }
            }
            
            if (e.target.matches('.toggle-farm-btn')) {
                const farmId = e.target.closest('.farm-item').dataset.farmId;
                postData('/api/farm/toggle', {farm_id: farmId});
            }
        });
        
        // Farm Management
        document.getElementById('add-farm-btn').addEventListener('click', () => {
            const name = document.getElementById('new-farm-name').value.trim();
            if (name) {
                postData('/api/farm/add', {name});
            }
        });
        
        document.addEventListener('change', (e) => {
            if (e.target.matches('.farm-group-select, .farm-kd-channel, .farm-ktb-channel')) {
                const farmItem = e.target.closest('.farm-item');
                const farmId = farmItem.dataset.farmId;
                const data = {farm_id: farmId};
                
                if (e.target.matches('.farm-group-select')) {
                    data.group = e.target.value;
                } else if (e.target.matches('.farm-kd-channel')) {
                    data.kd_channel = e.target.value;
                } else if (e.target.matches('.farm-ktb-channel')) {
                    data.ktb_channel = e.target.value;
                }
                
                postData('/api/farm/update', data);
            }
        });
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    used_accounts = set()
    for accounts in groups.values():
        used_accounts.update(accounts)
    
    return render_template_string(HTML_TEMPLATE,
        groups=groups,
        farms=farms,
        total_count=len(all_tokens),
        available_count=len(all_tokens) - len(used_accounts),
        used_accounts=used_accounts
    )

# === API ROUTES ===
@app.route("/api/group/add", methods=['POST'])
def api_group_add():
    name = request.json.get('name', '').strip()
    if not name or name in groups:
        return jsonify({'status': 'error', 'message': 'Tên group không hợp lệ hoặc đã tồn tại'})
    
    groups[name] = []
    save_settings()
    return jsonify({'status': 'success', 'message': f'Đã tạo group "{name}"', 'reload': True})

@app.route("/api/group/delete", methods=['POST'])
def api_group_delete():
    name = request.json.get('name')
    if name not in groups:
        return jsonify({'status': 'error', 'message': 'Group không tồn tại'})
    
    # Dừng các farm sử dụng group này
    for farm in farms:
        if farm.get('group') == name:
            farm['group'] = None
            if farm.get('enabled'):
                stop_farm_bots(farm['id'])
                farm['enabled'] = False
    
    del groups[name]
    save_settings()
    return jsonify({'status': 'success', 'message': f'Đã xóa group "{name}"', 'reload': True})

@app.route("/api/farm/add", methods=['POST'])
def api_farm_add():
    name = request.json.get('name', '').strip()
    if not name:
        return jsonify({'status': 'error', 'message': 'Tên farm không được trống'})
    
    farm_id = f"farm_{int(time.time() * 1000)}"
    farm = {
        'id': farm_id,
        'name': name,
        'group': None,
        'kd_channel': '',
        'ktb_channel': '',
        'enabled': False
    }
    
    farms.append(farm)
    save_settings()
    return jsonify({'status': 'success', 'message': f'Đã tạo farm "{name}"', 'reload': True})

@app.route("/api/farm/delete", methods=['POST'])
def api_farm_delete():
    farm_id = request.json.get('farm_id')
    
    # Tìm và xóa farm
    global farms
    farm_to_delete = None
    for farm in farms:
        if farm['id'] == farm_id:
            farm_to_delete = farm
            break
    
    if not farm_to_delete:
        return jsonify({'status': 'error', 'message': 'Farm không tồn tại'})
    
    # Dừng bots
    stop_farm_bots(farm_id)
    
    # Xóa khỏi danh sách
    farms = [f for f in farms if f['id'] != farm_id]
    save_settings()
    
    return jsonify({'status': 'success', 'message': f'Đã xóa farm "{farm_to_delete["name"]}"', 'reload': True})

@app.route("/api/farm/update", methods=['POST'])
def api_farm_update():
    data = request.json
    farm_id = data.get('farm_id')
    
    farm = next((f for f in farms if f['id'] == farm_id), None)
    if not farm:
        return jsonify({'status': 'error', 'message': 'Farm không tồn tại'})
    
    # Cập nhật thông tin
    if 'group' in data:
        old_group = farm.get('group')
        farm['group'] = data['group'] if data['group'] else None
        
        # Nếu thay đổi group và farm đang chạy, restart bots
        if farm.get('enabled') and old_group != farm['group']:
            stop_farm_bots(farm_id)
            if farm['group'] and farm['kd_channel'] and farm['ktb_channel']:
                start_farm_bots(farm)
                start_drop_cycle(farm)
    
    if 'kd_channel' in data:
        farm['kd_channel'] = data['kd_channel']
    
    if 'ktb_channel' in data:
        farm['ktb_channel'] = data['ktb_channel']
    
    save_settings()
    return jsonify({'status': 'success', 'message': 'Đã cập nhật farm'})

@app.route("/api/farm/toggle", methods=['POST'])
def api_farm_toggle():
    farm_id = request.json.get('farm_id')
    
    farm = next((f for f in farms if f['id'] == farm_id), None)
    if not farm:
        return jsonify({'status': 'error', 'message': 'Farm không tồn tại'})
    
    if farm.get('enabled'):
        # Tắt farm
        stop_farm_bots(farm_id)
        farm['enabled'] = False
        status = 'TẮT'
    else:
        # Bật farm - kiểm tra điều kiện
        if not farm.get('group'):
            return jsonify({'status': 'error', 'message': 'Farm chưa có group'})
        
        if farm['group'] not in groups or len(groups[farm['group']]) != 6:
            return jsonify({'status': 'error', 'message': 'Group không hợp lệ hoặc chưa đủ 6 accounts'})
        
        if not farm.get('kd_channel') or not farm.get('ktb_channel'):
            return jsonify({'status': 'error', 'message': 'Farm chưa có đủ thông tin channel'})
        
        # Bật farm
        start_farm_bots(farm)
        start_drop_cycle(farm)
        farm['enabled'] = True
        status = 'BẬT'
    
    save_settings()
    return jsonify({'status': 'success', 'message': f'Đã {status} farm "{farm["name"]}"', 'reload': True})

# === MAIN EXECUTION ===
if __name__ == "__main__":
    # Kiểm tra tokens
    if not all_tokens:
        print("Không tìm thấy tokens trong environment variables!")
        exit(1)
    
    print(f"Đã tải {len(all_tokens)} tokens")
    
    # Tải cài đặt
    load_settings()
    
    # Khởi động keep_alive
    keep_alive()
    
    # Auto-start enabled farms
    for farm in farms:
        if (farm.get('enabled') and 
            farm.get('group') and 
            farm.get('kd_channel') and 
            farm.get('ktb_channel') and
            farm['group'] in groups and 
            len(groups[farm['group']]) == 6):
            
            print(f"Auto-starting farm: {farm['name']}")
            start_farm_bots(farm)
            start_drop_cycle(farm)
    
    # Định kỳ lưu settings
    def periodic_save():
        while True:
            time.sleep(300)  # 5 phút
            save_settings()
    
    threading.Thread(target=periodic_save, daemon=True).start()
    
    # Chạy Flask
    port = int(os.environ.get("PORT", 10001))
    print(f"Khởi động server tại http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)