from PyQt5.QtWidgets import QMainWindow, QApplication, QLabel, QTextEdit, QPushButton
from PyQt5 import uic
import sys
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import cv2
import socket
import errno
import time
import os

class UI(QMainWindow):
    def __init__(self):
        super(UI, self).__init__()

        self.my_username = input("Username : ")
        # Load the ui file
        uic.loadUi("signApp.ui", self)

        # Define Widgets
        self.usernameLable = self.findChild(QLabel, "usernameLabel")
        self.recvLabel = self.findChild(QLabel, "recvLabel")
        self.sendLabel = self.findChild(QLabel, "sendLabel")
        self.startButton = self.findChild(QPushButton, "startButton")
        self.stopButton = self.findChild(QPushButton, "stopButton")

        self.usernameLabel.setText("Username : " + self.my_username)
        # Do something with Event
        # self.button.clicked.connect(self.clicker)
        # def clicker():
        #   do something
        self.recordingWorker = RecordingWorker()
        self.recordingWorker.ImageUpdate.connect(self.ImageUpdateSlot)
        self.playWorker = PlayWorker()
        self.playWorker.ImageUpdate.connect(self.ImageUpdateSlotForRecvFile)
        self.startButton.clicked.connect(self.startRecording)
        self.stopButton.clicked.connect(self.stopRecording)

        self.fileSocketWorker = FileSocketWorker(self.my_username)
        self.fileSocketWorker.start()
        self.fileSocketWorker.MessageUpdate.connect(self.MessageUpdateSlot)

        self.show()

    def MessageUpdateSlot(self, message):
        self.usernameLabel.setText( message + " => " + self.my_username)

        if not self.playWorker.isRunning():
            print("=======================================================================")
            print(" true or false ")
            print(self.playWorker.isRunning())
            self.playWorker.start()
        else:
            print("Ding ...")

        # need to improve the followings... I think ....another thread needed.
    def ImageUpdateSlot(self, image):
        self.sendLabel.setPixmap(QPixmap.fromImage(image))

    def ImageUpdateSlotForRecvFile(self, image):
        self.recvLabel.setPixmap(QPixmap.fromImage(image))

    def startRecording(self):
        self.usernameLabel.setText(self.my_username)
        if not self.recordingWorker.isRunning():
            self.recordingWorker.start()
        else:
            print("Ding ...")
        
    def stopRecording(self):
        if self.recordingWorker.isRunning():
            self.recordingWorker.stop()
            time.sleep(0.5)
            self.fileSocketWorker.send_file(self.recordingWorker.getRecordingFilename())

    def closeEvent(self, event):
        if self.recordingWorker.isRunning():
            self.recordingWorker.stop()


HEADER_LENGTH = 32
FMT = 'utf-8'

