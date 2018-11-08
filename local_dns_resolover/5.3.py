from socket import *
import struct
import time


# query part in DNS response
class Query(object):
    def __init__(self, query_bytes):
        i = 1
        self.name = ''
        while True:
            if query_bytes[i] == 0:
                break
            elif query_bytes[i] < 30:
                self.name = self.name + '.'
            else:
                self.name = self.name + chr(query_bytes[i])
            i = i + 1
        self.name_bytes = query_bytes[0: i + 1]
        self.type, self.clas = struct.unpack('>HH', query_bytes[i + 1:i + 5])
        self.mark = i + 5

    def toBytes(self):
        return self.name_bytes + struct.pack('>HH', self.type, self.clas)


# reslove client dns query
class DNSquery(object):
    def __init__(self, query_bytes):
        # resolove dns query head
        self.id, self.flags, self.questions, self.answers_rrs, self.authority_rrs, self.additional_rrs = struct.unpack(
            '>HHHHHH', query_bytes[0:12])
        i = 13
        self.name = ''
        while True:
            if query_bytes[i] == 0:
                break
            elif query_bytes[i] < 30:
                self.name = self.name + '.'
            else:
                self.name = self.name + chr(query_bytes[i])
            i = i + 1
        self.name_bytes = query_bytes[0: i + 1]
        self.type, self.clas = struct.unpack('>HH', query_bytes[i + 1:i + 5])
        self.mark = i + 5


# resolove DNS response from top DNS
class DNSresponse:
    def __init__(self, response_bytes):
        # resolove DNS response head
        self.id, self.flags, self.questions, self.answers_rrs, self.authority_rrs, self.additional_rrs = struct.unpack(
            '>HHHHHH', response_bytes[0:12])
        response_bytes = response_bytes[12:]
        # resolove
        self.query = Query(response_bytes)
        response_bytes = response_bytes[self.query.mark:]
        self.answers = []
        self.authority = []
        self.additional = []
        self.min_ttl = 0xffffffff
        self.record_time = int(time.time())
        for i in range(self.answers_rrs):
            ans = DNSanswer(response_bytes)
            self.min_ttl = min(ans.ttl, self.min_ttl)
            self.answers.append(ans)
            response_bytes = response_bytes[ans.mark:]
        for i in range(self.authority_rrs):
            aut = DNSanswer(response_bytes)
            self.min_ttl = min(aut.ttl, self.min_ttl)
            self.authority.append(aut)
            response_bytes = response_bytes[aut.mark:]
        for i in range(self.additional_rrs - 1):
            add = DNSanswer(response_bytes)
            self.min_ttl = min(add.ttl, self.min_ttl)
            self.additional.append(add)
            response_bytes = response_bytes[add.mark:]
        self.left = response_bytes[0:]

    # set response id
    def set_id(self, id):
        self.id = id

    # update RR ttl
    def set_ttl(self, new_time):
        for i in range(self.answers_rrs):
            self.answers[i].ttl -= new_time - self.record_time
        for i in range(self.authority_rrs):
            self.authority[i].ttl -= new_time - self.record_time
        for i in range(self.additional_rrs - 1):
            self.additional[i].ttl -= new_time - self.record_time
        self.min_ttl -= new_time - self.record_time
        self.record_time = new_time

    def toBytes(self):
        b = struct.pack('>HHHHHH', self.id, self.flags, self.questions, self.answers_rrs, self.authority_rrs,
                        self.additional_rrs)
        b += self.query.toBytes()
        for i in self.answers:
            b += i.toBytes()
        for i in self.authority:
            b += i.toBytes()
        for i in self.additional:
            b += i.toBytes()
        b += self.left
        return b


# reslove answers in DNS response
class DNSanswer(object):
    def __init__(self, answer_bytes):
        # if answer name is pointer ( first char is 'c' )
        if answer_bytes[0] >> 6 == 3:
            self.name, self.type, self.clas, self.ttl, self.data_length = struct.unpack('>HHHLH', answer_bytes[0: 12])
            self.name_bytes = answer_bytes[0: 2]
            self.data = answer_bytes[12: 12 + self.data_length]
            self.mark = 12 + self.data_length
        else:
            i = 1
            self.name = ''
            while True:
                if answer_bytes[i] == 0:
                    break
                elif answer_bytes[i] < 30:
                    self.name = self.name + '.'
                else:
                    self.name = self.name + chr(answer_bytes[i])
                i = i + 1
            self.name_bytes = answer_bytes[0: i + 1]
            self.type, self.clas, self.ttl, self.data_length = struct.unpack('>HHLH', answer_bytes[i + 1: i + 11])
            self.data = answer_bytes[i + 11: i + 11 + self.data_length]
            self.mark = i + 11 + self.data_length

    def toBytes(self):
        return self.name_bytes + struct.pack('>HHLH', self.type, self.clas, self.ttl, self.data_length) + self.data


class UDPserver(object):
    def __init__(self):
        self.cache = {}

    def start(self):
        serverPort = 53
        serverSocket = socket(AF_INET, SOCK_DGRAM)
        serverSocket.bind(('', serverPort))
        print('The server is ready to receieve')
        while True:
            message, clientAddress = serverSocket.recvfrom(2048)
            # resolove cliend query
            query = DNSquery(message)
            # check cache DNS query - response
            if (query.name, query.type) in self.cache:
                now = int(time.time())
                response = self.cache[query.name, query.type]
                # check if response is out of date
                if now > response.record_time + response.min_ttl:
                    # out of date: requery to public DNS
                    serverSocket.sendto(message, ('8.8.8.8', 53))
                    message, dns_server_address = serverSocket.recvfrom(2048)
                    # resolove public DNS response
                    response = DNSresponse(message)
                    self.cache[(query.name, query.type)] = response
                    serverSocket.sendto(message, clientAddress)
                else:
                    # within date: send cache response with correct id and update response TTL
                    response.set_id(query.id)
                    response.set_ttl(now)
                    serverSocket.sendto(response.toBytes(), clientAddress)
            else:
                # no cache: requery to public DNS
                serverSocket.sendto(message, ('8.8.8.8', 53))
                message, dns_server_address = serverSocket.recvfrom(2048)
                # resolove public dns response
                response = DNSresponse(message)
                self.cache[(query.name, query.type)] = response
                serverSocket.sendto(message, clientAddress)


DNSserver = UDPserver()
DNSserver.start()
