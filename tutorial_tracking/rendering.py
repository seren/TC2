###########RENDERING PART (OpenGL) ################
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import sys
import string
from Image import *
from liblo import *
import numpy
ESCAPE = '\033'


# Id of the glut window.
window = 0

#initial eye position in the world referential
eyepos = [0.0, 0.0, 0.0]
lefteyepos = [-2.5, 0.0, 0.0]
righteyepos = [+2.5, 0.0, 0.0]

##############################Step 2 ##########################################
#actual size of screen: unit is cm, adapt it to your case 
scr_height = 18
scr_width = 29

#widows size : unit is pixel be carreful whether fullscreen or windows mode 
window_width = 1280
window_height = 800

#define screen points in the world/room referential, adapt to your case
screenleftdownpos = [-scr_width/2,-scr_height/2,-60]
screenrightdownpos = [scr_width/2,-scr_height/2,-60]
screenleftuppos = [-scr_width/2,scr_height/2,-60]
###############################################################################


#general scale for the cube
object_scale = 6.0

#initial position of the cube. Normaly the frontal face of the cube is set on the screen plane 
objpos = [0.0, 0.0, -60.0-object_scale]

pause = True


##############################Step 10 ##########################################
stereo = False #True for stereo False for Monoscopic
################################################################################

near = 0.1
far = 100.0

class MyOSCServer(ServerThread):
		def __init__(self):
				ServerThread.__init__(self, 7000)

		@make_method('/tracker/head/pos_xyz/cyclope_eye', 'fff')
		def eyetracking_callback(self, path, args):
			global eyepos
			print "received message '%s' with arguments '%f %f %f'" % (path, args[0],args[1],args[2])
			eyepos[0]=args[0]
			eyepos[1]=args[1]	
			eyepos[2]=args[2]
				
		@make_method('/tracker/head/pos_xyz/left_eye', 'fff')
		def lefteyetracking_callback(self, path, args):
			global lefteyepos
			print "received message '%s' with arguments '%f %f %f'" % (path, args[0],args[1],args[2])
			lefteyepos[0]=args[0]
			lefteyepos[1]=args[1]	
			lefteyepos[2]=args[2]	
		@make_method('/tracker/head/pos_xyz/right_eye', 'fff')
		def righteyetracking_callback(self, path, args):
			global righteyepos
			print "received message '%s' with arguments '%f %f %f'" % (path, args[0],args[1],args[2])
			righteyepos[0]=args[0]
			righteyepos[1]=args[1]	
			righteyepos[2]=args[2]	
		@make_method(None, None)
                def fallback(self, path, args):
                        print "received unknown message '%s'" % path

try:
	server =  MyOSCServer()
	server.start()
except ServerError, err:
	print str(err)
	sys.exit()



texture = 0
# Rotations for cube. 
xrot = yrot = zrot = 0.0

def LoadTextures():
	#global texture
	image = open("NeHe.bmp")
	
	ix = image.size[0]
	iy = image.size[1]
	image = image.tostring("raw", "RGBX", 0, -1)
	
	# Create Texture	
	# There does not seem to be support for this call or the version of PyOGL I have is broken.
	#glGenTextures(1, texture)
	#glBindTexture(GL_TEXTURE_2D, texture)   # 2d texture (x and y size)
	
	glPixelStorei(GL_UNPACK_ALIGNMENT,1)
	glTexImage2D(GL_TEXTURE_2D, 0, 3, ix, iy, 0, GL_RGBA, GL_UNSIGNED_BYTE, image)
	glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP)
	glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP)
	glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
	glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
	glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
	glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
	glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_DECAL)


