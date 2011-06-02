from simworldbase import *

worldModel = 'world'
actorModel = 'ball'

# controlling the actor is done in setActorOIAction() by setting the movement flags
# movement is then updated in actorOIControlTask(), which just takes the input and moves the actor
# actorOIStateUpdateFunc() is called at every frame, and that's where I probably want to grab state variables, and maybe move the actor?
# moveActor(move, turn)

class MouseWorld(SimWorldBase):
	"""docstring for MouseWorld"""
	def __init__(self, width, height, isFullscreen, title):

		SimWorldBase.__init__(self, width, height, isFullscreen, title)
		
		self.setupScene(worldModel)
		self.addActor(actorModel, position=(0,0,10), collisionSphere=(0,0,0,0))
		self.addLight('ambient', 'l', 'ambient')
		self.actorOIMoveSpeed = 70
		self.actorOITurnSpeed = 100
		self.addCamera('camera', 'c', self.actorOINP, self.cam.node().getLens(), (0,0,0))
		self.cameraNP['camera'].lookAt(self.actorOINP)
		self.activateCamera('camera')
		self.activateActorOIControl(True)
		
		self.setTracing('myTraceFile')
		
	def myPositionUpdateFunction(self):
		velocity_vector = np.r_[1,1] # calculated from some input on the device
		return velocity_vector
		
	def traceUpdateFunc():
		print "My actor is at [%f,%f] and is moving at %f speed, and collision angle is %f " % ( self.actorPosition[0], self.actorPosition[0], self.actorSpeed[0], self.collisionAngle[0] )
		
if __name__ == "__main__":
	app = MouseWorld(width=1680, height=1050, isFullscreen=True, title='MouseWorld')
	app.run()