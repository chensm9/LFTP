import sys
sys.path.append("..")
from Helper.LFTPMessage import LFTPMessage
from Helper.LFTPRecvWindow import LFTPRecvWindow
from Helper.LFTPSendWindow import LFTPSendWindow
from Utils.Log import *

from socket import *
import time
import os
import struct
import json
import threading
import random
from progressbar import *

from enum import Enum

class State(Enum):
    CLOSED = 0
    LISTEN = 1
    SYN_RCVN = 2
    ESTABLISHED = 3
    CLOSN_WAIT = 4
    LAST_ACK = 5

class LFTPserver:
    def __init__(self, server_type, host, port, bufferSize):
        self.server_type = server_type
        self.host = host
        self.port = port
        self.bufferSize = bufferSize
        self.udpServer = socket(AF_INET,SOCK_DGRAM)
        self.udpServer.bind((host, port))
        self.state = State.LISTEN # 初始状态

        # 用于三次握手
        self.client_isn = -1
        self.server_isn = random.randint(0, 1000)
        self.fileInfo = None

    def start(self):
        if self.server_type == 'data':
            self.handshake()
            if (self.state == State.ESTABLISHED):
                log_info("客户端传输类型：",self.fileInfo["LFTPType"])
                if self.fileInfo["LFTPType"] == "UPLOAD":
                    self.recvfile()
                elif self.fileInfo["LFTPType"] == "DOWNLOAD":
                    self.sendfile()
            else:
                log_error("连接建立失败")
            # self.udpServer.close()
            # self.state = State.CLOSED
        elif self.server_type == 'control':
            self.ControlHandShake()

    def ControlHandShake(self):
        self.serverList = []
        self.base_port = 9000
        self.max_port = 9099
        for port in range(self.base_port, self.max_port):
            self.serverList.append(None)
        while True:
            log_info("等待用户连接传入")
            message, addr = self.udpServer.recvfrom(self.bufferSize)
            log_info(addr)
            message = LFTPMessage.unpack(message)
            log_info("getport：", message.getport)
            print(message)
            if message.getport == 1:
                for port in range(self.base_port, self.max_port):
                    if self.serverList[port-self.base_port] == None or self.serverList[port-self.base_port].state == State.CLOSED:
                        log_info("用户连接传入，分配端口：", port)
                        self.serverList[port-self.base_port] = LFTPserver(server_type='data', host='', port=port, bufferSize=2048)
                        threading.Thread(target=self.ServerRun, args=(self.serverList[port-self.base_port],)).start()
                        content = {"port": port}
                        content = json.dumps(content).encode("utf-8")
                        resp = LFTPMessage(getport=1, content_size=len(content), content=content)
                        self.udpServer.sendto(resp.pack(), addr)
                        break

    def ServerRun(self, server):
        server.start()

    def handshake(self):
        log_info("等待连接中")
        self.udpServer.settimeout(3)
        while True:
            try:
                message, self.client_addr = self.udpServer.recvfrom(self.bufferSize)
            except Exception as e:
                log_error("客户连接断开，超时关闭，当前端口：", self.port)
                self.state = State.CLOSED
                break
            message = LFTPMessage.unpack(message)
            if self.state == State.LISTEN:
                if message.SYN == 1:
                    log_info("收到第一次握手报文",self.client_addr)
                    self.client_isn = message.seqnum
                    res = LFTPMessage(SYN=1, ACK = 1, seqnum=self.server_isn, acknum=self.client_isn+1)
                    self.fileInfo = json.loads(message.content[:message.content_size].decode("utf-8"))
                    if self.fileInfo["LFTPType"] == "UPLOAD":
                        res.content = message.content
                    elif self.fileInfo["LFTPType"] == "DOWNLOAD":
                        try:
                            self.fileInfo["filesize"] = os.path.getsize(self.fileInfo["filename"])
                        except Exception as e:
                            log_error("对应文件已丢失，无法提供下载：", self.fileInfo["filename"])
                            self.fileInfo["filesize"] = -1
                            res.content = json.dumps(self.fileInfo).encode("utf-8")
                            res.content_size = len(res.content)
                            self.udpServer.sendto(res.pack(), self.client_addr)
                            return
                    res.content = json.dumps(self.fileInfo).encode("utf-8")
                    res.content_size = len(res.content)
                    self.udpServer.sendto(res.pack(), self.client_addr)
                    self.state = State.SYN_RCVN
                    threading.Timer(1, self.handshakeTimer, [self.state]).start()
                    log_info("发送第二次握手报文",self.client_addr)
            elif self.state == State.SYN_RCVN:
                if message.SYN == 0 and message.ACK == 1 and message.seqnum == self.client_isn+1 and message.acknum == self.server_isn+1:
                    self.state = State.ESTABLISHED
                    log_info("收到第三次握手报文",self.client_addr)
                    log_info("建立连接成功", self.client_addr)
                    break
                
    def handshakeTimer(self, state):
        if (state == self.state):
            if (state == State.SYN_RCVN):
                log_warn("第二次或第三次握手失败,超时丢包转回LISTEN状态")
                self.state = State.LISTEN   # 超时丢包转回LISTEN状态

    def recvfile(self):
        filename = self.fileInfo["filename"]
        filesize = self.fileInfo["filesize"]

        self.recv_base = 0  # 当前窗口基序号
        self.N = 1000 # 窗口大小
        self.window = [] # 接收方窗口
        for i in range(self.N):
            self.window.append(None)

        recvsize = 0 # 已接收数据大小
        log_info("开始接收文件 %s"%(filename))
        with open(filename, 'wb') as f:
            pbar = ProgressBar().start()
            while True:
                try:
                    message, addr = self.udpServer.recvfrom(self.bufferSize)
                except Exception as e:
                    print(self.port, e)
                    if (recvsize == filesize):
                        pbar.finish()
                        log_info("接收完毕，断开连接")
                    else:
                        log_error("连接已断开")
                    break
                message = LFTPMessage.unpack(message)
                seqnum = message.seqnum
                content = message.content
                content_size = message.content_size
                if (seqnum >= self.recv_base and seqnum < self.recv_base + self.N):
                    self.window[seqnum - self.recv_base] = content[:content_size]
                while self.window[0] != None:
                    f.write(self.window[0])
                    recvsize += len(self.window[0])
                    pbar.update(int(recvsize / filesize * 100))
                    self.window.pop(0)
                    self.window.append(None)
                    self.recv_base += 1

                rwnd = 0
                for item in self.window:
                    if item == None:
                        rwnd += 1
                response = LFTPMessage(ACK=1, seqnum=seqnum, rwnd=rwnd, acknum=self.recv_base)

                if (seqnum <= self.recv_base + self.N):
                    self.udpServer.sendto(response.pack(), addr)

    def sendfile(self):
        # 握手完毕未进入连接建立状态，退出
        if self.state != State.ESTABLISHED:
            log_error("连接建立失败")
            self.state = State.CLOSED
            return
        self.cwnd = 1
        self.rwnd = 1000
        self.ssthresh = 8
        self.lock = threading.Lock()
        # 定时器
        self.timer = None
        self.TimeoutInterval = 1
        # 发送窗口
        self.send_window = LFTPSendWindow(0, self.rwnd)
        filename = self.fileInfo["filename"]
        filesize = self.fileInfo["filesize"]

        self.send_buffersize = 1024

        # 应用端持续读取数据填入发送窗口
        with open(filename, 'rb') as f:
            log_info("开始传送文件:",filename)
            threading.Thread(target=self.recvACK, args=(filesize,)).start()
            while filesize > 0:
                self.lock.acquire()
                if (self.send_window.isFull()): # 窗口已经满了
                    self.lock.release()
                    time.sleep(0.00001)
                    continue
                if filesize >= self.send_buffersize:
                    content = f.read(self.send_buffersize)  # 每次读出来的文件内容
                    self.send_window.append(content)
                    self.lock.release()
                    filesize -= self.send_buffersize
                else:
                    content = f.read(filesize)  # 最后一次读出来的文件内容
                    self.send_window.append(content)
                    self.lock.release()
                    filesize = 0
                    break

    # 接收客户端ACK，滑动窗口
    def recvACK(self, filesize):

        while True:
            self.lock.acquire()
            if self.send_window.isEmpty() == False:
                item = self.send_window.getItemToSend()
                if item != None:
                    self.lock.release()
                    break
            self.lock.release()

        first_message = LFTPMessage(seqnum=item.seqnum, content_size=len(item.content), content=item.content)
        self.udpServer.sendto(first_message.pack(), self.client_addr)
        # 设置超时定时器
        self.timer = threading.Timer(self.TimeoutInterval, self.TimeOutAndReSend)
        self.timer.start()

        recvSize = 0
        while(True):
            # 接收信息
            try:
                message = self.udpServer.recv(2048)
            except Exception as e:
                if filesize == recvSize:
                    # pbar.finish()
                    log_info("服务端接收完毕")
                    self.timer.cancel()
                else:
                    self.timer.cancel()
                    log_error("超时重连失败")
                break
            message = LFTPMessage.unpack(message)
            acknum = message.acknum

            self.lock.acquire()
            # 更新滑动窗口
            if self.cwnd < self.ssthresh:
                self.cwnd += 1
            else:
                self.cwnd += 1/int(self.cwnd)
            # 更新rwnd
            self.send_window.ACKseqnum(acknum)
            self.rwnd = message.rwnd
            self.send_window.rwnd = message.rwnd
            log_info("rwnd: ", self.rwnd, ", cwnd: ", self.cwnd)
             # 确认一波
            log_info(acknum, " ACKTIME: ",self.send_window.getACKTimeBySeqnum(acknum))
            if self.send_window.getACKTimeBySeqnum(acknum) == 4:
                # 三次冗余进行重传，同时更新cwnd和ssthresh
                log_warn("三次冗余", acknum)
                self.ssthresh = self.cwnd/2
                self.cwnd = self.cwnd/2+3
                r_content = self.send_window.getContentBySeqnum(acknum)
                r_message = LFTPMessage(seqnum=acknum, content_size=len(r_content), content=r_content)
                self.udpServer.sendto(r_message.pack(), self.client_addr)
                # 重新设置超时定时器
                self.timer.cancel()
                self.timer = threading.Timer(self.TimeoutInterval, self.TimeOutAndReSend)
                self.timer.start()
            elif self.send_window.getACKTimeBySeqnum(acknum) == 1:
                # 首次接收到，send_base改变
                recvSize += self.send_window.updateSendBase(acknum)
                List = self.send_window.getSendList(self.cwnd)
                for item in List:
                    message = LFTPMessage(seqnum=item.seqnum, content_size=len(item.content), content=item.content)
                    self.udpServer.sendto(message.pack(), self.client_addr)
                # 重新设置超时定时器
                self.timer.cancel()
                self.timer = threading.Timer(self.TimeoutInterval, self.TimeOutAndReSend)
                self.timer.start()
            elif self.send_window.getACKTimeBySeqnum(acknum) == -1:
                log_info("服务端接收完毕")
                self.timer.cancel()
                break

            self.lock.release()

            print(filesize, "", recvSize)
            # pbar.update(int(recvSize/filesize)*100)

            if filesize == recvSize:
                pbar.finish()
                log_info("服务端接收完毕")
                self.timer.cancel()
                break
            

    # 定时器，超时重传，必定重传的是send_base
    def TimeOutAndReSend(self):
        self.lock.acquire()
        self.ssthresh = self.cwnd/2
        self.cwnd = 1
        seqnum = self.send_window.send_base
        content = self.send_window.getContentBySeqnum(seqnum)
        self.lock.release()
        if content == None:
            return
        log_warn("超时重传：", seqnum)
        message = LFTPMessage(seqnum=seqnum, content_size=len(content), content=content)
        self.udpServer.sendto(message.pack(), self.client_addr)
        self.timer.cancel()
        self.timer = threading.Timer(self.timer.interval*2, self.TimeOutAndReSend)
        self.timer.start()

if __name__ == "__main__":
    contrl_server = LFTPserver(server_type='control', host='', port=12345, bufferSize=2048)
    contrl_server.start()