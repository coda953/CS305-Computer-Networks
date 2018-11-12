from rdt import socket
import sys
import time
import threading
import struct


class Receiver:
    def __init__(self, server, SERVER_ADDR, SERVER_PORT, expectedseqnum, time_out):
        self.server = server
        self.SERVER_ADDR = SERVER_ADDR
        self.SERVER_PORT = SERVER_PORT
        self.ACK = 1
        self.expectedseqnum = expectedseqnum
        self.client_addr = ()
        self.time_out = time_out
        self.timer = None

    def make_pkt(self, expectedseqnum, chksum):
        return struct.pack('>HHH', expectedseqnum, self.ACK, chksum)

    @staticmethod
    def calc_checksum(payload):
        sum = 0
        for byte in payload:
            sum += byte
        sum = -(sum % 256)
        return sum & 0xFF

    def udt_resend(self):
        snd_pkt = self.make_pkt(self.expectedseqnum - 1, self.calc_checksum(struct.pack('>HH', self.expectedseqnum - 1, self.ACK)))
        print("Time out! Receiver resend ACK of pkt {}".format(self.expectedseqnum - 1))
        if receiver.timer is not None:
            receiver.timer.cancel()
        self.timer = threading.Timer(receiver.time_out, receiver.udt_resend)
        receiver.timer.start()
        self.server.sendto(snd_pkt, self.client_addr)


if __name__ == '__main__':
    SERVER_ADDR = "127.0.0.1"
    SERVER_PORT = 22333
    server = socket()
    server.bind((SERVER_ADDR, SERVER_PORT))
    receiver = Receiver(server, SERVER_ADDR, SERVER_PORT, 1, 5)
    print('Waiting for receiving ...')
    rcv_file = open('./out/rcv_message.txt', 'wb')
    start_time = time.time()
    end_time = start_time
    while True:
        start_time = time.time()
        if abs(end_time - start_time) > 100:
            print('Server closed.')
            receiver.timer.cancel()
            sys.exit()
        try:
            rcvpkt, addr = server.recvfrom(4096)
            end_time = time.time()
            receiver.client_addr = addr
            nextseqnum, chcksum = struct.unpack('>HH', rcvpkt[0: 4])
            print("Server received pkt: {}".format(nextseqnum))

            data = rcvpkt[4:]
            if receiver.calc_checksum(rcvpkt[0:2] + rcvpkt[4:]) == chcksum and receiver.expectedseqnum == nextseqnum:

                rcv_file.write(data)
                print("Send ACK of pkt {}".format(receiver.expectedseqnum))

                snd_pkt = receiver.make_pkt(receiver.expectedseqnum, receiver.calc_checksum(struct.pack('>HH', receiver.expectedseqnum, receiver.ACK)))
                server.sendto(snd_pkt, addr)
                receiver.expectedseqnum = receiver.expectedseqnum + 1
                if receiver.timer is not None:
                    receiver.timer.cancel()
                receiver.timer = threading.Timer(receiver.time_out, receiver.udt_resend)
                receiver.timer.start()
            elif receiver.expectedseqnum != nextseqnum:
                print('pkt not expected! expected pkt is {}'.format(receiver.expectedseqnum))
            else:
                print('pkt incorrupt!')
        except TypeError:
            pass
        except ConnectionResetError:
            print('Connection close!')
            receiver.timer.cancel()
            sys.exit()

