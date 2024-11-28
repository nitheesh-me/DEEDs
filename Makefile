# docker compose up --build --abort-on-container-exit

PROTO_DIR := src/protos
OUT_DIR := genproto

PROTO_FILES := $(shell find $(PROTO_DIR) -name '*.proto')

all: $(PROTO_FILES)
	@mkdir -p $(OUT_DIR)
	python -m grpc_tools.protoc -I=$(PROTO_DIR) --python_out=$(OUT_DIR) --grpc_python_out=$(OUT_DIR) $(PROTO_FILES)
	@find $(OUT_DIR) -type d -exec touch {}/__init__.py \;

# run using `make test`
test:
	PYTHONPATH=./src pytest ./tests

build-proto:
	@cd $(PROTO_DIR) && bash BUILD.sh

control-backup:
	PYTHONPATH=./src python -m servers backup

control:
	PYTHONPATH=./src python -m servers control

storage:
	PYTHONPATH=./src python -m servers storage

client-connect:
	mkdir -p /mnt/deeds
	PYTHONPATH=./src python -m deedsclient setup --mountpoint /mnt/deeds

expire:
	PYTHONPATH=./src python -m deedsclient expire
