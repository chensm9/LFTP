# 表示发送窗口中的每一项
class SendWindowItem:
    def __init__(self, state, seqnum, content):
        self.state = state # 0表示可用，1表示已经发送未确认，2表示已经确认
        self.seqnum = seqnum
        self.content = content
        self.acktime = 0  # ack次数(等于4时表示三次冗余)

# 表示发送窗口
class LFTPSendWindow:
    def __init__(self, send_base, rwnd):
        self.window = []
        self.send_base = send_base
        self.nextseqnum = send_base
        self.max = 2000
        self.rwnd = rwnd

    def isFull(self):
        return len(self.window) == self.max

    def isEmpty(self):
        return len(self.window) == 0

    def append(self, content):
        if self.isFull():
            return
        seqnum = self.send_base + len(self.window)
        self.window.append(SendWindowItem(0, seqnum, content))
        
    def getItemToSend(self):
        if self.nextseqnum < self.send_base + self.rwnd:
            self.window[self.nextseqnum - self.send_base].state = 1 # 变为已经发送状态
            item = self.window[self.nextseqnum - self.send_base]
            self.nextseqnum += 1
            return item
        return None

    # 确认序列号
    def ACKseqnum(self, seqnum):
        if (seqnum >= self.send_base and seqnum < self.send_base + len(self.window)):
            # 因为发回来的acknum等于接收到的seqnum+1
            # 所以其实是确认接收到了acknum-1的包
            if seqnum > self.send_base:
                self.window[seqnum-self.send_base-1].state = 2 
            self.window[seqnum-self.send_base].acktime += 1

    def getACKTimeBySeqnum(self, seqnum):
        if (seqnum >= self.send_base and seqnum < self.send_base + len(self.window)):
            return self.window[seqnum-self.send_base].acktime
        # 特殊情况，最后一块到达
        if seqnum == self.send_base + len(self.window):
            return -1
        return 0

    def getContentBySeqnum(self, seqnum):
        if (seqnum >= self.send_base and seqnum < self.send_base + len(self.window)):
            return self.window[seqnum-self.send_base].content
        return None

    def update(self):
        size = 0
        while self.window[0].state == 2:
            size += len(self.window[0].content)
            self.window.pop(0)
            self.send_base += 1
        return size
        
    def updateSendBase(self, send_base):
        size = 0
        if send_base > self.send_base:
            num = send_base - self.send_base
            for i in range(num):
                size += len(self.window[0].content)
                self.window.pop(0)
            self.send_base = send_base
        return size

    def getSendList(self, cwnd):
        cwnd = min(cwnd, self.rwnd, len(self.window))
        List = []
        while cwnd + self.send_base > self.nextseqnum:
            List.append(self.getItemToSend())
        return List
        