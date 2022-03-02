import socket
import select
import time
import os

HEADER_LENGTH = 32
FMT = "utf-8"

#IP = "127.0.0.1"
IP = "172.31.40.194"
PORT = 5000
PORT2= 5001

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

server_socket.bind((IP, PORT))
server_socket.listen()

server_socket2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket2.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

server_socket2.bind((IP, PORT2))
server_socket2.listen()

sockets_list = [server_socket, server_socket2]
clients = {}
clients2 = {}


def receive_bytes(client_socket):
    try:
        message_header = client_socket.recv(HEADER_LENGTH)

        if not len(message_header):
            print("receiving signal data from byte socket")
            return False

        message_length = int(message_header.decode(FMT, errors="ignore").strip())
        print(f"file length from message_length {message_length}")

        user = clients2[notified_socket]
        print(f"the sender is {user['data'].decode(FMT)}")
        filename = user['data'].decode(FMT) + "_srv_tmp.avi"

        video_file = open(filename, 'wb')

        while message_length > 0:
            video_chunk = client_socket.recv(2048)
            #print(f"check point video chunk = {message_length} video_chunk size = {len(video_chunk)}")
            message_length -= len(video_chunk)
            video_file.write(video_chunk)

        video_file.close()
        result = {"header" : message_header, "filename" : filename.encode(FMT) }
        #return {"header" : message_header, "filename" : filename.encode(FMT) }
        return result
    except Exception as e:
        print("Error while receiving a video file in receive_bytes()", str(e))
        return False

def receive_message(client_socket):
    try:
        message_header = client_socket.recv(HEADER_LENGTH)

        if not len(message_header):
            print("receiving signal data from text socket")
            return False

        message_length = int(message_header.decode(FMT).strip())
        return {"header" : message_header, "data" : client_socket.recv(message_length)}
    except Exception as e:
        print("Error while receiving a text message", str(e))
        return False

while True:
    read_sockets, _, exception_sockets = select.select(sockets_list, [], sockets_list)

    for notified_socket in read_sockets:
        if notified_socket == server_socket:
            client_socket, client_address = server_socket.accept()

            user = receive_message(client_socket)

            if user is False:
                print("what ? ###############1")
                continue

            sockets_list.append(client_socket)
            clients[client_socket] = user
            #print(clients[client_socket])
            print(clients)
            print(f"Accepted new connection from {client_address[0]}:{client_address[1]} username:{user['data'].decode(FMT)}")
        elif notified_socket == server_socket2:
            client_socket, client_address = server_socket2.accept()

            user = receive_message(client_socket)

            if user is False:
                print("what ? ###############1")
                continue

            sockets_list.append(client_socket)
            clients2[client_socket] = user
            print(clients2[client_socket])
            print(f"Accepted new connection from {client_address[0]}:{client_address[1]} username:{user['data'].decode(FMT)}")
        elif notified_socket in clients:
            print("Text User sent a message")
            message = receive_message(notified_socket)

            if message is False:
                print(f"Closed connection from {clients[notified_socket]['data'].decode(FMT)}")
                sockets_list.remove(notified_socket)
                del clients[notified_socket]
                continue

            user = clients[notified_socket]
            print(f"Received message from {user['data'].decode(FMT)}:{message['data'].decode(FMT)}")

            for client_socket in clients:
                if client_socket != notified_socket:
                    client_socket.send(user['header']+user['data']+message['header']+message['data'])

            for client_socket in clients2:
                if client_socket != notified_socket:
                    filename = 'default_animation.avi'
                    default_file_size = os.path.getsize(filename)
                    sFilesize = str(default_file_size)
                    #print(f"file size = {sFilesize}")
                    msg_header = f"{sFilesize:>{HEADER_LENGTH}}".encode(FMT)
                    file_contents = None
                    client_socket.send(user['header']+user['data']) #i+message_header+filename)
                    with open(filename, 'rb') as readFile:
                        file_contents = readFile.read()
                        f_s = len(file_contents)
                        #print(f"file_contents = {f_s}")
                    client_socket.send(msg_header)
                    client_socket.send(file_contents)

        elif notified_socket in clients2:
            print("Sign Language User sent a video content")
            msg_file = receive_bytes(notified_socket)

            if msg_file is False:
                print(f"Closed connection from {clients2[notified_socket]['data'].decode(FMT)}")
                sockets_list.remove(notified_socket)
                del clients2[notified_socket]
                continue

            user = clients2[notified_socket]
            print(f"Received message from {user['data'].decode(FMT)}:{msg_file['filename'].decode(FMT)}")

            for client_socket in clients2:
                if client_socket != notified_socket:
                    #client_socket.send(user['header']+user['data']+message['header']+message['data'])
                    client_socket.send(user['header']+user['data'])
                    filename = msg_file['filename']

                    video_file = open(filename,'rb')
                    message_length = int(msg_file['header'].decode(FMT).strip())
                    video_contents = video_file.read()
                    video_file.close()

                    client_socket.send(msg_file['header'])
                    client_socket.send(video_contents)

            filename = msg_file['filename']
            message_header = f"{len(filename) : <{HEADER_LENGTH}}".encode(FMT)

            for client_socket in clients:
                if client_socket != notified_socket:
                    client_socket.send(user['header']+user['data']+message_header+filename)

    for notified_socket in exception_sockets:
        sockets_list.remove(notified_socket)
        del clients[notified_socket]
