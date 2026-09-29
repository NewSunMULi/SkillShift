import cv2
from PIL import ImageGrab

class InputImg:
    def __init__(self):
        self.imgBuffer = None

    def get(self):
        self.imgBuffer = ImageGrab.grab()

    def show(self):
        cv2.imshow("img", self.imgBuffer)