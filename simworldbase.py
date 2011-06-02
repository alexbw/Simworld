'''
Created on Feb 22, 2011

@author: murat
'''

#@PydevCodeAnalysisIgnore

import sys
import io
import os
import atexit
from textwrap import dedent

from direct.task import Task
from direct.actor.Actor import Actor
from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectGui import DirectDialog
from direct.showbase.ShowBase import ShowBase
from panda3d.core import AmbientLight
from panda3d.core import AntialiasAttrib
from panda3d.core import BillboardEffect
from panda3d.core import BitMask32
from panda3d.core import Camera
from panda3d.core import CollisionNode
from panda3d.core import CollisionSphere
from panda3d.core import CollisionTraverser
from panda3d.core import CollisionHandlerEvent
from panda3d.core import CollisionHandlerPusher
from panda3d.core import ConfigVariableBool
from panda3d.core import ConfigVariableInt
from panda3d.core import ConfigVariableString
from panda3d.core import DirectionalLight
from panda3d.core import PointLight
from panda3d.core import Fog
from panda3d.core import NodePath
from panda3d.core import TextNode
from panda3d.core import WindowProperties
from panda3d.core import Point3
from panda3d.core import Vec3D
from panda3d.core import Filename
from panda3d.physics import ActorNode
from panda3d.physics import PhysicsCollisionHandler
from panda3d.ai import *            


