############This python script implements a simple example of adaptive viewing 
############based on marker tracking ###############################

# date: Nov 2011
# authors: Nicolas Ferey & JM Vezien
# Copyright LIMSI-CNRS groupe VENISE

#usage:

#python adaptive.py model_3d.txt
# the argument is the name of a file containing a list of 3D points of a model
# see glasses.txt for an example

# import necessary modules

import cv2.cv as cv
import time
from math import *
import sys
import numpy
import liblo

# capture frame from available camera
capture = cv.CaptureFromCAM(0)

# get image size
testframe = cv.QueryFrame(capture)
size_image = cv.GetSize(testframe)
print "image is size %d x %d" %size_image

# images for base processing

# RGB format
rgb_image = cv.CreateImage(size_image, 8, 3)

# HSV image (better for color processing)
hsv_image = cv.CreateImage(size_image, cv.IPL_DEPTH_8U, 3)

# mask images: will contain pixels identified by color (see color plate included)
yellowmask_image = cv.CreateImage(size_image, cv.IPL_DEPTH_8U, 1)
greenmask_image = cv.CreateImage(size_image, cv.IPL_DEPTH_8U, 1)
redmask_image = cv.CreateImage(size_image, cv.IPL_DEPTH_8U, 1)
bluemask_image = cv.CreateImage(size_image, cv.IPL_DEPTH_8U, 1)

# pixels are gathered in "blobs" in theses images
greenblob_image = cv.CreateImage(size_image, cv.IPL_DEPTH_8U, 1)
yellowblob_image = cv.CreateImage(size_image, cv.IPL_DEPTH_8U, 1)
redblob_image = cv.CreateImage(size_image, cv.IPL_DEPTH_8U, 1)
blueblob_image = cv.CreateImage(size_image, cv.IPL_DEPTH_8U, 1)

#you can tune HSV range for color blob tracking
hsvyellowmin=[21,90,180]
hsvyellowmax=[40,160,255]

hsvgreenmin=[70,135,70]
hsvgreenmax=[90,190,190]

hsvredmin=[130,180,150]
hsvredmax=[180,240,240]

hsvbluemin=[105,150,170]
hsvbluemax=[125,200,255]

hsvyellowtab=[]
hsvgreentab=[]
hsvredtab=[]
hsvbluetab=[]

# a color will be defined with this tolerance
hsvrange = [10,40,50]

hsvmouse = [0,0,0]

step = 0
pausecam = False

#read 3d model input file
print "I read file %s" %sys.argv[1] 
f = open(sys.argv[1], 'r')
nb_pts = int(f.readline())
modelepoints=[]

print "I read  %d points" %nb_pts

for i in range(nb_pts):
	this_pt = f.readline()
	tmplist = this_pt.split(' ')
	modelepoints.append((float(tmplist[0]),float(tmplist[1]),float(tmplist[2])))
	print modelepoints[i]
f.close()

print "I read file %s" %sys.argv[2] 
f = open(sys.argv[2], 'r')
eye_offsets={}
tmplist = f.readline().split(' ')
eye_offsets['right'] = (float(tmplist[0]),float(tmplist[1]),float(tmplist[2]))
tmplist = f.readline().split(' ')
eye_offsets['left'] = (float(tmplist[0]),float(tmplist[1]),float(tmplist[2]))
print "Eye offsets read:"
print eye_offsets
f.close()



blob_centers = []


###############################################################  Color Blob Tracking  Function ##############################################################

