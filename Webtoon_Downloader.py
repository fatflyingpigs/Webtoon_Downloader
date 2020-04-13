import argparse
import os
import shutil
import sys
from multiprocessing import Process, freeze_support, Array, Queue, Value

import module.cookie as Cookie
import module.shared as shared
from module.image import getImgNo, saveImg
from module.log import log
from module.merge import mergeImage, mergeImagePdf
from module.webtooninfo import getWebtoonName


def downPartialEpisode(op, webtoonId, start, finish, saveDir, divNo, modular, cnt, qu, savedEpisode, cookie):
    for viewNo in range(start, finish + 1):
        imgNo = getImgNo(op, webtoonId, viewNo, cookie)
        for i in range(modular, imgNo, divNo):
            imgName = os.path.join(saveDir,
                                   getWebtoonName(op, webtoonId, cookie) + "_" + str(viewNo) + "_" + str(i) + ".png")
            saveImg(op, webtoonId, viewNo, i, imgName, cookie)
        cnt[viewNo] -= 1
        if cnt[viewNo] == 0:
            qu.put(viewNo)
            log("d " + str(viewNo), 5)
    savedEpisode.value -= 1


def pathChk(saveDir):
    if os.path.isdir(os.path.join(saveDir, 'tmp')):
        shutil.rmtree(os.path.join(saveDir, 'tmp'))
    os.makedirs(os.path.join(saveDir, 'tmp'))


def downWebtoon(op, webtoonId, start, finish, saveDir, mergeOption, multiThreadCount=8, multiThreadMergingCount=8,
                cookie=None):
    if op == 'naver' or op == 'nbest' or op == 'nchall':
        webtoonId = int(webtoonId)
    thrs = list()
    cnt = Array('i', [multiThreadCount] * (finish + 1))
    runningThreadNo = Value('i', 0)
    qu = Queue()
    leftEpisode = finish - start + 1
    savedEpisode = Value('i', finish - start + 1)
    for i in range(0, multiThreadCount):
        if mergeOption:
            thr = Process(target=downPartialEpisode, args=(
                op, webtoonId, start, finish, os.path.join(saveDir, 'tmp'), multiThreadCount, i, cnt, qu, savedEpisode,
                cookie))
        else:
            thr = Process(target=downPartialEpisode, args=(
                op, webtoonId, start, finish, saveDir, multiThreadCount, i, cnt, qu, savedEpisode, cookie))
        thrs.append(thr)
        thr.start()
    if mergeOption:
        while leftEpisode > 0:
            if savedEpisode.value == 0:
                multiThreadMergingCount += multiThreadCount / 2
                multiThreadCount = 0
            if not qu.empty() and runningThreadNo.value < multiThreadMergingCount:
                targetEpisode = qu.get()
                if targetEpisode not in shared.imgNo:
                    getImgNo(op, webtoonId, targetEpisode, cookie)
                if shared.imgNo[targetEpisode] == 0:
                    log("m " + str(targetEpisode), 3)
                    leftEpisode -= 1
                    continue
                runningThreadNo.value += 1
                if mergeOption == 1:
                    thr = Process(target=mergeImage, args=(
                        op, webtoonId, targetEpisode, shared.imgNo[targetEpisode], saveDir, runningThreadNo, cookie))
                else:
                    thr = Process(target=mergeImagePdf, args=(
                        op, webtoonId, targetEpisode, shared.imgNo[targetEpisode], saveDir, runningThreadNo, cookie))
                thr.start()
                thrs.append(thr)
                leftEpisode -= 1
    for i in thrs:
        i.join()


if __name__ == '__main__':
    freeze_support()
    parser = argparse.ArgumentParser(description='Webtoon Downloader 3.0.0 by Seohyun Lee.')
    parser.add_argument('Type', type=str,
                        help='Webtoon provider. One of naver, nbest, nchall, daum, and kakao.',
                        choices=['naver', 'nbest', 'nchall', 'daum', 'kakao'])
    parser.add_argument('ID', type=str, help='Webtoon ID.')
    parser.add_argument("-s", "--start", type=int, required=True, help='Episode Number to Start download.')
    parser.add_argument("-f", "--finish", type=int, required=True, help='Episode Number to Finish download.')
    parser.add_argument("--downThreadNo", type=int, default=4, help='Thread Number to download Webtoon.')
    parser.add_argument("--mergeThreadNo", type=int, default=4, help='Thread Number to merge Webtoon.')
    merge = parser.add_mutually_exclusive_group()
    merge.add_argument("--mergeAsPng", help='Thread Number to merge Webtoon.', action='store_true')
    merge.add_argument("--mergeAsPdf", help='Thread Number to merge Webtoon.', action='store_true')
    parser.add_argument('Path', type=str, help='Path to save Webtoon.')
    parser.add_argument('cookie', type=str, nargs='*',
                        help='Cookie value to authorize while downloading Webtoon. Find document to get info.')
    args = parser.parse_args()
    pathChk(sys.argv[5])
    cookie = None
    if len(sys.argv) - 1 > 8:
        if sys.argv[1] == 'naver':
            cookie = Cookie.NCookie(sys.argv[9], sys.argv[10])
        if sys.argv[1] == 'daum':
            cookie = Cookie.DCookie(sys.argv[9], sys.argv[10], sys.argv[11], sys.argv[12], sys.argv[13])
        if sys.argv[1] == 'kakao':
            cookie = Cookie.KCookie(sys.argv[9], sys.argv[10], sys.argv[11], sys.argv[12], sys.argv[13])
    downWebtoon(sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5], int(sys.argv[6]),
                int(sys.argv[7]), int(sys.argv[8]), cookie)
    try:
        shutil.rmtree(os.path.join(sys.argv[5], 'tmp'))
    except:
        pass
