from ultralytics import YOLO


class DynamicYOLO:
    def __init__(self):
        self.yolo = YOLO("yolo8n.pt")

    def forward(self,x):
        pass