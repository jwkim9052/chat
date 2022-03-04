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
import platform

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

        self.recordingWorker = RecordingWorker()
        self.recordingWorker.ImageUpdate.connect(self.ImageUpdateSlot)
        self.recordingWorker.finished.connect(self.threadFinished)
        self.playWorker = PlayWorker()
        self.playWorker.ImageUpdate.connect(self.ImageUpdateSlotForRecvFile)
        self.startButton.clicked.connect(self.startRecording)
        self.stopButton.clicked.connect(self.stopRecording)

        self.fileSocketWorker = FileSocketWorker(self.my_username)
        self.fileSocketWorker.start()
        self.fileSocketWorker.MessageUpdate.connect(self.MessageUpdateSlot)

        self.show()

    def threadFinished(self):
        # too many event has fired from QThread. 
        print("===== check that the thread has just finished == for debug purpose")

    def MessageUpdateSlot(self, message):
        self.usernameLabel.setText( message + " => " + self.my_username)

        if not self.playWorker.is_running():
            print("Playing a new arrived video message")
            print(self.playWorker.is_running())
            self.playWorker.start()
        else:
            print("New Message has arrived but I am busy to play the previous one ...")

    def ImageUpdateSlot(self, image):
        self.sendLabel.setPixmap(QPixmap.fromImage(image))

    def ImageUpdateSlotForRecvFile(self, image):
        self.recvLabel.setPixmap(QPixmap.fromImage(image))

    def startRecording(self):
        self.usernameLabel.setText(self.my_username)
        if not self.recordingWorker.is_running():
            self.recordingWorker.start()
        else:
            print("Ding ...")

    def stopRecording(self):
        if self.recordingWorker.is_running():
            self.recordingWorker.stop()
            time.sleep(0.5)
            self.fileSocketWorker.send_file(self.recordingWorker.getRecordingFilename())
        else:
            print("Dong ...")

    def closeEvent(self, event):
        if self.recordingWorker.is_running():
            self.recordingWorker.stop()


HEADER_LENGTH = 32
FMT = 'utf-8'

class FileSocketWorker(QThread):
    MessageUpdate = pyqtSignal(str)

    def __init__(self, username):
        super(FileSocketWorker, self).__init__()
        #self.IP = '127.0.0.1'
        # my aws server
        #self.IP = '18.204.222.197'
        self.IP = '220.149.231.128'
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
        message_header = f"{sFilesize:>{HEADER_LENGTH}}".encode(FMT)
        #print(message_header)
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
        print("FileSocketWorker Thread has just started...")
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
                    print(f"filezise = {message_length}")
                    #contents = self.client_socket.recv(message_length)
                    #print(len(contents))

                    filename = 'default_client.mp4'
                    buffer_size = 2048
                    with open(filename, 'wb') as writeFile:
                        while message_length != 0:
                            video_chunk = self.client_socket.recv(buffer_size)
                            message_length -= len(video_chunk)
                            writeFile.write(video_chunk)
                    # event fire
                    self.MessageUpdate.emit(username)
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
        self.recordingFilename = 'chat_video.mp4'
        self.frames = []
        self.is_windows = any(platform.win32_ver())

    def setRecordingFilename(self, filename):
        self.recordingFilename = filename

    def getRecordingFilename(self):
        return self.recordingFilename

    def run(self):
        self.ThreadActive = True
        if self.is_windows:
            self.Capture = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            print("Windows.. cv2.VideoCapture(0, cv2.CAP_DSHOW)")
        else:
            self.Capture = cv2.VideoCapture(0)
        self.frames = []
        #fourcc = cv2.VideoWriter_fourcc(*'DIVX')
        # VideoWriter filename, codec, frame rate = 30, size
        fps = 30.0
        #self.out = cv2.VideoWriter(self.recordingFilename, fourcc, fps, (640,480))
        frame_count = 1
        while self.ThreadActive:
            now = time.time()
            ret, frame = self.Capture.read()
            if ret:
                #self.out.write(frame)
                self.frames.append(frame)
                frame_count += 1
                Image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = Image.shape
                bytes_per_line = ch * w
                #FlippedImage = cv2.flip(Image, 1) # 1 means vertical axis
                #ConvertToQtFormat = QImage(FlippedImage.data, FlippedImage.shape[1], FlippedImage.shape[0], QImage.Format_RGB888)
                ConvertToQtFormat = QImage(Image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                Pic = ConvertToQtFormat.scaled(640, 480, Qt.KeepAspectRatio)
                self.ImageUpdate.emit(Pic)
            else:
                print("debug purpose for Capture and write")
            timeDiff = time.time() - now
            if(timeDiff < 1.0/(fps)):
                time.sleep(1.0/(fps) - timeDiff)
        else:
            filesize = os.path.getsize(self.recordingFilename)
            print(f"out.release and video file size = {filesize} frame count = {frame_count}")

    def stop(self):
        # the order very important...
        self.Capture.release()

        ### writing frames to file
        #fourcc = cv2.VideoWriter_fourcc(*'DIVX')
        #fourcc = cv2.VideoWriter_fourcc(*'MP4V') Opencv:ffmpeg does not support MP4V.... in which i am coding.
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = 30.0
        self.out = cv2.VideoWriter(self.recordingFilename, fourcc, fps, (640,480))

        for frame in self.frames:
            self.out.write(frame)
        ### the end of writing frames
        self.out.release()

        self.ThreadActive = False
        self.quit()

    def is_running(self):
        return self.ThreadActive


class PlayWorker(QThread):
    ImageUpdate = pyqtSignal(QImage)

    def __init__(self):
        super(PlayWorker, self).__init__()
        self.ThreadActive = False
        self.playFilename = 'default_client.mp4'

    def setPlayFilename(self, filename):
        self.playFilename = filename

    def getPlayFilename(self):
        return self.playFilename

    def run(self):
        print("PlayWorker Thread has just started to play the Video ")
        self.Capture = cv2.VideoCapture(self.playFilename)
        fps = self.Capture.get(cv2.CAP_PROP_FPS)

        self.ThreadActive = True
        while self.ThreadActive:
            ret, frame = self.Capture.read()
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
            filesize = os.path.getsize(self.playFilename)
            print(f"out.release and video file size = {filesize}")

    def stop(self):
        self.ThreadActive = False
        self.Capture.release()
        self.quit()

    def is_running(self):
        return self.ThreadActive

# Initialize the App
app = QApplication(sys.argv)
UIWindow = UI()
app.exec_()
