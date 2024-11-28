import grpc
import sample_pb2_grpc
import sample_pb2
import time

from concurrent import futures


class SampleService(sample_pb2_grpc.SampleServiceServicer):
    def GetSample(self, request, context):
        return sample_pb2.SampleResponse(message='Hello, %s!' % request.id)

    def GetSampleStream(self, request, context):
        if not request.count:
            request.count = 1
        for i in range(request.count):
            time.sleep(1)
            yield sample_pb2.SampleResponse(message='Hello, %s!' % request.id)

    def GetSampleStreamBidirectional(self, request_iterator, context):
        for request in request_iterator:
            time.sleep(1)
            yield sample_pb2.SampleResponse(message='Hello, %s!' % request.id)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
    sample_pb2_grpc.add_SampleServiceServicer_to_server(SampleService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
