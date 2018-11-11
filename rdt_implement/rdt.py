from udp import UDPsocket

class socket(UDPsocket):
    def __init__(self):
        super(socket, self).__init__()

    def connect(self):
        # send syn; receive syn, ack; send ack
        # your code here
        pass

    def accept(self):
        # receive syn; send syn, ack; receive ack
        # your code here
        pass

    def close(self):
        # send fin; receive ack; receive fin; send ack
        # your code here
        pass

    def recv(self):
        # your code here
        pass

    def send(self):
        # your code here
        pass
        