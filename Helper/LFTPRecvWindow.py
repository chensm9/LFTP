# 表示接收窗口中的每一项
class RecvWindowItem:
    def __init__(self, state, seqnum, content):
        self.state = state # 0表示未确认，1表示已经确认
        self.seqnum = seqnum
        self.content = content

# 表示接收窗口
class LFTPRecvWindow:
    def __init__(self, recv_base, rwnd):
        self.window = []
        self.recv_base = recv_base
        self.rwnd = rwnd
        for i in range(rwnd):
            self.window.append(RecvWindowItem(0, self.recv_base+i, None))


    def insert(self, seqnum, content):
        if (self.recv_base > seqnum or seqnum < self.send_base + self.N):
            return
        

    def ifACK(self, seqnum):
        if (seqnum >= self.recv_base - self.window_len and seqnum < self.recv_base + self.window_len):
            return True
        return False


    def update(self):
        size = 0
        while self.window[0].state == 1:
            size += len(self.window[0].content)
            self.window.pop(0)
            self.window.append(RecvWindowItem(0, self.resv_base+self.window_len, None))
            self.recv_base += 1
        return size
        