def findBlob(rgbimage,hsvimage, maskimage,blobimage, hsvcolorrange, hsvmin, hsvmax) : 
	
	cv.CvtColor(rgbimage, hsvimage, cv.CV_BGR2HSV)
	hsvmin = [hsvmin[0]-hsvcolorrange[0], hsvmin[1]-hsvcolorrange[1], hsvmin[2]-hsvcolorrange[2]]
	hsvmax = [hsvmax[0]+hsvcolorrange[0], hsvmax[1]+hsvcolorrange[1], hsvmax[2]+hsvcolorrange[2]]	
	if hsvmin[0] <0 :
		hsvmin[0] = 0
	if hsvmin[1] <0 :
		hsvmin[1] = 0
	if hsvmin[2] <0 :
		hsvmin[2] = 0

	if hsvmax[0] >255 :
		hsvmax[0]=255;
	if hsvmax[1] >255 :
		hsvmax[1]=255;
	if hsvmax[2] >255 :
		hsvmax[2]=255;
	
	cv.InRangeS(hsvimage, cv.Scalar(hsvmin[0], hsvmin[1],   hsvmin[2]), cv.Scalar(hsvmax[0],hsvmax[1],hsvmax[2]), maskimage)

	element = cv.CreateStructuringElementEx(5, 5, 2, 2, cv.CV_SHAPE_RECT)
	cv.Erode(maskimage, maskimage, element, 1)
	cv.Dilate(maskimage, maskimage, element, 1)
	storage = cv.CreateMemStorage(0)
	
	cv.Copy(maskimage,blobimage)
	contour = cv.FindContours(maskimage , storage, cv.CV_RETR_CCOMP, cv.CV_CHAIN_APPROX_SIMPLE)
	
	trackedpoint=None
	maxtrackedpoint=None	
	
	maxareasize=0
	
	#You can tune these value to improve tracking
	maxarea=0
	minarea=1
	
	areasize=0
	while contour:
		bound_rect = cv.BoundingRect(list(contour))
		contour = contour.h_next()
		pt1 = (bound_rect[0], bound_rect[1])
		pt2 = (bound_rect[0] + bound_rect[2], bound_rect[1] + bound_rect[3])
		areasize=fabs(bound_rect[2]*bound_rect[3])
		if(areasize>maxareasize) : 
			maxareasize=areasize
			maxtrackedpoint=(int((pt1[0]+pt2[0])/2),int((pt1[1]+pt2[1])/2), 1.0)
			cv.Rectangle(rgb_image, pt1, pt2, cv.CV_RGB(255,0,0), 1)
			
	trackedpoint=maxtrackedpoint	
	if(trackedpoint!=None) :
		cv.Circle(rgb_image, (trackedpoint[0], trackedpoint[1]), 5, cv.CV_RGB(255,0,0),1)
	return trackedpoint

# find minimum in hsv point tab
def mintab(hsvtab) : 
	if len(hsvtab)==1 : 
		minhsv=[hsvtab[0][0],hsvtab[0][1],hsvtab[0][2] ]
		return minhsv
		
	if len(hsvtab)>=1 : 
		minhsv=[hsvtab[0][0],hsvtab[0][1],hsvtab[0][2] ]
		for i in range (1,len(hsvtab)) : 
			if minhsv[0]>hsvtab[i][0] : 
				minhsv[0]=hsvtab[i][0]
			if minhsv[1]>hsvtab[i][1] : 
				minhsv[1]=hsvtab[i][1]
			if minhsv[2]>hsvtab[i][2] : 
				minhsv[2]=hsvtab[i][2]
		return minhsv	
	return None

# find minimum in hsv point tab
def maxtab(hsvtab) : 
	if len(hsvtab)==1 : 
		maxhsv=[hsvtab[0][0],hsvtab[0][1],hsvtab[0][2] ]		
		return maxhsv
		
	if len(hsvtab)>=1 : 
		maxhsv=[hsvtab[0][0],hsvtab[0][1],hsvtab[0][2] ]
		for i in range (1,len(hsvtab)) : 
			if maxhsv[0]<hsvtab[i][0] : 
				maxhsv[0]=hsvtab[i][0]
			if maxhsv[1]<hsvtab[i][1] : 
				maxhsv[1]=hsvtab[i][1]
			if maxhsv[2]<hsvtab[i][2] : 
				maxhsv[2]=hsvtab[i][2]
		return maxhsv	
	return None

# mouse picking HSV color in image

def getObjectHSV(event, x, y, flags, image):
# click routine on webcam input
	global hsvmouse
	if event==cv.CV_EVENT_LBUTTONDOWN :
		pixel = cv.Get2D(hsv_image, y, x)
		pixelrgb = cv.Get2D(rgb_image, y, x)
		hsvmouse = pixel
		print "Pixel color (HSV): "
		print hsvmouse     

########################### core routine: find 3d pose of model based on POSIT algorithm #################################################

def find_pose(nb_pts,points2d,points3d):
	focal_length = 1000 #scale factor: number of pixels per focal length
	