# A general OpenGL initialization function.  Sets all of the initial parameters. 
def InitGL(Width, Height):				# We call this right after our OpenGL window is created.
        global stereo
	LoadTextures()
	glEnable(GL_TEXTURE_2D)
	glClearColor(0.0, 0.0, 0.0, 0.0)	# This Will Clear The Background Color To Black
	glClearDepth(1.0)					# Enables Clearing Of The Depth Buffer
	glDepthFunc(GL_LESS)				# The Type Of Depth Test To Do
	glEnable(GL_DEPTH_TEST)				# Enables Depth Testing
	glShadeModel(GL_SMOOTH)				# Enables Smooth Color Shading
	glEnable (GL_LINE_SMOOTH)
	glEnable(GL_BLEND)					# Enables Blending	
	glBlendFunc (GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
   	glHint (GL_LINE_SMOOTH_HINT, GL_NICEST)
	glViewport(0, 0, Width, Height)		# Reset The Current Viewport And Perspective Transformation	
	glMatrixMode(GL_MODELVIEW)
	glLoadIdentity()	

# The function called when our window is resized (which shouldn't happen if you enable fullscreen, below)
def ReSizeGLScene(Width, Height):
    if Height == 0:						# Prevent A Divide By Zero If The Window Is Too Small 
	    Height = 1

    glViewport(0, 0, Width, Height)		# Reset The Current Viewport And Perspective Transformation


#compute adaptative projection matrix according to the tracked eye position, and the constant screen corner positions
# This code suppose that a world referential with Y up, X pointing to the rigth according to you in front of the screen, and Z pointing behind you 
def calcProjection(eye):
	global near, far, screenleftdownpos, screenrightdownpos,screenleftuppos
	pa=numpy.array(screenleftdownpos)
	pb=numpy.array(screenrightdownpos)
	pc=numpy.array(screenleftuppos)
	pe=numpy.array(eye)
	
	vr = numpy.subtract(pb,pa)
	
	vu=numpy.subtract(pc, pa)
	
	
	normvr = numpy.sqrt(numpy.dot(vr,vr))
	vr = numpy.dot(vr,1/normvr)
	
	normvu = numpy.sqrt(numpy.dot(vu,vu))
	vu = numpy.dot(vu, 1/normvu)
	
	vn = numpy.cross(vr,vu)
	normvn=numpy.sqrt(numpy.dot(vn,vn))
	vn=numpy.dot(vn, 1/normvn)
	
	va=numpy.subtract(pa,pe)
	
	vb=numpy.subtract(pb,pe)
	
	vc=numpy.subtract(pc,pe)
	
	d=-numpy.dot(va,vn)
	
	# here the frustum matrix is computed
	l = numpy.dot(vr,va) * near / d
	r = numpy.dot(vr,vb) * near / d
	b = numpy.dot(vu,va) * near / d
	t = numpy.dot(vu,vc) * near / d 
	
	#   compute M
	M=[[vr[0],vu[0],vn[0], 0.0], 
	[vr[1],vu[1],vn[1], 0.0],
	[vr[2],vu[2],vn[2], 0.0],
	[0.0,0.0,0.0,1.0]]

	# stack in projection matrix
	glMatrixMode(GL_PROJECTION) 
	glLoadIdentity()
	
        # call glFrustum
	glFrustum(l,r,b,t,near,far)
	glMultMatrixf(M)
	
	# Translate the apex of the frustum to the user position
	glTranslatef(-pe[0], -pe[1], -pe[2])

# The cube drawing fonction.
def DrawGLCube():
        # Note there does not seem to be support for this call.
	#glBindTexture(GL_TEXTURE_2D,texture)	# Rotate The Pyramid On It's Y Axis

	glBegin(GL_QUADS)			    # Start Drawing The Cube
	
	# Front Face (note that the texture's corners have to match the quad's corners)
	glTexCoord2f(0.0, 0.0); glVertex3f(-1.0, -1.0,  1.0)	# Bottom Left Of The Texture and Quad
	glTexCoord2f(1.0, 0.0); glVertex3f( 1.0, -1.0,  1.0)	# Bottom Right Of The Texture and Quad
	glTexCoord2f(1.0, 1.0); glVertex3f( 1.0,  1.0,  1.0)	# Top Right Of The Texture and Quad
	glTexCoord2f(0.0, 1.0); glVertex3f(-1.0,  1.0,  1.0)	# Top Left Of The Texture and Quad
	
	# Back Face
	glTexCoord2f(1.0, 0.0); glVertex3f(-1.0, -1.0, -1.0)	# Bottom Right Of The Texture and Quad
	glTexCoord2f(1.0, 1.0); glVertex3f(-1.0,  1.0, -1.0)	# Top Right Of The Texture and Quad
	glTexCoord2f(0.0, 1.0); glVertex3f( 1.0,  1.0, -1.0)	# Top Left Of The Texture and Quad
	glTexCoord2f(0.0, 0.0); glVertex3f( 1.0, -1.0, -1.0)	# Bottom Left Of The Texture and Quad
	
	# Top Face
	glTexCoord2f(0.0, 1.0); glVertex3f(-1.0,  1.0, -1.0)	# Top Left Of The Texture and Quad
	glTexCoord2f(0.0, 0.0); glVertex3f(-1.0,  1.0,  1.0)	# Bottom Left Of The Texture and Quad
	glTexCoord2f(1.0, 0.0); glVertex3f( 1.0,  1.0,  1.0)	# Bottom Right Of The Texture and Quad
	glTexCoord2f(1.0, 1.0); glVertex3f( 1.0,  1.0, -1.0)	# Top Right Of The Texture and Quad
	
	# Bottom Face       
	glTexCoord2f(1.0, 1.0); glVertex3f(-1.0, -1.0, -1.0)	# Top Right Of The Texture and Quad
	glTexCoord2f(0.0, 1.0); glVertex3f( 1.0, -1.0, -1.0)	# Top Left Of The Texture and Quad
	glTexCoord2f(0.0, 0.0); glVertex3f( 1.0, -1.0,  1.0)	# Bottom Left Of The Texture and Quad
	glTexCoord2f(1.0, 0.0); glVertex3f(-1.0, -1.0,  1.0)	# Bottom Right Of The Texture and Quad
	
	# Right face
	glTexCoord2f(1.0, 0.0); glVertex3f( 1.0, -1.0, -1.0)	# Bottom Right Of The Texture and Quad
	glTexCoord2f(1.0, 1.0); glVertex3f( 1.0,  1.0, -1.0)	# Top Right Of The Texture and Quad
	glTexCoord2f(0.0, 1.0); glVertex3f( 1.0,  1.0,  1.0)	# Top Left Of The Texture and Quad
	glTexCoord2f(0.0, 0.0); glVertex3f( 1.0, -1.0,  1.0)	# Bottom Left Of The Texture and Quad
	
	# Left Face
	glTexCoord2f(0.0, 0.0); glVertex3f(-1.0, -1.0, -1.0)	# Bottom Left Of The Texture and Quad
	glTexCoord2f(1.0, 0.0); glVertex3f(-1.0, -1.0,  1.0)	# Bottom Right Of The Texture and Quad
	glTexCoord2f(1.0, 1.0); glVertex3f(-1.0,  1.0,  1.0)	# Top Right Of The Texture and Quad
	glTexCoord2f(0.0, 1.0); glVertex3f(-1.0,  1.0, -1.0)	# Top Left Of The Texture and Quad
	
	glEnd();
# The main drawing function.
def DrawGLScene():
	global xrot, yrot, zrot, texture, screenpoints, eyepos,lefteyepos,righeyepos, pause, objpos,screenleftdownpos, screenrightdownpos,screenleftuppos, stereo
	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)	# Clear The Screen And The Depth Buffer
	glMatrixMode(GL_MODELVIEW)
	glLoadIdentity()					# Reset The View
	glTranslatef(objpos[0],objpos[1],objpos[2])			# Move Into The Screen
	glScalef(object_scale,object_scale,object_scale)
	

	glRotatef(xrot,1.0,0.0,0.0)			# Rotate The Cube On It's X Axis
	glRotatef(yrot,0.0,1.0,0.0)			# Rotate The Cube On It's Y Axis
	glRotatef(zrot,0.0,0.0,1.0)			# Rotate The Cube On It's Z Axis

        if(stereo) :
                calcProjection(lefteyepos)
                #left eye stereo buffer
                glDrawBuffer(GL_BACK_LEFT);
                glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        	DrawGLCube()

                calcProjection(righteyepos)
                #right eye stereo buffer
                glDrawBuffer(GL_BACK_RIGHT);
                glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        	DrawGLCube()
        else :
                calcProjection(eyepos)
                glDrawBuffer(GL_BACK);
                glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
                DrawGLCube()
	
	# Done Drawing The Cube
	if (not pause) :
		xrot  =xrot + 0.02                # X rotation
		yrot = yrot + 0.02                 # Y rotation
		zrot = zrot + 0.02                 # Z rotation

	#  since this is double buffered, swap the buffers to display what just got drawn. 
	glutSwapBuffers()


