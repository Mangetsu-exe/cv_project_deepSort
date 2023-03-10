import torch.backends.cudnn as cudnn
import torch
import cv2
import warnings
import numpy as np
import time
import sys
import argparse
import os
import math
from deep_sort import build_tracker
from utils.draw import draw_boxes, compute_color_for_labels
from utils.parser import get_config
from yolov5.utils.general import check_img_size, non_max_suppression, xyxy2xywh, scale_coords
from yolov5.utils.datasets import letterbox
from yolov5.utils.torch_utils import select_device, time_synchronized

currentUrl = os.path.dirname(__file__)
print(os.path.abspath(os.path.join(currentUrl, 'yolov5')))
sys.path.append(os.path.abspath(os.path.join(currentUrl, 'yolov5')))

cudnn.benchmark = True

class VideoTracker(object):
    def __init__(self, args):
        print('Initialize DeepSORT & YOLO-V5')
        # ***************** Initialize ******************************************************
        self.args = args
        # image size in detector, default is 640
        self.img_size = args.img_size
        self.frame_interval = args.frame_interval       # frequency

        self.device = select_device(args.device)
        self.half = self.device.type != 'cpu'  # half precision only supported on CUDA

        # create video capture ****************
        #if args.display:
        #    cv2.namedWindow("test", cv2.WINDOW_NORMAL)
        #    cv2.resizeWindow("test", args.display_width, args.display_height)

        self.vdo = cv2.VideoCapture()

        # ***************************** initialize DeepSORT **********************************
        cfg = get_config()
        cfg.merge_from_file(args.config_deepsort)

        use_cuda = self.device.type != 'cpu' and torch.cuda.is_available()
        self.deepsort = build_tracker(cfg, use_cuda=use_cuda)

        # ***************************** initialize YOLO-V5 **********************************
        self.detector = torch.load(args.weights, map_location=self.device)['model'].float()  # load to FP32
        self.detector.to(self.device).eval()
        if self.half:
            self.detector.half()  # to FP16

        self.names = self.detector.module.names if hasattr(self.detector, 'module') else self.detector.names
        self.img_tracks = [[]]

        print('Done..')
        if self.device == 'cpu':
            warnings.warn("Running in cpu mode which maybe very slow!", UserWarning)

    def __enter__(self):
        # ************************* Load video from file *************************
        assert os.path.isfile(self.args.input_path), "Path error"
        mp4 = os.path.basename(self.args.input_path)
        file_name = os.path.splitext(mp4)[0]
        self.vdo.open(self.args.input_path)
        self.im_width = int(self.vdo.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.im_height = int(self.vdo.get(cv2.CAP_PROP_FRAME_HEIGHT))
        assert self.vdo.isOpened()
        print('Done. Load video file ', self.args.input_path)

        # ************************* create output *************************
        if self.args.save_path:
            os.makedirs(self.args.save_path, exist_ok=True)
            # path of saved video and results
            self.save_video_path = os.path.join(self.args.save_path, f"results_{file_name}.mp4")

            # create video writer
            fourcc = cv2.VideoWriter_fourcc(*self.args.fourcc)
            self.writer = cv2.VideoWriter(
                self.save_video_path,
                fourcc,
                self.vdo.get(cv2.CAP_PROP_FPS),
                (self.im_width, self.im_height)
                )
            print('Done. Create output file ', self.save_video_path)

        if self.args.save_txt:
            os.makedirs(self.args.save_txt, exist_ok=True)

        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.vdo.release()
        self.writer.release()
        if exc_type:
            print(exc_type, exc_value, exc_traceback)

    def run(self):
        yolo_time, sort_time, avg_fps = [], [], []
        t_start = time.time()

        idx_frame = 0
        last_out = None
        while self.vdo.grab():
            # Inference *********************************************************************
            t0 = time.time()
            _, img0 = self.vdo.retrieve()

            if idx_frame % self.args.frame_interval == 0:
                outputs, yt, st = self.image_track(img0) # (#ID, 5) x1,y1,x2,y2,id
                #print(outputs)
                last_out = outputs
                yolo_time.append(yt)
                sort_time.append(st)
                #print('Frame %d Done. YOLO-time:(%.3fs) SORT-time:(%.3fs)' % (idx_frame, yt, st))
            else:
                outputs = last_out  # directly use prediction in last frames
            t1 = time.time()
            avg_fps.append(t1 - t0)

            # visualize bbox  ********************************
            if len(outputs) > 0:
                bbox_xyxy  = outputs[:, :4]
                identities = outputs[:, -1]
                #print("identities = ", identities)
                img0, self.img_tracks = draw_boxes(img0, bbox_xyxy, identities, tracks=self.img_tracks)  # BGR
                # match tracks
                
                # add FPS information on output video
                text_scale = max(1, img0.shape[1] // 1600)
                cv2.putText(
                    img0,
                    #'frame: %d fps: %.2f' % (idx_frame, len(avg_fps) / sum(avg_fps)),
                    'frame: %d fps: %.2f id# %d' % (idx_frame, len(avg_fps) / sum(avg_fps), len(self.img_tracks)-1),
                    (20, 20 + text_scale),
                    cv2.FONT_HERSHEY_PLAIN,
                    text_scale,
                    (0, 0, 255),
                    thickness=2
                    )

            # match paths ******************************
        
            # draw tracks ******************************

            def dist_(pi, pj):
                return math.sqrt((pi[0]-pj[1])**2+(pi[0]-pj[1])**2)
        
            #print(self.img_tracks)
            if True:
                for i_ in range(1,len(self.img_tracks)):
                    for j_ in range(i_,len(self.img_tracks)):
                        if i_==j_ or len(self.img_tracks[j_]) < 2:
                            continue
                        trk_i = self.img_tracks[i_]
                        trk_j = self.img_tracks[j_] 
                        #print(tracks)
                        if dist_(trk_i[-1], trk_j[0]) < 30:
                            self.img_tracks[i_].extend(self.img_tracks[j_])
                            self.img_tracks[j_] = []
                            #print(j_,"->",i_)

            for track_id in range(len(self.img_tracks)):
                    cur_track = self.img_tracks[track_id] 
                    if len(cur_track) < 2:
                            continue
                    for coord_id in range(len(cur_track)):
                        if coord_id == 0:
                            continue
                        cv2.line(img0, cur_track[coord_id-1], cur_track[coord_id], (255,155,55), thickness=2) 
                        
            if self.args.display:
                cv2.imshow("Visual Results" , img0)
                if cv2.waitKey(1) == ord('q'):  # q to quit
                    cv2.destroyAllWindows()
                    break

            # save to video file *****************************
            if self.args.save_path:
                self.writer.write(img0)

            if self.args.save_txt:
                with open(self.args.save_txt + str(idx_frame).zfill(4) + '.txt', 'a') as f:
                    for i in range(len(outputs)):
                        x1, y1, x2, y2, idx = outputs[i]
                        f.write('{}\t{}\t{}\t{}\t{}\n'.format(x1, y1, x2, y2, idx))

            idx_frame += 1

        print('Avg YOLO time (%.3fs), Sort time (%.3fs) per frame' % (sum(yolo_time) / len(yolo_time), sum(sort_time)/len(sort_time)))
        t_end = time.time()
        print('Total time (%.3fs), Total Frame: %d' % (t_end - t_start, idx_frame))

    def image_track(self, im0):
        """
        :param im0: original image, BGR format
        :return:
        """
        # preprocess ************************************************************
        # Padded resize
        img = letterbox(im0, new_shape=self.img_size)[0]
        # Convert
        img = img[:, :, ::-1].transpose(2, 0, 1)  # BGR to RGB, to 3x416x416
        img = np.ascontiguousarray(img)

        # numpy to tensor
        img = torch.from_numpy(img).to(self.device)
        img = img.half() if self.half else img.float()  # uint8 to fp16/32
        img /= 255.0  # 0 - 255 to 0.0 - 1.0
        if img.ndimension() == 3:
            img = img.unsqueeze(0)
        s = '%gx%g ' % img.shape[2:]    # print string

        # Detection time *********************************************************
        # Inference
        t1 = time_synchronized()
        with torch.no_grad():
            pred = self.detector(img, augment=self.args.augment)[0]  # list: bz * [ (#obj, 6)]

        # Apply NMS and filter object other than person (cls:0)
        pred = non_max_suppression(
            pred, self.args.conf_thres,
            self.args.iou_thres,
            classes=self.args.classes,
            agnostic=self.args.agnostic_nms
        )
        t2 = time_synchronized()

        # get all obj ************************************************************
        det = pred[0]  # for video, bz is 1
        # det: (#obj, 6)  x1 y1 x2 y2 conf cls
        if det is not None and len(det):
            # Rescale boxes from img_size to original im0 size
            det[:, :4] = scale_coords(img.shape[2:], det[:, :4], im0.shape).round()

            # Print results. statistics of number of each obj
            for c in det[:, -1].unique():
                n = (det[:, -1] == c).sum()  # detections per class
                s += '%g %ss, ' % (n, self.names[int(c)])  # add to string

            bbox_xywh = xyxy2xywh(det[:, :4]).cpu()
            confs = det[:, 4:5].cpu()

            # ****************************** deepsort ****************************
            outputs = self.deepsort.update(bbox_xywh, confs, im0)
            # (#ID, 5) x1,y1,x2,y2,track_ID
        else:
            outputs = torch.zeros((0, 5))

        t3 = time.time()
        return outputs, t2-t1, t3-t2


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    # input and output
    # file/folder
    parser.add_argument('--input_path', type=str, default='./video_005.mp4', help='input folder path')
    parser.add_argument('--save_path', type=str, default='output/', help='output folder path')
    parser.add_argument("--frame_interval", type=int, default=2)
    parser.add_argument('--fourcc', type=str, default='mp4v', help='output video codec (verify ffmpeg support)')
    parser.add_argument('--device', default='', help='cuda device, i.e. 0 or 0,1,2,3 or cpu')
    parser.add_argument('--save_txt', default='output/predict/', help='cuda device, i.e. 0 or 0,1,2,3 or cpu')

    # live display settings
    parser.add_argument("--display", action="store_true")
    parser.add_argument("--display_width", type=int, default=800)
    parser.add_argument("--display_height", type=int, default=600)

    # YOLO-V5 parameters
    parser.add_argument('--weights', type=str, default='yolov5/weights/withoutfreeze.pt', help='model.pt path')
    parser.add_argument('--img-size', type=int, default=640, help='inference size (pixels)')
    parser.add_argument('--conf-thres', type=float, default=0.2, help='object confidence threshold')
    parser.add_argument('--iou-thres', type=float, default=0.5, help='IOU threshold for NMS')
    parser.add_argument('--classes', nargs='+', type=int, default=[0], help='filter by class')
    parser.add_argument('--agnostic-nms', action='store_true', help='class-agnostic NMS')
    parser.add_argument('--augment', action='store_true', help='augmented inference')

    # deepsort parameters
    parser.add_argument("--config_deepsort", type=str, default="configs/deep_sort.yaml")

    args = parser.parse_args()
    args.img_size = check_img_size(args.img_size)
    print(args)

    with VideoTracker(args) as vdo_trk:
        vdo_trk.run()
