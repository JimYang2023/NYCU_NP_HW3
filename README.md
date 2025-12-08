# NYCU Network Programing HW3

- [環境設定](#環境設定)
- [開始執行](#開始執行)
- [平台操作(開發者)](#平台操作開發者)
- [平台操作(玩家)](#平台操作玩家)

## 環境設定

> 建議執行在Linux或是WSL系統上

- GNU Make 4.3
- Python 3.10.12
- Server: sqlite3 3.37.2
- Player: pygame

設定server及player的環境:

```bash
make sever_env_setting
make player_env_setting
```

若在codespace中未有tool資料夾，請先執行以下指令:

```bash
make set_tool
```

## 開始執行

### Server

```bash
make db_server
```

```bash 
make server
```

### 開發者

請依照server執行對應的位置，輸入指令。`linux1` 可以取代為 `linux2`, `linux3`, `linux4`，會連線到不同位置。若無`SERVER`輸入則會以本地端坐為連線目標。\
若需要修改連線的port，請修改 Makefile 檔案中的`SERVER_PORT`。

```bash
make developer SERVER=linux1
```


### 玩家

請依照server執行對應的位置，輸入指令。`linux1` 可以取代為 `linux2`, `linux3`, `linux4`，會連線到不同位置。若無`SERVER`輸入則會以本地端坐為連線目標。\
若需要修改連線的port，請修改 Makefile 檔案中的`SERVER_PORT`。

```bash
make player SERVER=linux1
```

## 平台操作(開發者)

以下是開發者端的檔案架構:

```javascript
developer
├── tool
|   ├── common_protocal.py
|   └── file_manager.py 
└── games
    ├── game_1
    └── game_2
```

> [!important]
>建議使用系統內的`Create New Game`功能後，在進行遊戲開發

### 建立遊戲

選擇`Create New Game`後，開發者需要輸入相關資訊，如: 遊戲名稱，遊玩人數等，輸入完成後會建立起基本的遊戲檔案，開發者需使用該檔案進行遊戲開發。

建立完成後，在遊戲檔案下會有 main.py 檔案。player_start(), server_start() 分別為玩家與平台的遊戲開始點。

以下為示範:
若遊戲會從player_main 及 server_main開始，則需設定將main.py修改為以下形式。

```python
def player_start():
    player_main()

def server_start():
    server_main()
```

### 遊戲上傳

選擇`Upload Game`後，系統會自動比較 config.json 中的資訊，並若發現可處理的錯誤，會自動進行修改。

以下上傳遊戲的要求:

- 遊戲資料夾內需有 config.json 檔案
- 遊戲資料夾必須位於 games 底下

### 遊戲下架

開發者選擇`Remove Game`之後，平台會下架該遊戲。

> 注意: 
> 當玩家進行遊戲時，無法下架該遊戲 \
> 只提供上傳者下架遊戲


## 平台操作(玩家)

在登入之後可以看見以下選項，玩家更據需求進行操作:

1. Player List  : 顯示目已登入的玩家
2. Room Menu    : 建立/加入 房間
3. Game Shop    : 下載/刪除/顯示/評論 遊戲 
4. Logout       : 登出

### Game Shop

1. Download Game : 從平台下載遊戲
2. Remove Game   : 移除本地端遊戲
3. Current Download Game : 目前以下載的遊戲
4. Game Review   : 評論遊戲

### Room Menu

1. Create Room  : 建立房間
2. Enter Room   : 進入房間
3. List Room    : 顯示目前房間

### 進入房間後

1. Watting State : 進入等待介面(開始遊戲)
2. Exit Room     : 回到房建清單