class FileSocketWorker(QThread):
    MessageUpdate = pyqtSignal(str)

    def __init__(self, username):
        super(FileSocketWorker, self).__init__()
        #self.IP = '127.0.0.1'
        # my aws server
        self.IP = '18.204.222.197'
        self.PORT = 5001
        self.my_username = username
        self.sock_setup()

    def sock_setup(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((self.IP, self.PORT))
        self.client_socket.setblocking(True)

        username = self.my_username.encode(FMT)
        username_header = f"{len(username):<{HEADER_LENGTH}}".encode(FMT)
        print(f"[{username_header}]")
        self.client_socket.send(username_header + username)

    def send_file(self, filename):
        # buffer_size = 2048
        filesize = os.path.getsize(filename)
        sFilesize = str(filesize)
        print(sFilesize, "what the hell")
        message_header = f"{sFilesize:>{HEADER_LENGTH}}".encode(FMT)
        #message_header.encode('utf-8')
        print(message_header)
        file_contents = None
        self.client_socket.send(message_header)
        with open(filename, 'rb') as readFile:
            file_contents = readFile.read()
        self.client_socket.send(file_contents)
        
    def send_message(self, send_string):
        if send_string:
            message = send_string.encode(FMT)
            message_header = f"{len(message) :<{HEADER_LENGTH}}".encode(FMT)
            self.client_socket.send(message_header + message)

    def run(self): # receive data from server
        print("Thread has just started...")
        while True:
            try:
                while True:
                    # receive things. sever always send username and message
                    username_header = self.client_socket.recv(HEADER_LENGTH)
                    # if sock is nonblocking and there is nodata in the recv buffer, it goes to IOError.
                    print("check point 1")
                    if not len(username_header):
                        print("connection closed by the server")
                        sys.exit()
                    print("check point 2")
                    username_length = int(username_header.decode(FMT).strip())
                    username = self.client_socket.recv(username_length).decode(FMT)

                    print("check point 3")
                    message_header = self.client_socket.recv(HEADER_LENGTH)
                    message_length = int(message_header.decode(FMT).strip())
                    print(f"filezise = {message_length}")
                    #contents = self.client_socket.recv(message_length)
                    #print(len(contents))

                    print("check point 4")
                    filename = 'default_client.avi'
                    buffer_size = 2048
                    with open(filename, 'wb') as writeFile:
                        while message_length != 0:
                            video_chunk = self.client_socket.recv(buffer_size)
                            message_length -= len(video_chunk)
                            writeFile.write(video_chunk)
                        """
                        while True:
                            if message_length <= buffer_size:
                                video_chunk = self.client_socket.recv(message_length)
                                writeFile.write(video_chunk)
                                print(f"remaining bytes = {message_length} received")
                                break
                            video_chunk = self.client_socket.recv(buffer_size)
                            writeFile.write(video_chunk)
                            message_length -= buffer_size
                            #print(f"remaining bytes = {message_length}")
                        """

                    #print("check point 5")
                    # event fire
                    self.MessageUpdate.emit(username)
                    #print("check point 6")
            except IOError as e: # if client_socket set nonblocking, IOError will be executed.
                if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
                    print('Reading error', str(e))
                    sys.exit()
                print("continue ..", str(e))
                time.sleep(0.5)
                continue
            except Exception as e:
                print('General error in run function', str(e))
                sys.exit()

class RecordingWorker(QThread):
    ImageUpdate = pyqtSignal(QImage)

    def __init__(self):
        super(RecordingWorker, self).__init__()
        self.ThreadActive = False
        self.recordingFilename = 'chat_video.avi'

    def setRecordingFilename(self, filename):
        self.recordingFilename = filename

    def getRecordingFilename(self):
        return self.recordingFilename

    def run(self):
        self.ThreadActive = True
        self.Capture = cv2.VideoCapture(0)
        fourcc = cv2.VideoWriter_fourcc(*'DIVX')
        # VideoWriter filename, codec, frame rate = 30, size
        self.out = cv2.VideoWriter(self.recordingFilename, fourcc, 20.0, (640,480))
        while self.ThreadActive:
            ret, frame = self.Capture.read()
            self.out.write(frame)
            if ret:
                Image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = Image.shape
                bytes_per_line = ch * w
                #FlippedImage = cv2.flip(Image, 1) # 1 means vertical axis
                #ConvertToQtFormat = QImage(FlippedImage.data, FlippedImage.shape[1], FlippedImage.shape[0], QImage.Format_RGB888)
                ConvertToQtFormat = QImage(Image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                Pic = ConvertToQtFormat.scaled(640, 480, Qt.KeepAspectRatio)
                self.ImageUpdate.emit(Pic)
        else:
            self.Capture.release()
            self.out.release()
            filesize = os.path.getsize(self.recordingFilename)
            print("out.release and video file size = {filesize}")

    def stop(self):
        self.ThreadActive = False
        self.quit()

    def isRunning(self):
        return self.ThreadActive


class PlayWorker(QThread):
    ImageUpdate = pyqtSignal(QImage)

    def __init__(self):
        super(PlayWorker, self).__init__()
        self.ThreadActive = False
        self.playFilename = 'default_client.avi'

    def setPlayFilename(self, filename):
        self.playFilename = filename

    def getPlayFilename(self):
        return self.playFilename

    def run(self):
        #filename = 'default_client.avi'
        self.Capture = cv2.VideoCapture(self.playFilename)
        print("Start to play the Video ")
        fps = self.Capture.get(cv2.CAP_PROP_FPS)

        self.ThreadActive = True
        while self.ThreadActive:
            ret, frame = self.Capture.read()
            #self.out.write(frame)
            if ret:
                now = time.time()

                Image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = Image.shape
                bytes_per_line = ch * w
                #FlippedImage = cv2.flip(Image, 1) # 1 means vertical axis
                #ConvertToQtFormat = QImage(FlippedImage.data, FlippedImage.shape[1], FlippedImage.shape[0], QImage.Format_RGB888)
                ConvertToQtFormat = QImage(Image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                Pic = ConvertToQtFormat.scaled(640, 480, Qt.KeepAspectRatio)
                self.ImageUpdate.emit(Pic)

                timeDiff = time.time() - now
                if (timeDiff < 1.0/(fps)):
                    time.sleep(1.0/(fps) - timeDiff)
            else:
                self.ThreadActive = False
        else:
            self.Capture.release()
            #self.out.release()
            filesize = os.path.getsize(self.playFilename)
            print(f"out.release and video file size = {filesize}")
            self.quit()

    def stop(self):
        self.ThreadActive = False
        self.quit()

    def isRunning(self):
        return self.ThreadActive

# Initialize the App
app = QApplication(sys.argv)
UIWindow = UI()
app.exec_()
