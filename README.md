# LFTP

实现一个网络应用**LFTP**, 用于互联网中的两台电脑的大文件传输。

## 介绍

1. 客户端－服务端　服务模型
2. 包含一个客户端程序和一个服务端程序，客户端程序既可以可以往服务端发送大文件，也可以从服务端下载文件。
```
    发送文件:
    LFTP lsend myserver mylargefile
    下载文件:
    LFTP lget myserver mylargefile
    参数 myserver可以是url地址或者ip地址
```

3. LFTP 使用UDP传输层协议
4. LFTP 可以像TCP一样实现100%可靠
5. LFTP 实现了与TCP类似的流控制功能
6. LFTP 实现了与TCP类似的阻塞控制功能
7. LFTP 服务端可以同时服务多个客户
8. LFTP 程序在运行时可以提供有意义的debug信息