# create posit object
	positObject = cv.CreatePOSITObject(points3d)

	rotation_matrix=cv.CreateMat(3,3,cv.CV_64FC1)
	translation_vector=cv.CreateMat(3,1,cv.CV_64FC1)
	criteria = (cv.CV_TERMCRIT_EPS, 0, 0.01) 
	(rotation_matrix, translation_vector) = cv.POSIT( positObject, points2d, focal_length, criteria)
	pos_mat = ((rotation_matrix[0][0],rotation_matrix[0][1], rotation_matrix[0][2],0.0),
			(rotation_matrix[1][0],rotation_matrix[1][1], rotation_matrix[1][2],0.0),
			(rotation_matrix[2][0],rotation_matrix[2][1], rotation_matrix[2][2],0.0),
			(translation_vector[0],translation_vector[1],translation_vector[2],1.0))			
	return pos_mat


############################################################### Matrix Operation tools ####################################################
def MultMat4(src, mat33) : 
		return (
	mat33[0,0]*src[0]+mat33[0,1]*src[1]+mat33[0,2]*src[2], 
	mat33[1,0]*src[0]+mat33[1,1]*src[1]+mat33[1,2]*src[2],
	mat33[2,0]*src[0]+mat33[2,1]*src[1]+mat33[2,2]*src[2]
	)

def XAxisRotationMatrix(angle):
	return 
	((1.0,0.0,0.0,0.0),
	(0.0, cos(angle), sin(angle),0.0),
	(0.0, -sin(angle), cos(angle),0.0),
	(0.0,0.0,0.0,1.0))


def YAxisRotationMatrix(angle):
	return((cos(angle),0.0,-sin(angle),0.0),
	(0.0, 1.0, 0.0,0.0),
	(sin(angle), 0.0, cos(angle),0.0),
	(0.0,0.0,0.0,1.0))

def ZAxisRotationMatrix(angle):
	return((cos(angle), sin(angle),0.0,0.0),
	(-sin(angle), cos(angle), 0.0,0.0),
	(0.0, 0.0,1.0,0.0),
	(0.0,0.0,0.0,1.0))

def TranslationMatrix(x,y,z):
	return ((1.0,0.0,0.0,0.0),
	(0.0, 1.0, 0.0,0.0),
	(0.0, 0.0, 1.0,0.0),
	(x,y,z,1.0))

def ScaleMatrix(scale):
	return ((scale,0.0,0.0,0.0),
	(0.0, scale, 0.0,0.0),
	(0.0, 0.0, scale,0.0),
	(0.0,0.0,0.0,1.0))


def MultMatrix(matleft,matright):
	mat=[[0.0,0.0,0.0,0.0],
	[0.0, 0.0, 0.0,0.0],
	[0.0, 0.0, 0.0,0.0],
	[0.0,0.0,0.0,0.0]]
	
	for i in range(4) : 
		for j in range(4) :
			for k in range(4) :			 
				mat[i][j]+=matright[i][k]*matleft[k][j]
	return mat
	

############################################################### Referential transform ####################################################

#tracker to world/room referential
def WorldToTrackerTransform(trackingmatrix) :
        ##############################Step 5 ##########################################        
        rotated_trackingmatrix = MultMatrix(trackingmatrix, ZAxisRotationMatrix(180))
    	result = MultMatrix(rotated_trackingmatrix, TranslationMatrix(0,0,-100))
        return result
        ###############################################################################


        ##############################Step 7 ##########################################
#cyclop eye referential in body/glass referential 
def BodyToCyclopsEyeTransform() : 
        #...
        return result

#left eye referential in body/glass referential 
def BodyToLeftEyeTransform() : 
	#...
	return result

#right eye referential in body/glass referential 
def BodyToRightEyeTransform() : 
	#...
	return result

        ###############################################################################

############################################################### Tracking routine ####################################################
	
