import os
import subprocess

idx = [5]
if __name__ == '__main__':
    os.chdir('..')
    print(os. getcwd())

    for i in range(10):
        print('file {} is being processed'.format(i))
        os.system('python3 main.py --input_path ./vids/video_00{}.mp4 --display >> log{}.txt'.format(i,i))
    for i in range(10,27):
        print('file {} is being processed'.format(i))
        os.system('python3 main.py --input_path ./vids/video_0{}.mp4 --display >> log{}.txt'.format(i,i))
    
    print('all files are processed .. chill'.format(i))
        