class SimWorldBase(ShowBase):
 
    def __init__(self, width, height, isFullscreen, title):
        
        ShowBase.__init__(self)

        #=======================================================================
        # Set window properties.
        #=======================================================================
        win_props = WindowProperties(self.win.getProperties())
        win_props.setTitle(title)
        win_props.setFullscreen(isFullscreen)
        win_props.setSize(width, height)
        self.win.requestProperties(win_props)
        
        # Apply the property changes.
        self.graphicsEngine.openWindows()

        #=======================================================================
        # Scene related fields.
        #=======================================================================
        self.sceneNP = None
        '''
        Main scene node path. There can be only one scene at any given time.
        '''

        #=======================================================================
        # Actor related fields.
        #=======================================================================
        self.actorNP = {}
        '''
        Dictionary of actor node paths keyed with the actor name.Internal use 
        only.
        '''
        
        self.actorOINP = None
        '''
        Actor of interest node path. There can be only one actor of interest
        at any given time.
        '''

        self.actorOIName = None
        '''
        Actor of interest name. There can be only one actor of interest at any 
        given time.
        '''

        self.actorOIMoveDir = 0
        '''
        Actor of interest movement direction indicator. Forward is 1, reverse is
        -1, and stop is 0.
        '''

        self.actorOITurnDir = 0
        '''
        Actor of interest turn direction indicator. Left is 1, right is -1, and 
        no turn is 0.
        '''

        self.actorOIMoveSpeed = 3
        '''
        Actor of interest translational speed. Distance units per second.
        '''
        
        self.actorOITurnSpeed = 30
        '''
        Actor of interest rotational speed. Degrees per second.
        '''
        
        self.actorOILocation = Vec3D.zero()
        '''
        Actor of interest's location coordinates after the last frame.
        '''
        
        self.actorOIVelocity = Vec3D.zero()
        '''
        Actor of interest's velocity vector after the last frame.
        '''

        #=======================================================================
        # Camera related fields.
        #=======================================================================
        self.cameraNP = {}
        '''
        Dictionary of camera node paths keyed with the camera name.
        '''

        # Add the showbase camera as 'default'.
        self.cameraNP['default'] = self.cam

        #=======================================================================
        # Illumination related fields
        #=======================================================================
        self.lightNP  = {}
        '''
        Dictionary of light node paths keyed with the light name.
        '''

        self.goalNP  = {}
        '''
        Dictionary of goal node paths keyed with the goal name.
        '''
        
        #=======================================================================
        # Display region related fields.
        #=======================================================================
        self.displayRegion = {}
        '''
        Dictionary of display regions keyed with the display region name.
        '''

        self.displayRegionOI = None
        '''
        Display region of interest. Any action related to display regions 
        will be applied to the current display region of interest.
        '''

        self.displayRegionOIName = None
        '''
        Display region of interest name. Any action related to display 
        regions will be applied to the current display region of interest.
        '''

        # Add the display region associated with the default showbase camera.
        self.displayRegion['default'] = self.camNode.getDisplayRegion(0)
        self.displayRegion['default'].setSort(1) 
        self.accept('control-`', self.setDisplayRegionOfInterest, ['default'])
        
        # Current display region of interest is the 'default' one.
        self.displayRegionOI = self.displayRegion['default']
        self.displayRegionOIName = 'default'

        #=======================================================================
        # AI related fields.
        #=======================================================================
        self.AIWorld = AIWorld(self.render)
        self.AICharacter = {}

        #=======================================================================
        # Trace file related fields.
        #=======================================================================
        self.traceFile = None
        '''Handle to the trace file.'''

        self.traceMessage = ''
        '''Message to be written to the trace file.'''

        self.onScreenHelpNP = None
        '''Text node path holding the on screen help information.'''

        #=======================================================================
        # Other fields.
        #=======================================================================
        self.clock = globalClock
        '''Exposes Panda3D's GlobalClock.'''
        
        self.userDialog = OnscreenText(text='', bg=(0,0,0,.6), fg=(.8,0,0,1),
                                       mayChange=True)
       
        self.userDialogTask = None
       
        self.isNotifyUser = True
        
        # We do not need the default mouse controls.
        self.disableMouse()
        
        # We do not need the default camera.
        self.cam.node().setActive(False)

        # Make sure a clean exit from the application when requested.
        atexit.register(self.exitfunc)
        
        # Default collision traverser.
        self.cTrav = CollisionTraverser()
        
        #=======================================================================
        # On screen help setup.
        #=======================================================================
        OSHelp_str = '\nHELP\n'
        text_font = self.loader.loadFont('cmtt12', spaceAdvance=.52)
        self.onScreenHelpNP = OnscreenText(text=OSHelp_str,
                                           font=text_font,
                                           style=1, 
                                           fg=(1,1,1,1),
                                           bg=(0,0,0,.6), 
                                           align=TextNode.ALeft,
                                           scale=.05,
                                           mayChange=True)
        self.onScreenHelpNP.reparentTo(self.a2dTopLeft)
        self.onScreenHelpNP.hide()

        #=======================================================================
        # Keyboard control related fields and default settings.
        #=======================================================================
        self.keyMap = {}
        '''Dictionary of keyboard controls keyed with the action name.'''

        self.setActorOIActionKey('forward', 'arrow_up')
        self.setActorOIActionKey('reverse', 'arrow_down')
        self.setActorOIActionKey('turn left', 'arrow_left')
        self.setActorOIActionKey('turn right', 'arrow_right')

        self.addHotKey('t', 'toggle pip', self.toggleDisplayRegion, [])
        self.addHotKey('f1', 'help', self.toggleOnScreenHelp, [])
        self.addHotKey('escape', 'quit', self.shutDown, [])

    def setTracing(self, fileName, flag=True):
        if flag and self.traceFile is None:
            self.traceFile = open(fileName, 'w')
            self.taskMgr.add(self.traceUpdateTask, 'traceUpdate', sort=100)
        else:
            self.taskMgr.remove('traceUpdate')
            self.traceFile.close()
            self.traceFile = None

    def getTracing(self):
        return self.taskMgr.hasTaskNamed('traceUpdate')

    def setupScene(self, modelName, position=(0,0,0), orientation=(0,0,0), 
                   scale=(1,1,1)):
        base_path  = os.path.dirname(__file__)
        model_path = os.path.join(base_path, 'models', modelName)
        model_path = Filename.fromOsSpecific(model_path)
        self.sceneNP = self.loader.loadModel(model_path)
        self.sceneNP.setPosHprScale(position, orientation, scale)
        self.sceneNP.reparentTo(self.render)

        base.setBackgroundColor((.1, .1, .1, 0))

    def getObject(self, name):
        return self.render.findAllMatches('**/'+name)

    def setObjectSolid(self, name, flag):
        if flag:
            self.getObject(name).setCollideMask(BitMask32(0x001),
                                                BitMask32(0x001))
        else:
            self.getObject(name).setCollideMask(BitMask32.allOff(),
                                                BitMask32(0x001))

    def setObjectGoal(self, name, flag):
        if flag:
            self.getObject(name).setCollideMask(BitMask32(0x002),
                                                     BitMask32(0x002))
        else:
            self.getObject(name).setCollideMask(BitMask32.allOff(),
                                                     BitMask32(0x002))
    
    def addHotKey(self, hotkey, action, callback, args):
        self.keyMap[action] = hotkey
        self.accept(hotkey, callback, args)
    
    def addActor(self, name, position=(0,0,0), orientation=(0,0,0), 
                 scale=(1,1,1), collisionSphere=None):
        # Create the scene node path.
        actor_np = NodePath(ActorNode(name))
        actor_np.setPosHpr(position, orientation)
        actor_np.reparentTo(self.render)

        # Attach model to the node path.
        base_path  = os.path.dirname(__file__)
        model_path = os.path.join(base_path, 'models', name)
        model_path = Filename.fromOsSpecific(model_path)
        model_np   = self.loader.loadModel(model_path)
        model_np.setScale(scale)
        model_np.reparentTo(actor_np)

        #=======================================================================
        # Make actor physics collidible.
        #=======================================================================
        # Attach collision solid to the node path. 
        cn = CollisionNode(name+'PhysicsCollisionNode')
        cn.setIntoCollideMask(BitMask32.allOff())
        cn.setFromCollideMask(BitMask32.bit(0))
        cs = CollisionSphere(collisionSphere[0:3], collisionSphere[3])
        cn.addSolid(cs)
        actor_cnp = actor_np.attachNewNode(cn)
        
        # Add actor to the physics collision detection system.
        handler = PhysicsCollisionHandler()
        handler.addCollider(actor_cnp, actor_np)
        # self.cTrav.addCollider(actor_cnp, handler)

        #=======================================================================
        # Make actor AI compatible.
        #=======================================================================
        ai_character = AICharacter(name, actor_np, mass=50, movt_force=10, 
                                   max_force=30)
        self.AICharacter[name] = ai_character
        self.AIWorld.addAiChar(ai_character)
        
        #=======================================================================
        # Make actor events collidible.
        #=======================================================================
        # Attach collision solid to the node path. 
        cn = CollisionNode(name+'EventCollisionNode')
        cn.setIntoCollideMask(BitMask32.allOff())
        cn.setFromCollideMask(BitMask32.bit(1))
        cs = CollisionSphere(collisionSphere[0:3], collisionSphere[3])
        cn.addSolid(cs)
        actor_cnp = actor_np.attachNewNode(cn)
        actor_cnp.show()
        
        # Add actor to the collision event detection system.
        handler = CollisionHandlerEvent()
        handler.addInPattern('%fn-enters')
        handler.addOutPattern('%fn-exits')
        self.cTrav.addCollider(actor_cnp, handler)
        self.accept(name+'EventCollisionNode'+'-enters', self.onActorEnterEventFunc)
        self.accept(name+'EventCollisionNode'+'-exits', self.onActorExitEventFunc)

        self.actorNP[name] = actor_np
        
        # The most recently added actor becomes actor of interest.
        self.setActorOfInterest(name)

        self.taskMgr.add(self.actorOIStateUpdateTask,'actorStateUpdate',sort=50)
    
    def activateActorOIControl(self, flag):
        if flag:
            self.taskMgr.add(self.actorOIControlTask,'actorControl',sort=10)
        else:
            self.taskMgr.remove('actorControl')

    def setActorOfInterest(self, name):
        self.actorOINP = self.actorNP[name]
        self.actorOIName = name
        self.actorOILocation = self.actorOINP.getPos()

    def setActorOIActionKey(self, action, key):
        self.keyMap[action] = key
        self.accept(key, self.setActorOIAction, [action])
        self.accept(key+'-up', self.setActorOIAction, [action+' stop'])
        self.keyMap[action] = key

    def setActorOIAction(self, action):
        if action == 'forward':
            self.actorOIMoveDir = 1;
        elif action == 'reverse':
            self.actorOIMoveDir = -1;
        elif action == 'forward stop' or action == 'reverse stop':
            self.actorOIMoveDir = 0;
        elif action == 'turn right':
            self.actorOITurnDir = -1;
        elif action == 'turn left':
            self.actorOITurnDir = 1;
        elif action == 'turn right stop' or action == 'turn left stop':
            self.actorOITurnDir = 0;

    def addLight(self, name, hotkey, type, color=(1,1,1,1), position=(0,0,0), 
                 orientation=(0,0,0)):
        if type == 'ambient':
            light_np = AmbientLight(name)
            light_np.setColor(color)
        elif type == 'point':
            light_np = PointLight(name)
            light_np.setColor(color)
            light_np.setPoint(position)
        elif type == 'directional':
            light_np = DirectionalLight(name)
            light_np.setColor(color)
            light_np.setPoint(position)
            light_np.setDirection(orientation)
        else:
            return
        
        self.keyMap[name] = hotkey
        self.accept(hotkey, self.toggleLight, [name])
        
        self.lightNP[name] = self.render.attachNewNode(light_np)

    def toggleLight(self, name):
        light_np = self.lightNP[name]
        if self.render.hasLight(light_np):
            self.render.setLightOff(light_np)
            msg = '''Light [{0}] turned off.'''.format(name)
        else:
            self.render.setLight(light_np)
            msg = '''Light [{0}] turned on.'''.format(name)
        self.notifyUser(msg, 2)

    def activateLight(self, name, flag):
        if flag:
            self.render.setLight(self.lightNP[name])
        else:
            self.render.setLightOff(self.lightNP[name])

    def addCamera(self, name, hotkey, parent, lens, position=(0,0,0), 
                  orientation=(0,0,0)):
        camera_n  = Camera(name, lens)
        camera_np = NodePath(camera_n)
        camera_np.setPosHpr(position, orientation)
        camera_np.reparentTo(parent)

        self.keyMap[name] = hotkey
        self.accept(hotkey, self.activateCamera, [name])
        
        self.cameraNP[name] = camera_np

    def activateCamera(self, name):
        dr = self.displayRegionOI
        ar = float(dr.getPixelWidth()) / dr.getPixelHeight()
        self.cameraNP[name].node().getLens().setAspectRatio(ar)
        
        self.displayRegionOI.setCamera(self.cameraNP[name])
        self.cameraNP[name].node().setActive(True)
        
        msg = '''Camera [{0}] active on display region [{1}].'''
        self.notifyUser(msg.format(name, self.displayRegionOIName), 2)

    def addDisplayRegion(self, name, hotkey, lrbt):
        dr = self.win.makeDisplayRegion(lrbt[0],lrbt[1],lrbt[2],lrbt[3])
        dr.setSort(99)
        dr.setActive(False)

        self.keyMap[name] = hotkey
        self.accept(hotkey, self.setDisplayRegionOfInterest, [name])
        
        self.displayRegion[name] = dr

    def setDisplayRegionOfInterest(self, name):
        self.displayRegionOI = self.displayRegion[name]
        self.displayRegionOIName = name
        self.displayRegionOI.setActive(True)

        msg = '''Display region [{0}] selected.'''
        self.notifyUser(msg.format(self.displayRegionOIName), 2)

    def activateDisplayRegion(self, name, flag):
        self.displayRegion[name].setActive(flag)

    def toggleDisplayRegion(self, name=None):
        if name is not None:
            dr = self.displayRegion[name]
        else:
            dr =  self.displayRegionOI 
        dr.setActive(not dr.isActive())

    def startAITask(self):
        taskMgr.add(self.AIUpdateTask, "AIUpdate")

    def stopAITask(self):
        taskMgr.remove("AIUpdate")

    def shutDown(self):
        if self.traceFile: self.traceFile.close()
        sys.exit()
    
    def toggleOnScreenHelp(self):
        str = '\n'.join([n.title().ljust(10)+' : '+k.title() 
                         for n,k in self.keyMap.iteritems()])
        self.onScreenHelpNP.setText('\n'+str)
        if self.onScreenHelpNP.isHidden():
            self.onScreenHelpNP.show()
        else:
            self.onScreenHelpNP.hide()
    
    def notifyUser(self, msg, delay):
        if self.isNotifyUser:
            self.userDialog.setText(msg)
            self.userDialog.show()
            if self.userDialogTask is not None: self.userDialogTask.remove() 
            self.userDialogTask = self.taskMgr.doMethodLater(delay,
                                                             self.userDialog.hide,
                                                             'destroyMessage',
                                                             extraArgs=[])
    
    def AIUpdateTask(self, task):
        self.AIWorld.update()
        return task.cont        

    def traceUpdateFunc(self):
        pass

    def traceUpdateTask(self, task):
        self.traceUpdateFunc()
        message = 'timestamp:{0:.4f},{1}\n'.format(self.clock.getFrameTime(),
                                                   self.traceMessage)
        self.traceFile.write(message)
        return task.cont

    def onActorEnterEventFunc(self, collisionEntry):
        pass

    def onActorExitEventFunc(self, collisionEntry):
        pass

    def actorOIControlTask(self, task):
        dt = self.clock.getDt()
		
        rotation = self.actorOITurnSpeed * self.actorOITurnDir * dt
        self.actorOINP.setH(self.actorOINP, rotation)
        
        translation = self.actorOIMoveSpeed * self.actorOIMoveDir * dt
        self.actorOINP.setY(self.actorOINP, translation)
        
        return task.cont

    def actorOIStateUpdateFunc(self):
        pass

    def actorOIStateUpdateTask(self, task):
        self.actorOIStateUpdateFunc()
        return task.cont



if __name__ == "__main__":
    
    # Panda configuration variables.
    config = {}
    config['framerate']  = ConfigVariableBool('show-frame-rate-meter',True)
    config['display']    = ConfigVariableString('load-display','pandagl')
 
    app = SimWorldBase(width=1680, height=1050, isFullscreen=True, title='Maze')

    app.run()
        