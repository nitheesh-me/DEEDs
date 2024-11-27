from pathlib import Path
import sys

# add deedsproto to the path
PROTO_LOCATION = "../servers/deedsproto"
sys.path.append(str(Path(__file__).parent / PROTO_LOCATION))
print(sys.path)
