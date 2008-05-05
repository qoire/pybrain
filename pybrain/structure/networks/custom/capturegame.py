__author__ = 'Tom Schaul, tom@idsia.ch'

import random 

from pybrain import SharedFullConnection, MotherConnection, MDLSTMLayer, IdentityConnection
from pybrain import ModuleMesh, LinearLayer, TanhLayer, SigmoidLayer
from pybrain.structure.networks import BorderSwipingNetwork


class CaptureGameNetwork(BorderSwipingNetwork):
    """ a custom-made swiping network for the Capture-Game.
    As an input it takes an array of values corresponding to the occupation state on
    the board positions (black, white, empty) -  the output produced is an array
    of values for positions that correspond to the preference of moving there. """                    
    
    size = 5
    insize = 2
    bnecksize = 1
    combbnecksize = 1
    hsize = 5
    predefined = None
    directlink = False
    componentclass = TanhLayer
    peepholes = False
    clusterssize = 1
    clusteroverlap = 0
    outputs = 1
    comboutputs = 0    
    wtRange = 1
    
    # a flag purely for xml reading to avoid full reconstruction:            
    rebuilt = False
    
    def __init__(self, **args):
        """
        @param clusterssize: the side of the square for clustering: if > 1, an extra layer for cluster-construction is added 
        @param clusteroverlap: by how much should the cluster overlap (default = 0)
        @param directlink: should connections from the input directly to the bottleneck be included?         
        """
        self.predefined = {}   
        if 'size' in args:
            self.size = args['size']      
        args['dims'] = (self.size, self.size)  
        BorderSwipingNetwork.__init__(self, **args)
        
        if not self.rebuilt:
            self._buildCaptureNetwork()
            self.sortModules()
            self.rebuilt = True
            self.setArgs(rebuilt = True)
                    
    def _buildCaptureNetwork(self):
        # the input is a 2D-mesh (as a view on a flat input layer)
        inmod = LinearLayer(self.insize*self.size*self.size, name = 'input')
        inmesh = ModuleMesh.viewOnFlatLayer(inmod, (self.size, self.size), 'inmesh')
        
        # the output is a 2D-mesh (as a view on a flat sigmoid output layer)
        outmod = SigmoidLayer(self.outputs*self.size*self.size, name = 'output')
        outmesh = ModuleMesh.viewOnFlatLayer(outmod, (self.size, self.size), 'outmesh')
        
        if self.componentclass == MDLSTMLayer:
            c = lambda: MDLSTMLayer(self.hsize, 2, self.peepholes).meatSlice()
            hiddenmesh = ModuleMesh(c, (self.size, self.size, 4), 'hidden', baserename = True)
        else:
            hiddenmesh = ModuleMesh.constructWithLayers(self.componentclass, self.hsize, (self.size, self.size, 4), 'hidden')
        
        self._buildBorderStructure(inmesh, hiddenmesh, outmesh)
        
        # add the identity connections for the states
        for m in self.modules:
            if isinstance(m, MDLSTMLayer):
                tmp = m.stateSlice()
                index = 0
                for c in list(self.connections[m]):
                    if isinstance(c.outmod, MDLSTMLayer):
                        self.addConnection(IdentityConnection(tmp, c.outmod.stateSlice(), 
                                                              outSliceFrom = self.hsize*(index), 
                                                              outSliceTo = self.hsize*(index+1)))
                        index += 1
        if self.directlink:
            self._buildDirectLink(inmesh, outmesh)
        
    def _buildDirectLink(self, inmesh, outmesh):                
        if not 'directconn' in self.predefined:
            self.predefined['directconn'] = MotherConnection(inmesh.componentOutdim*outmesh.componentIndim, 'inconn')
        for unit in self._iterateOverUnits():
            self.addConnection(SharedFullConnection(self.predefined['directconn'], inmesh[unit], outmesh[unit]))
        
    def _generateName(self):
        """ generate a quasi unique name, using construction parameters """
        name = self.__class__.__name__
        if self.size != 5:
            name += '-s'+str(self.size)
        name += '-h'+str(self.hsize)
        if self.bnecksize != 1:
            name += '-bn'+str(self.bnecksize)
        if self.directlink:
            name += '-direct'
        if self.componentclass != TanhLayer:
            name += '-'+self.componentclass.__name__
        if self.outputs > 1:
            name += '-o'+str(self.outputs)
        if self.comboutputs > 0:
            name += '-combo'+str(self.comboutputs)
        if self.combbnecksize > 0:
            name += '-combbn'+str(self.combbnecksize)            
        if self.clusterssize != 1:
            name += '-cluster'+str(self.clusterssize)+'ov'+str(self.clusteroverlap)    
        # add a 6-digit random number, for distinction:
        name += '--'+str(int(random.random()*9e5+1e5))   
        # TODO: use hash of the weights.
        return name
    