from PyQt5.QtWidgets import QMainWindow, QApplication, QLabel, QTextEdit, QPushButton, QLineEdit
from PyQt5 import uic
from PyQt5.QtGui import QColor
from PyQt5.QtCore import *
import socket
import errno
import time
import sys

class UI(QMainWindow):
    def __init__(self):
        super(UI, self).__init__()

        username = input("Username : ")
        # Load the ui file
        uic.loadUi("textApp.ui", self)

        # Define Widgets
        self.usernameLable = self.findChild(QLabel, "usernameLabel")
        self.textEdit = self.findChild(QTextEdit, "textEdit")
        self.lineEdit = self.findChild(QLineEdit, "lineEdit")
        self.sendButton = self.findChild(QPushButton, "sendButton")

        self.textEdit.setReadOnly(True)
        #self.textEdit.setDisabled(True)
        self.sendButton.clicked.connect(self.sendButton_Event)
        self.lineEdit.returnPressed.connect(self.sendButton_Event)
        self.usernameLabel.setText("Username : " + username)


        # Do something with Event
        # self.button.clicked.connect(self.clicker)
        # def clicker():
        #   do something

        self.textSocketWorker = TextSocketWorker(username)
        self.textSocketWorker.start()
        self.textSocketWorker.MessageUpdate.connect(self.messageUpdateSlot)

        self.show()

    def sendButton_Event(self):
        input_string = self.lineEdit.text()
        self.textEdit.append("You typed : "+input_string)
        self.textSocketWorker.send_message(input_string)
        print(input_string)
        self.lineEdit.clear()

    def messageUpdateSlot(self, recv_string):
        self.textEdit.append(recv_string)
        print(recv_string)

HEADER_LENGTH = 32
FMT = 'utf-8'

class TextSocketWorker(QThread):
    MessageUpdate = pyqtSignal(str)


    def __init__(self, username):
        super(TextSocketWorker, self).__init__()
        #self.IP = '127.0.0.1'
        # This is my aws server
        self.IP = '18.204.222.197'
        self.PORT = 5000
        self.my_username = username
        self.sock_setup()

    def sock_setup(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((self.IP, self.PORT))
        self.client_socket.setblocking(True)

        username = self.my_username.encode('utf-8')
        username_header = f"{len(username):<{HEADER_LENGTH}}".encode(FMT)
        self.client_socket.send(username_header + username)

    def send_message(self, send_string):
        if send_string:
            message = send_string.encode(FMT)
            message_header = f"{len(message) :< {HEADER_LENGTH}}".encode(FMT)
            self.client_socket.send(message_header + message)

    def run(self): # receive data from server
        print("Thread has just started...")
        while True:
            try:
                while True:
                    # receive things. sever always send username and message
                    username_header = self.client_socket.recv(HEADER_LENGTH)
                    # if sock is nonblocking and there is nodata in the recv buffer, it goes to IOError.
                    if not len(username_header):
                        print("connection closed by the server")
                        sys.exit()
                    username_length = int(username_header.decode(FMT).strip())
                    username = self.client_socket.recv(username_length).decode(FMT)

                    message_header = self.client_socket.recv(HEADER_LENGTH)
                    message_length = int(message_header.decode(FMT).strip())
                    message = self.client_socket.recv(message_length).decode(FMT)
                    # event fire
                    self.MessageUpdate.emit(username + " : " + message)
            except IOError as e: # if client_socket set nonblocking, IOError will be executed.
                if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
                    print('Reading error', str(e))
                    sys.exit()
                print("continue ..", str(e))
                time.sleep(0.5)
                continue
            except Exception as e:
                print('General error', str(e))
                sys.exit()

# Initialize the App
app = QApplication(sys.argv)
UIWindow = UI()
app.exec_()
