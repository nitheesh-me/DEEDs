# protofiles current and subdirectories
protofiles=$(find . -name "*.proto")

# generate python code
for file in $protofiles; do
    python -m grpc_tools.protoc \
        -I. \
        --include_imports \
        -o "../servers/deedsproto/${file}.desc" \
        --python_out=../servers/deedsproto/ \
        --grpc_python_out=../servers/deedsproto/ \
        --proto_path=. \
        ${file}
done