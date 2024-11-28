import grpc
import sample_pb2_grpc
import sample_pb2

from concurrent import futures

class SampleClient:
    def __init__(self, host, port):
        host = 'localhost'
        port = 50051
        self.channel = grpc.insecure_channel(f'{host}:{port}')
        self.stub = sample_pb2_grpc.SampleServiceStub(self.channel)

    def get_sample(self, id):
        response = self.stub.GetSample(sample_pb2.SampleRequest(id=id))
        self.handle_response(response)
        return response.message

    def handle_response(self, response):
        print(response.message)

    def generate_requests(self, id, count):
        for i in range(count):
            print(f'Generating request {i}')
            yield sample_pb2.SampleRequest(id=id)

    def get_sample_stream(self, id, count):
        responses = self.stub.GetSampleStream(sample_pb2.SampleRequest(id=id, count=count))
        for response in responses:
            self.handle_response(response)

    def get_sample_stream_bidirectional(self, id, count):
        responses = self.stub.GetSampleStreamBidirectional(self.generate_requests(id, count))
        for response in responses:
            self.handle_response(response)


def run():
    client = SampleClient('localhost', 50051)
    client.get_sample('Alice')
    client.get_sample_stream('Bob', 5)
    client.get_sample_stream_bidirectional('Charlie', 5)


if __name__ == '__main__':
    run()
