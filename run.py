import grpc
from grpc import aio
from genproto.services import (
    master_metadata_service_pb2_grpc as service_pb2_grpc,
    master_metadata_service_pb2 as service_pb2,
)


# Example usage
async def main():
    async with aio.insecure_channel('localhost:50051') as channel:
        stub = service_pb2_grpc.YourServiceStub(channel)
        response = await stub.YourMethod(service_pb2.YourRequest())
        print(response)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
