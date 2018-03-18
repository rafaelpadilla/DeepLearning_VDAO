import os
import fnmatch
import cv2
import itertools

# Ex: 
# in: '/home/rafael/thesis/simulations/data1/test_data/000001.jpg'
# out: '/home/rafael/thesis/simulations/data1/test_data/', '000001.jpg'
def splitPathFile(fileDataPath):
    idx = fileDataPath.rfind('/')
    p = fileDataPath[:idx+1] #path
    f = fileDataPath[idx+1:] #file
    return p,f

# Ex: 
# in: '/home/rafael/thesis/simulations/data1/test_data/'
# out: '{ 'home', 'rafael', 'thesis', 'simulations', 'data1', 'test_data' }
def splitPaths(path):
    folders = []
    indexes = [i for i, letter in enumerate(path) if letter == '/']
    for i in range(len(indexes)):
        if i+1 < len(indexes):
            item = path[indexes[i]:indexes[i+1]]
        else:
            item = path[indexes[i]:]
        item = item.replace('/','')
        if item != '':
            folders.append(item)
    return folders


def getAllFilesRecursively(filePath, extension="*"):
    files = [os.path.join(dirpath, f)
        for dirpath, dirnames, files in os.walk(filePath)
        for f in fnmatch.filter(files, '*.'+extension)]
    return files

# boxA = (Ax1,Ay1,Ax2,Ay2)
# boxB = (Bx1,By1,Bx2,By2)
def boxesIntersect(boxA, boxB):
    if boxA[0] > boxB[2]: 
        return False # boxA is right of boxB
    if boxB[0] > boxA[2]:
        return False # boxA is left of boxB
    if boxA[3] < boxB[1]:
        return False # boxA is above boxB
    if boxA[1] > boxB[3]:
        return False # boxA is below boxB
    return True

# box = (Ax1,Ay1,Ax2,Ay2)
def getArea(box):
    return (box[2] - box[0]) * (box[3] - box[1])

def getNonOverlappedBoxes(boxes):
    if len(boxes) == 1 or boxes == []:
        return boxes, [0]

    nonOverlappedBoxes = []
    idxes = []
    # Get combination among all boxes
    combinations = list(itertools.combinations(boxes,2))
    # Loop through the pairs
    for combination in combinations:
        # If boxes do not intersect
        if boxesIntersect(combination[0], combination[1]) == False:
            if combination[0] not in nonOverlappedBoxes:
                nonOverlappedBoxes.append(combination[0])
                idxes.append(boxes.index(combination[0]))
            if combination[1] not in nonOverlappedBoxes:
                nonOverlappedBoxes.append(combination[1])
                idxes.append(boxes.index(combination[1]))
    return nonOverlappedBoxes, idxes
    

def add_bb_into_image(image, boundingBox, color, thickness, label=None):
    r = int(color[0])
    g = int(color[1])
    b = int(color[2])

    font = cv2.FONT_HERSHEY_SIMPLEX
    fontScale = 0.5
    fontThickness = 1
    safetyPixels = 0

    xIn = boundingBox[0]
    yIn = boundingBox[1]
    cv2.rectangle(image,(boundingBox[0], boundingBox[1]),(boundingBox[2], boundingBox[3]),(b,g,r), thickness)
    # Add label
    if label != None:
        # Get size of the text box
        (tw, th) = cv2.getTextSize(label, font, fontScale, fontThickness)[0]
        # Top-left coord of the textbox
        (xin_bb, yin_bb) = (xIn+thickness, yIn-th+int(12.5*fontScale))
        # Checking position of the text top-left (outside or inside the bb)
        if yin_bb - th <= 0: # if outside the image
            yin_bb = yIn+th # put it inside the bb
        r_Xin = xIn-int(thickness/2) 
        r_Yin = yin_bb-th-int(thickness/2) 
        # Draw filled rectangle to put the text in it
        cv2.rectangle(image,(r_Xin,r_Yin-thickness), (r_Xin+tw+thickness*3,r_Yin+th+int(12.5*fontScale)), (b,g,r), -1)
        cv2.putText(image,label, (xin_bb, yin_bb), font, fontScale, (0,0,0), fontThickness, cv2.LINE_AA)
    return image

