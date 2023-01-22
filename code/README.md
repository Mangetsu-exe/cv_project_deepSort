# CV_Project_DeepSort

## Folder organization

output/
├── code/
├   ├── configs/
├   ├── deep_sort/
├   ├── utils_ds/
├   ├── vids/
├   ├   ├──input videos
├   ├── yolov5/
├   ├── main.py
├── tracked_videos/
├   ├── link.txt
├── project_report.pdf

## Prepare 
1) Install all dependencies
~~~
bash
$ pip install -r requirements.txt
~~~

2) Create a videos to add the videos to detect

## Run
~~~
# on video file
python main.py --input_path [VIDEO_FILE_NAME] --display
~~~

## Implementation details

- *Yolo model:* For training the yolo model we used the project: [Ultralytics YoloV5](https://github.com/ultralytics/yolov5) 

- *DeepSort* we used the frame work proportioned for YoloV5 and Pytorch [Github repo](https://github.com/HowieMa/DeepSORT_YOLOv5_Pytorch), then using the output bounding boxes of the tracking stage we added the tracking path to the videos.

