import struct

class LFTPMessage:
    def __init__(self, SYN = 0, ACK = 0, getport=0, seqnum = -1, acknum = -1, rwnd = 1000, content_size = 0, content = b''):
        self.SYN = SYN
        self.ACK = ACK
        self.getport = getport
        self.seqnum = seqnum # 序列号
        self.acknum = acknum # 确认号
        self.rwnd = rwnd
        self.content_size = content_size   # 表示实际的content的大小
        self.content = content # 二进制表示

    def pack(self):
        return struct.pack("iiiiiii1024s", self.SYN, self.ACK, self.getport,self.seqnum, self.acknum, self.rwnd, self.content_size, self.content)

    @staticmethod 
    def unpack(message):
        SYN, ACK, getport, seqnum, acknum, rwnd, content_size, content = struct.unpack("iiiiiii1024s", message)
        return LFTPMessage(SYN, ACK, getport, seqnum, acknum, rwnd, content_size, content)
