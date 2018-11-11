import struct
import threading
from rdt import socket


class WindowFullError(Exception):
    def __str__(self):
        return "The window is full, you can not send data right now."


class Sender:
    def __init__(self, client,SERVER_ADDR, SERVER_PORT, base, nextseqnum, N, time_out, seg_size):
        self.client = client
        self.SERVER_ADDR = SERVER_ADDR
        self.SERVER_PORT = SERVER_PORT
        self.base = base
        self.nextseqnum = nextseqnum
        self.sndpkt = [[b'']]
        self.N = N
        self.seg_size = seg_size
        self.time_out = time_out
        self.timer = None

    def udt_resend(self):
        print('Time out! Client resend now pkt from {} to {}！'.format(self.base, self.nextseqnum - 1))
        if sender.timer is not None:
            sender.timer.cancel()
        self.timer = threading.Timer(self.time_out, self.udt_resend)
        self.timer.start()
        for i in range(self.base, self.nextseqnum):
            self.client.sendto(self.sndpkt[i], (self.SERVER_ADDR, self.SERVER_PORT))

    @staticmethod
    def calc_checksum(payload):
        sum = 0
        for byte in payload:
            sum += byte
        sum = -(sum % 256)
        return sum & 0xFF

    @staticmethod
    def make_pkt(nextseqnum, checksum, data):
        return struct.pack('>HH', nextseqnum, checksum) + data

    def rdt_send(self, data):
        try:
            if self.nextseqnum < self.base + self.N:
                if self.base == self.nextseqnum:
                    self.timer = threading.Timer(self.time_out, self.udt_resend).start()
                self.sndpkt.append(
                    self.make_pkt(self.nextseqnum, self.calc_checksum(struct.pack('>H', self.nextseqnum) + data), data))
                print('Sender send pkt {}'.format(self.nextseqnum))
                self.client.sendto(self.sndpkt[self.nextseqnum], (self.SERVER_ADDR, self.SERVER_PORT))
                self.nextseqnum = self.nextseqnum + 1
            else:
                raise WindowFullError
        except WindowFullError:
            pass


if __name__ == '__main__':
    client = socket()
    sender = Sender(client, "127.0.0.1", 22333, 1, 1, 5, 5, 1024)
    file = open('./alice.txt', 'rb')

    flag = 0

    while True:
        if sender.nextseqnum < sender.base + sender.N:
            data = file.read(sender.seg_size)
            print("File reading ...")
            if not data:
                print('File read completed.')
                flag = sender.nextseqnum - 1
            else:
                sender.rdt_send(data)
                if sender.timer is not None:
                    sender.timer.cancel()
                sender.timer = threading.Timer(sender.time_out, sender.udt_resend)
                sender.timer.start()
        try:
            rcvpkt, addr = client.recvfrom(4096)
            expectedseqnum, ACK, chksum = struct.unpack('>HHH', rcvpkt)
            print('Client received pkt of expectedseqnum {}'.format(expectedseqnum))
            if sender.calc_checksum(struct.pack('>HH', expectedseqnum, ACK)) == chksum:
                print('receive ACK {}'.format(expectedseqnum))
                if expectedseqnum == flag:
                    print("Transfer complete!")
                    client.close()
                    break
                sender.base = expectedseqnum + 1
            else:
                print('pkt incorrupt!')
            if sender.base == sender.nextseqnum:
                if sender.timer is not None:
                    sender.timer.cancel()
            else:
                if sender.timer is not None:
                    sender.timer.cancel()
                sender.timer = threading.Timer(sender.time_out, sender.udt_resend)
                sender.timer.start()
        except TypeError:
            pass
