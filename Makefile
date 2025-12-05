# directory
SERVER_FLD = server
PLAYER_FLD = player
DEVELOPER_FLD = developer
TOOL_DIR = tool

# IP
DB_NAME = database.db
DB_PORT = 30007

# Server definitions
LINUX1_HOST = 140.113.17.11
LINUX2_HOST = 140.113.17.12
LINUX3_HOST = 140.113.17.13
LINUX4_HOST = 140.113.17.14
LOCAL_HOST = 127.0.0.1

SERVER_PORT = 25003

# Default server
SERVER ?= local

# Determine HOST based on SERVER argument
ifeq ($(SERVER), linux1)
	TARGET_HOST = $(LINUX1_HOST)
else ifeq ($(SERVER), linux2)
	TARGET_HOST = $(LINUX2_HOST)
else ifeq ($(SERVER), linux3)
	TARGET_HOST = $(LINUX3_HOST)
else ifeq ($(SERVER), linux4)
	TARGET_HOST = $(LINUX4_HOST)
else ifeq ($(SERVER), local)
	TARGET_HOST = $(LOCAL_HOST)
else
	TARGET_HOST = $(LOCAL_HOST)
endif

.PHONY: db_server server player developer open_db

db_server: $(SERVER_FLD)/db_server.py
	@cd $(SERVER_FLD) && \
	python3 -B db_server.py $(DB_PORT) $(DB_NAME)

server: $(SERVER_FLD)/server.py
	@cd $(SERVER_FLD) && \
	python3 -B server.py $(DB_PORT) $(SERVER_PORT)

player: $(PLAYER_FLD)/player.py
	@echo "Connecting to $(SERVER) server: $(TARGET_HOST):$(SERVER_PORT)"
	@cd $(PLAYER_FLD) && \
	python3 -B player.py $(TARGET_HOST) $(SERVER_PORT)

developer: $(DEVELOPER_FLD)/developer.py
	@echo "Connecting to $(SERVER) server: $(TARGET_HOST):$(SERVER_PORT)"
	@cd $(DEVELOPER_FLD) && \
	python3 -B developer.py $(TARGET_HOST) $(SERVER_PORT)

# Using for debug
open_db:
	@cd $(SERVER_FLD) && \
	sqlite3 $(DB_NAME)

# =========================
#   	   Clean
# =========================

clean_player:
	@cd $(PLAYER_FLD) && rm -rf downloads

clean_server:
	@cd $(SERVER_FLD) && rm -rf games

clean_developer:
	@cd $(DEVELOPER_FLD) && rm -rf games

clean:
	@cd $(SERVER_FLD) && \
	rm -rf __pycache__ ./$(TOOL_DIR) && \
	rm -f $(DB_NAME)
	@cd $(DEVELOPER_FLD) && \
	rm -rf __pycache__ ./$(TOOL_DIR)
	@cd $(PLAYER_FLD) && \
	rm -rf __pycache__ ./$(TOOL_DIR)
	@$(MAKE) clean_player


# =========================
#    Tool Setting
# =========================

set_tool:
	@cp -r $(TOOL_DIR) $(SERVER_FLD)
	@cp -r $(TOOL_DIR) $(PLAYER_FLD)
	@cp -r $(TOOL_DIR) $(DEVELOPER_FLD)

# =========================
#    Environment Setting
# =========================

server_env:
	sudo apt-get update
	sudo apt-get install sqlite3
	sudo apt-get install python3

player_env:
	sudo apt-get update
	sudo apt-get install python3
	pip3 install pygame