def runtracking():
	global rgb_image, hsv_image, hsvmouse, pausecam, hsvgreen, hsvyellow , hsvblue, hsvred, homographycomputed
	global hsvyellowtab, hsvrange
	global homography , pose_flag
	global hsvyellowmin, hsvyellowmax, hsvgreenmin, hsvgreenmax, hsvbluemin, hsvbluemax, hsvredmin, hsvredmax
	global cycloppoint, righteyepoint, lefteyepoint
	global capture, pausecam, size_image
	global yellowmask_image, greenmask_image, redmask_image, bluemask_image
	global nb_pts, modelepoints,blob_centers
	global rx,ry,rz

	size_thumb = [size_image[0]/2, size_image[1]/2]

	thumbgreen = cv.CreateImage(size_thumb, cv.IPL_DEPTH_8U, 1)
	thumbred = cv.CreateImage(size_thumb, cv.IPL_DEPTH_8U, 1)
	thumbblue = cv.CreateImage(size_thumb, cv.IPL_DEPTH_8U, 1)
	thumbyellow = cv.CreateImage(size_thumb, cv.IPL_DEPTH_8U, 1)

	cv.NamedWindow("GreenBlobDetection", cv.CV_WINDOW_AUTOSIZE)
	cv.ShowImage("GreenBlobDetection", thumbgreen)
	
	cv.NamedWindow("YellowBlobDetection", cv.CV_WINDOW_AUTOSIZE)
	cv.ShowImage("YellowBlobDetection", thumbyellow)
	
	cv.NamedWindow("BlueBlobDetection", cv.CV_WINDOW_AUTOSIZE)
	cv.ShowImage("BlueBlobDetection", thumbblue)
	
	cv.NamedWindow("RedBlobDetection", cv.CV_WINDOW_AUTOSIZE)
	cv.ShowImage("RedBlobDetection", thumbred)

	rgb_image = cv.QueryFrame(capture)	
	cv.NamedWindow("Source", cv.CV_WINDOW_AUTOSIZE)
	cv.ShowImage("Source", rgb_image)
	
	cv.SetMouseCallback("Source", getObjectHSV)

	print "Hit ESC key to quit..."
                
	try:
		target = liblo.Address("127.0.0.1", 7000)
	except liblo.AddressError, err:
		print str(err)
		sys.exit()


	#infinite loop for processing
	while True:
		
		time.sleep(0.02)
		blobcentergreen=findBlob(rgb_image,hsv_image, greenmask_image, greenblob_image, hsvrange, hsvgreenmin, hsvgreenmax)
		blobcenteryellow=findBlob(rgb_image,hsv_image, yellowmask_image, yellowblob_image, hsvrange, hsvyellowmin, hsvyellowmax)
		blobcenterblue=findBlob(rgb_image,hsv_image, bluemask_image, blueblob_image, hsvrange, hsvbluemin, hsvbluemax)
		blobcenterred=findBlob(rgb_image,hsv_image, redmask_image, redblob_image, hsvrange, hsvredmin, hsvredmax)

		if not pausecam :	
			if(blobcentergreen != None): 
				cv.Resize(greenblob_image, thumbgreen) 
				#cv.ShowImage("GreenBlobDetection", greenblob_image)
				cv.ShowImage("GreenBlobDetection", thumbgreen)
				#print "green center: %d %d %d" %blobcentergreen
			if(blobcenteryellow != None):            
				cv.Resize(yellowblob_image, thumbyellow) 
				cv.ShowImage("YellowBlobDetection", thumbyellow)
				#print "yellow center: %d %d %d" %blobcenteryellow
			if(blobcenterblue != None):            
				cv.Resize(blueblob_image, thumbblue) 
				cv.ShowImage("BlueBlobDetection", thumbblue)
				#print "blue center: %d %d %d" %blobcenterblue
			if(blobcenterred != None):            
				cv.Resize(redblob_image, thumbred) 
				cv.ShowImage("RedBlobDetection", thumbred)
				#print "red center: %d %d %d" %blobcenterred

			
		cv.ShowImage("Source", rgb_image)
		c = cv.WaitKey(7) % 0x100
		if c == 27:
                        break
		if c == ord('p') or c == ord('P') : 
                        pausecam = not pausecam  
                        
		if c == ord('y') : 
			hsvyellowtab.append(hsvmouse)
			hsvyellowmin=mintab(hsvyellowtab)
			hsvyellowmax=maxtab(hsvyellowtab)		
			print "minyellow" 
			print hsvyellowmin
			print "maxyellow" 
			print hsvyellowmax 		
		if c == ord('Y') : 
			if(len(hsvyellowtab)>0):
				hsvyellowtab.pop(len(hsvyellowtab)-1)
			if(len(hsvyellowtab)!=0):			
				hsvyellowmin=mintab(hsvyellowtab)
				hsvyellowmax=maxtab(hsvyellowtab)		
			else :
				hsvyellowmin=[255,255,255]
				hsvyellowmax=[0,0,0]
		if c == ord('g') : 
			hsvgreentab.append(hsvmouse)
			hsvgreenmin=mintab(hsvgreentab)
			hsvgreenmax=maxtab(hsvgreentab)		
			print "mingreen" 
			print hsvgreenmin
			print "maxgreen" 
			print hsvgreenmax 		
		if c == ord('G') : 
			if(len(hsvgreentab)>0):
				hsvgreentab.pop(len(hsvgreentab)-1)
			if(len(hsvgreentab)!=0):			
				hsvgreenmin=mintab(hsvgreentab)
				hsvgreenmax=maxtab(hsvgreentab)		
			else :
				hsvgreenmin=[255,255,255]
				hsvgreenmax=[0,0,0]
		if c == ord('r') : 
			hsvredtab.append(hsvmouse)
			hsvredmin=mintab(hsvredtab)
			hsvredmax=maxtab(hsvredtab)		
			print "minred" 
			print hsvredmin
			print "maxred" 
			print hsvredmax 		
		if c == ord('R') : 
			if(len(hsvredtab)>0):
				hsvredtab.pop(len(hsvredtab)-1)
			if(len(hsvredtab)!=0):			
				hsvredmin=mintab(hsvredtab)
				hsvredmax=maxtab(hsvredtab)		
			else :
				hsvredmin=[255,255,255]
				hsvredmax=[0,0,0]
		if c == ord('b') : 
			hsvbluetab.append(hsvmouse)
			hsvbluemin=mintab(hsvbluetab)
			hsvbluemax=maxtab(hsvbluetab)		
			print "minblue" 
			print hsvbluemin
			print "maxblue" 
			print hsvbluemax 		
		if c == ord('B') : 
			if(len(hsvbluetab)>0):
				hsvbluetab.pop(len(hsvbluetab)-1)
			if(len(hsvbluetab)!=0):			
				hsvbluemin=mintab(hsvbluetab)
				hsvbluemax=maxtab(hsvbluetab)		
			else :
				hsvbluemin=[255,255,255]
				hsvbluemax=[0,0,0]
		if c == ord('R') : 
                        step=0
		if not pausecam :
                        rgb_image = cv.QueryFrame(capture)
		#after blob center detection we need to launch pose estimation
		if ((blobcentergreen != None) and (blobcenteryellow != None) and (blobcenterblue != None) and (blobcenterred != None)):
			#order is Yellow,red, blue,green
			pose_flag = 1
			blob_centers=[]
			blob_centers.append((blobcenteryellow[0]-size_image[0]/2, blobcenteryellow[1]-size_image[1]/2))
			blob_centers.append((blobcenterblue[0]-size_image[0]/2, blobcenterblue[1]-size_image[1]/2))
			blob_centers.append((blobcenterred[0]-size_image[0]/2, blobcenterred[1]-size_image[1]/2))
			blob_centers.append((blobcentergreen[0]-size_image[0]/2, blobcentergreen[1]-size_image[1]/2))

			#get the tracking matrix (orientation and position) result with POSIT method in the tracker (camera) referential
			trackingmatrix=find_pose(nb_pts,blob_centers,modelepoints)
 			  			
			#put it in the world coordinate system
			trakerinroom=WorldToTrackerTransform(trackingmatrix)
			# express the coordinates of the eyes in the world coordinate system
            cyclopeinroom=BodyToCyclopsEyeTransform()
			rightinroom=BodyToRightEyeTransform()
			leftinroom=BodyToLeftEyeTransform()			
			
            ## extract translations and send

   			# poscyclope=[cyclopeinroom[3][0], cyclopeinroom[3][1], cyclopeinroom[3][2]]
			# print "poscylope",poscyclope

			# posleft=[leftinroom[3][0], leftinroom[3][1], leftinroom[3][2]]
			# print "posleft",posleft
			
			# posright=[rightinroom[3][0], rightinroom[3][1], rightinroom[3][2]]
			# print "posright",posright

			
			# liblo.send(target, "/tracker/head/pos_xyz/cyclope_eye",  poscyclope[0],poscyclope[1],poscyclope[2])
			# liblo.send(target, "/tracker/head/pos_xyz/left_eye",  posleft[0],posleft[1],posleft[2])
			# liblo.send(target, "/tracker/head/pos_xyz/right_eye",  posright[0],posright[1],posright[2])						
		else :
			print "Traking failed" 	
			
runtracking() 