def UpdateGLScene():
	#nothing for now
	return 0
	
# The function called whenever a key is pressed. Note the use of Python tuples to pass in: (key, x, y)  
def keyPressed(*args):
	global objpos, pause, server
	# If escape is pressed, kill everything.
	if args[0] == ESCAPE:
        	server.stop()
        	sys.exit()
        if args[0] == 'x':
                objpos[0]=objpos[0]+0.5
        if args[0] == 'X':
                objpos[0]=objpos[0]-0.5
        if args[0] == 'y':
                objpos[1]=objpos[1]+0.5
        if args[0] == 'Y':
                objpos[1]=objpos[1]-0.5				
        if args[0] == 'z':
                objpos[2]=objpos[2]+0.5
        if args[0] == 'Z':
                objpos[2]=objpos[2]-0.5
        if args[0] == 'p':
                pause=not pause
        print "objpos", objpos
	

########## main routine

def main():
	global server, window, scr_height, scr_width,window_height, window_width
	
	# create server, listening on port 1234
	
	glutInit(sys.argv)

	# Select type of Display mode:  
	#  Double buffer 
	#  RGBA color
	# Alpha components supported 
	# Depth buffer
        glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_ALPHA | GLUT_DEPTH | GLUT_STEREO)
	# Normally the window has the size of the screen...
	# for convenience we select a smaller size
	# caution: aspect ratio MUST be the same has the real one (scr_width / scr_height)


	glutInitWindowSize(window_width, window_height)
	
	# the window starts at the upper left corner of the screen 
	glutInitWindowPosition(0, 0)
	
	# Okay, like the C version we retain the window id to use when closing, but for those of you new
	# to Python (like myself), remember this assignment would make the variable local and not global
	# if it weren't for the global declaration at the start of main.
	window = glutCreateWindow("Rendering Windows")

   	# Register the drawing function with glut, BUT in Python land, at least using PyOpenGL, we need to
	# set the function pointer and invoke a function to actually register the callback, otherwise it
	# would be very much like the C version of the code.	
	glutDisplayFunc(DrawGLScene)
	
	# Uncomment this line to get full screen.
	#glutFullScreen()


	# When we are doing nothing, update scene
	glutIdleFunc(DrawGLScene)
	
	# Register the function called when our window is resized.
	glutReshapeFunc(ReSizeGLScene)
	
	# Register the function called when the keyboard is pressed.  
	glutKeyboardFunc(keyPressed)

	# Initialize our window. 
	InitGL(window_width, window_height)

	# Start Event Processing Engine	
	glutMainLoop()

# Print message to console, and kick off the main to get it rolling.

main()
    	
