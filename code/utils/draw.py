import numpy as np
import cv2
import math
palette = (2 ** 11 - 1, 2 ** 15 - 1, 2 ** 20 - 1)

def static_vars(**kwargs):
    def decorate(func):
        for k in kwargs:
            setattr(func, k, kwargs[k])
        return func
    return decorate

def compute_color_for_labels(label):
    """
    Simple function that adds fixed color depending on the class
    """
    color = [int((p * (label ** 2 - label + 1)) % 255) for p in palette]
    return tuple(color)

def draw_boxes(img, bbox, identities=None, offset=(0, 0), tracks=[[]]):
    for i, box in enumerate(bbox):
        x1, y1, x2, y2 = [int(i) for i in box]
        x1 += offset[0]
        x2 += offset[0]
        y1 += offset[1]
        y2 += offset[1]

        def dist_(pi, pj):
            return math.sqrt((pi[0]-pj[1])**2+(pi[0]-pj[1])**2)

        #print(self.img_tracks)
        if True:
            for i_ in range(1,len(tracks)):
                for j_ in range(i_,len(tracks)):
                    if i_==j_ or len(tracks[j_]) < 1:
                        continue
                    trk_i = tracks[i_]
                    trk_j = tracks[j_] 
                    #print(tracks)
                    if dist_(trk_i[-1], trk_j[0]) < 30:
                        tracks[i_].extend(tracks[j_])
                        del tracks[j_]# = []
                        #print(j_,"->",i_)

        for track_id in range(len(tracks)):
                cur_track = tracks[track_id] 
                if len(cur_track) < 2:
                        continue
                for coord_id in range(len(cur_track)):
                    if coord_id == 0:
                        continue
                    cv2.line(img, cur_track[coord_id-1], cur_track[coord_id], (255,155,55), thickness=2) 
                
        # box text and bar
        id = int(identities[i]) if identities is not None else 0    
        color = (255,155,55)#compute_color_for_labels(id)
        label = '{}{:d}'.format("", id)
        # add new new track id
        if id >= len(tracks):
            tracks.append([((x2+x1)//2,(y2+y1)//2)])
        else:
            tracks[id].append(((x2+x1)//2,(y2+y1)//2))            
        # t_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_PLAIN, 2 , 2)[0]
        cv2.rectangle(img, (x1, y1), (x2,y2), color, 2)
        # cv2.rectangle(img, (x1, y1), (x1 + abs(x1 - x2), y1 - abs(x1 - x2)), color, -1)
        cv2.putText(
            img=img,
            text=label,
            org=(x1, y1),
            fontFace=cv2.FONT_HERSHEY_PLAIN,
            fontScale=1.2,
            color=[255,255,255],
            thickness=2
            )
    return img, tracks

if __name__ == '__main__':
    for i in range(82):
        print(compute_color_for_labels(i))
