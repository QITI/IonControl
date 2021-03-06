# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import collections
from PyQt5 import QtCore
import os
import logging
import traceback
import numpy
from datetime import datetime
from .Script import ScriptException
from modules.quantity import is_Q, Q
from trace.PlottedTrace import PlottedTrace
from trace.TraceCollection import TraceCollection
from trace import pens
from pyqtgraph.graphicsItems.ViewBox import ViewBox
import functools
import pytz
from persist.MeasurementLog import  Measurement, Parameter, Result
from copy import deepcopy

from QITI_communicate_instruments.flir.black_fly_camera import BlackFlyCamera
import PySpin
import scipy.ndimage




class ScriptHandler(QtCore.QObject):
    """The ScriptHandler is what handles all the interfacing between the Script and the GUI. The Script
    emits signals, which are picked up by the ScriptHandler, which executes the necessary changes on the
    GUI."""
    def __init__(self, script, experimentUi):
        super().__init__()
        self.experimentUi = experimentUi
        self.scanExperiment = experimentUi.tabDict['Scan']
        self.globalVariablesUi = experimentUi.globalVariablesUi
        self.voltageControlWindow = experimentUi.voltageControlWindow
        self.scanControlWidget = self.scanExperiment.scanControlWidget
        self.evaluationControlWidget = self.scanExperiment.evaluationControlWidget
        self.analysisControlWidget = self.scanExperiment.analysisControlWidget
        self.fitWidget = self.scanExperiment.fitWidget
        self.pulser = self.experimentUi.pulser
        self.AWGUiDict = experimentUi.AWGUiDict
        self.currentLines = []
        self.script = script
        self.scriptTraces = dict() #Place to put traces generated by the script
        self.traceAlreadyCreated = dict() #Place to keep track of whether or not a given trace has been added to the traceUi
        self.globalVariablesRevertDict = dict() #original values of global variables which are changed
        self.namedTraceList = set()
        
        self.pyspin_system = PySpin.System.GetInstance()
        self.pyspin_camera_dict = dict()
        
        #Experiment information signals
        self.scanExperiment.progressUi.stateChanged.connect(self.onScanStateChanged)
        self.analysisControlWidget.analysisResultSignal.connect(self.onAnalysisResult)
        self.scanExperiment.evaluatedDataSignal.connect(self.onData)
        self.scanExperiment.allDataSignal.connect(self.onAllData)
        
        #status signals
        self.script.locationSignal.connect( self.onLocation )
        self.script.exceptionSignal.connect( self.onException )
        self.script.consoleSignal.connect( self.onConsoleSignal )
        
        #shutter signals
        self.script.setShutterSignal.connect(self.onSetShutter)
        
        #Camera signals
        self.script.addCameraSignal.connect(self.onAddCamera) 
        self.script.startCameraSignal.connect(self.onStartCamera)
        self.script.stopCameraSignal.connect(self.onStopCamera)
        self.script.plotCameraImageSignal.connect(self.onPlotCameraImage)

        #action signals
        self.script.setGlobalSignal.connect(self.onSetGlobal)
        self.script.addGlobalSignal.connect(self.onAddGlobal)
        self.script.pauseScriptSignal.connect(self.onPauseScriptFromScript)
        self.script.stopScriptSignal.connect(self.onStopScriptFromScript)
        self.script.startScanSignal.connect(self.onStartScan)
        self.script.setScanSignal.connect(self.onSetScan)
        self.script.setEvaluationSignal.connect(self.onSetEvaluation)
        self.script.setAnalysisSignal.connect(self.onSetAnalysis)
        self.script.plotPointSignal.connect(self.onPlotPoint)
        self.script.plotListSignal.connect(self.onPlotList)
        self.script.plotImageSignal.connect(self.onPlotImage)
        self.script.addPlotSignal.connect(self.onAddPlot)
        self.script.addImagePlotSignal.connect(self.onAddImagePlot)
        self.script.pauseScanSignal.connect(self.onPauseScan)
        self.script.stopScanSignal.connect(self.onStopScan)
        self.script.abortScanSignal.connect(self.onAbortScan)
        self.script.createTraceSignal.connect(self.onCreateTrace)
        self.script.closeTraceSignal.connect(self.onCloseTrace)
        self.script.genericCallSignal.connect(self.onGenericCall)
        self.script.consolePrintSignal.connect( self.onConsolePrintSignal )
        self.script.fitSignal.connect(self.onFit)
        self.script.namedTraceSignal.connect(self.onPushToNamedTrace)
        self.script.loadVoltageDefSignal.connect(self.onLoadVoltageDef)
        self.script.programAWGSignal.connect(self.onProgramAWG)
        self.script.setAWGSignal.connect(self.onSetAWG)

        #finished signal
        self.script.finished.connect(self.onFinished)

    def scriptCommand(func):#@NoSelf
        """Decorator for script commands. 
        
        Catches exceptions, sets the script exception variables, and wakes the script after the
        specified action has been completed.
        """
        def baseScriptCommand(self, *args, **kwds):
            logger = logging.getLogger(__name__)
            try:
                error, message = func(self, *args, **kwds)
                if error and message:
                    logger.error(message)
                    self.writeToConsole(message, error=True)
                    raise ScriptException(message)
                elif error and (not message):
                    raise ScriptException('')
                elif (not error) and message:
                    logger.debug(message)
                    self.writeToConsole(message)
            except Exception as e:
                with QtCore.QMutexLocker(self.script.mutex):
                    self.script.exception = e
                    logger.error(traceback.print_exc())
            finally:
                self.script.guiWait.wakeAll()
        baseScriptCommand.__name__ = func.__name__
        baseScriptCommand.__doc__ = func.__doc__
        return baseScriptCommand
    
    @QtCore.pyqtSlot(str, float, str)
    @scriptCommand
    def onAddGlobal(self, name, value, unit):
        """Add a global 'name' and set it to 'value, unit'"""
        name = str(name) #signal is passed as a QString
        value = float(value)
        unit = str(unit)
        magValue = Q(value, unit)
        doesNotExist = name not in list(self.globalVariablesUi.keys())
        if doesNotExist:
            self.globalVariablesUi.model.addVariable(name)
            message = "Global variable {0} created\n".format(name)
        else:
            message = "Global variable {0} already exists\n".format(name)
        self.globalVariablesUi.model.update([('Global', name, magValue)])
        message +=  "Global variable {0} set to {1} {2}".format(name, value, unit)
        error = False
        return (error, message)

    @QtCore.pyqtSlot(str, float, str)
    @scriptCommand
    def onSetGlobal(self, name, value, unit):
        """Set global 'name' to 'value, unit'"""
        name = str(name) #signal is passed as a QString
        value = float(value)
        unit = str(unit)
        magValue = Q(value, unit)
        doesNotExist = name not in list(self.globalVariablesUi.keys())
        if doesNotExist:
            message = "Global variable {0} does not exist.".format(name)
            error = True
        else:
            if name not in self.globalVariablesRevertDict: #entry is added to revert dict only the first time a global is set in a script
                self.globalVariablesRevertDict[name] = deepcopy(self.globalVariablesUi.globalDict[name])
            self.globalVariablesUi.model.update([('Global', name, magValue)])
            message = "Global variable {0} set to {1} {2}".format(name, value, unit)
            error = False
        return (error, message)
    
    @QtCore.pyqtSlot(int, bool)
    @scriptCommand
    def onSetShutter(self, index, value):
        """Set shutter 'index' to 'value'"""
        index = int(index)
        value = bool(value)
        shutter = self.experimentUi.pulser.shutter
        mask = 1 << index 
        shutter =  (shutter & ~mask) | ((value << index) & mask) 
        setattr(self.experimentUi.pulser,'shutter',shutter)
        return (False,'Set shutter {index} to {value}'.format(index=index,value=value))
        
    def getShutter(self,index):
        """Returns the current value of the shutter"""
        shutter = self.experimentUi.pulser.shutter
        value = shutter >> index & 1
        return bool(value)
    

    @QtCore.pyqtSlot(str, str)
    @scriptCommand
    def onLoadVoltageDef(self, name, path):
        """Load voltage definition given by name and the associated '_shuttling.xml' from path"""
        if self.voltageControlWindow: # can be None
            if path:
                name = os.path.join(path,name)
            self.voltageControlWindow.voltageFilesUi.loadVoltageDef(name)
            message = "Loaded voltage definition file {0} ".format(name)
            error = False
        else:
            message = "Voltage control was disabled by the UI"
            error = True
        return (error, message)

    @QtCore.pyqtSlot(str, object, object)
    @scriptCommand
    def onGenericCall(self, funcname, args, kwargs):
        """Return a generic piece of data from the program, specified by 'funcname'
        """
        funcname = str(funcname)
        try:
            with QtCore.QMutexLocker(self.script.mutex):
                self.script.genericResult = getattr(self, funcname)(*args, **kwargs)
            self.script.genericWait.wakeAll()
        except Exception as e:
            return True, str(e)
        return False, "{0}{1} executed".format(funcname, args)

    def getGlobal(self, name):
        """Return the value of a global variable, returns a quantity 'q' with 
        magnitude given by q.m and units given by q.u"""
        if name in self.globalVariablesUi.globalDict.keys():
            return self.globalVariablesUi.globalDict[name]
        return ScriptException("Global '{}' does not exist!".format(name))
    
     
    
    

    @QtCore.pyqtSlot(list)
    @scriptCommand
    def onStartScan(self, globalOverrides=list()):
        """Start the scan
        globalOverrrides is list of (name, magnitude) values or list of (name, (value, unit)) values
        that will override global variables during the scan
        """
        logger = logging.getLogger(__name__)
        with QtCore.QMutexLocker(self.script.mutex):
            self.script.scanIsRunning = True
            self.script.analysisReady = False
            self.script.dataReady = False
            self.script.allDataReady = False
        # make sure we hand on a list of (key, magnitude) pairs
        myGlobalOverrides = list()
        for key, value in globalOverrides:
            if not is_Q(value):
                if isinstance(value, collections.Sized):
                    value = Q(value[0], value[1])
                else:
                    value = Q(value)
            myGlobalOverrides.append((key, value))
        self.experimentUi.onStart(globalOverrides=myGlobalOverrides)
        scan = self.scanControlWidget.settingsName
        evaluation = self.evaluationControlWidget.settingsName
        analysis = self.analysisControlWidget.currentAnalysisName
        message = "Scan started at {0} with scan = {1}, evaluation = {2}, analysis = {3}".format(str(datetime.now()), scan, evaluation, analysis)
        logger.info(message)
        self.writeToConsole(message, color='green')
        return (False, None)

    @QtCore.pyqtSlot()
    @scriptCommand
    def onPauseScan(self):
        self.experimentUi.actionPause.trigger()
        error = False
        message = "Scan paused"
        return (error, message)
        
    @QtCore.pyqtSlot()
    @scriptCommand
    def onStopScan(self):
        self.experimentUi.actionStop.trigger()
        with QtCore.QMutexLocker(self.script.mutex):
            self.script.scanIsRunning = False
        error = False
        message = "Scan stopped"
        return (error, message)
        
    @QtCore.pyqtSlot()
    @scriptCommand
    def onAbortScan(self):
        self.experimentUi.actionAbort.trigger()
        with QtCore.QMutexLocker(self.script.mutex):
            self.script.scanIsRunning = False
        error = False
        message = "Scan aborted"
        return (error, message)

    @QtCore.pyqtSlot(str)
    @scriptCommand
    def onSetScan(self, name):
        name = str(name)
        doesNotExist = (self.scanControlWidget.comboBox.findText(name)==-1)
        if doesNotExist:
            message = "Scan {0} does not exist.".format(name)
            error = True
        else:
            self.scanControlWidget.loadSetting(name)
            message = "Scan set to {0}".format(name)
            error = False
        return (error, message)
    
    @QtCore.pyqtSlot(str)
    @scriptCommand
    def onSetEvaluation(self, name):
        name = str(name)
        doesNotExist = (self.evaluationControlWidget.comboBox.findText(name)==-1)
        if doesNotExist:
            message = "Evaluation {0} does not exist.".format(name)
            error = True
        else:
            self.evaluationControlWidget.loadSetting(name)
            message = "Evaluation set to {0}".format(name)
            error = False
        return (error, message)
    
    @QtCore.pyqtSlot(str)
    @scriptCommand
    def onSetAnalysis(self, name):
        name = str(name)
        doesNotExist = (name not in self.analysisControlWidget.analysisDefinitionDict)
        if doesNotExist:
            message = "Analysis {0} does not exist.".format(name)
            error = True
        else:
            self.analysisControlWidget.onLoadAnalysisConfiguration(name)
            message = "Analysis set to {0}".format(name)
            error = False
        return (error, message)

    @QtCore.pyqtSlot(str, str)
    @scriptCommand
    def onSetAWG(self, AWGname, name):
        AWGname = str(AWGname)
        name = str(name)
        if AWGname not in self.AWGUiDict:
            message = "AWG {0} does not exist".format(AWGname)
            error = True
        else:
            doesNotExist = (self.AWGUiDict[AWGname].settingsComboBox.findText(name)==-1)
            if doesNotExist:
                message = "AWG {0} settings {1} does not exist.".format(AWGname, name)
                error = True
            else:
                self.AWGUiDict[AWGname].loadSetting(name)
                message = "AWG {0} settings set to {1}".format(AWGname, name)
                error = False
        return (error, message)

    @QtCore.pyqtSlot(str)
    @scriptCommand
    def onProgramAWG(self, AWGname):
        AWGname = str(AWGname)
        if AWGname not in self.AWGUiDict:
            message = "AWG {0} does not exist".format(AWGname)
            error = True
        else:
            self.AWGUiDict[AWGname].device.program()
            message = "AWG {0} programmed".format(AWGname)
            error = False
        return (error, message)

    @QtCore.pyqtSlot(str)
    @scriptCommand
    def onAddPlot(self, name):
        if name not in list(self.scanExperiment.plotDict.keys()):
            self.scanExperiment.addPlot(str(name))
            message = 'Plot {0} added'.format(name)
        else:
            message = 'Plot {0} already exists'.format(name)
        error = False
        return (error, message)
    
    @QtCore.pyqtSlot(str)
    @scriptCommand
    def onAddImagePlot(self, name):
        if name not in list(self.scanExperiment.imagePlotDict.keys()):
            self.scanExperiment.addImagePlot(str(name))
            message = 'Plot {0} added'.format(name)
        else:
            message = 'Plot {0} already exists'.format(name)
        error = False
        return (error, message)
    
    @QtCore.pyqtSlot(str,str)
    @scriptCommand
    def onAddCamera(self, camera_name,camera_serial):
        if camera_name not in list(self.pyspin_camera_dict.keys()):
            camera = BlackFlyCamera(camera_name,camera_serial,self.pyspin_system)
            self.pyspin_camera_dict[camera_name] = camera
            message = 'Camera {0} added'.format(camera_name)
        else:
            message = 'Camera {0} already exists'.format(camera_name)
        error = False
        return (error, message)
    
    @QtCore.pyqtSlot(str)
    @scriptCommand
    def onStartCamera(self, camera_name):
        if camera_name in list(self.pyspin_camera_dict.keys()):
            camera = self.pyspin_camera_dict[camera_name]
            camera.start_camera()
            message = 'Camera {0} started'.format(camera_name)
        else:
            message = 'Camera {0} not found. Add using addCamera'.format(camera_name)
        error = False
        return (error, message)
    
    @QtCore.pyqtSlot(str)
    @scriptCommand
    def onStopCamera(self, camera_name):
        if camera_name in list(self.pyspin_camera_dict.keys()):
            camera = self.pyspin_camera_dict[camera_name]
            camera.stop_camera()
            message = 'Camera {0} stopped'.format(camera_name)
        else:
            message = 'Camera {0} not found. Add using addCamera'.format(camera_name)
        error = False
        return (error, message)
    
    @QtCore.pyqtSlot(str,str,dict)
    @scriptCommand
    def onPlotCameraImage(self, camera_name,plot_name,kwargs):
        image = numpy.array([])
        error,message = False, ''
        try:
            if camera_name in list(self.pyspin_camera_dict.keys()):
                camera = self.pyspin_camera_dict[camera_name]
                status,image = camera.get_camera_image()
                if not status:
                    message = 'Camera image incomplete'
                else:
                    if kwargs.get('angle'):
                        angle = kwargs.get('angle')
                        image = scipy.ndimage.rotate(image,angle)
                    if kwargs.get('roi'):
                        xs,ys,xe,ye = kwargs['roi']
                        image = image[xs:xe,ys:ye]
                    if kwargs.get('filename'):
                        filename = kwargs.get('filename')
                        numpy.savetxt(filename)
                    color_levels = kwargs.get('color_levels')
                    self.onPlotImage(image,plot_name,{'color_levels':color_levels})
                    message = 'Camera image plotted'.format(camera_name)
            else:
                message = 'Camera {0} not found. Add using addCamera'.format(camera_name)
        except Exception as e:
            error, message = True, str(e)
        with QtCore.QMutexLocker(self.script.mutex):
            self.script.genericResult = image
        self.script.genericWait.wakeAll()
        print('.')
        return (error, message)
    
    @QtCore.pyqtSlot(list)
    @scriptCommand
    def onCreateTrace(self, traceCreationData):
        traceCreationData = list(map(str, traceCreationData))
        [traceName, plotName, xUnit, xLabel, comment] = traceCreationData
        if plotName not in self.scanExperiment.plotDict:
            message = "plot {0} does not exist".format(plotName)
            error = True
        else:
            traceCollection = TraceCollection()
            yColumnName = 'y0'
            plottedTrace = PlottedTrace(traceCollection, self.scanExperiment.plotDict[plotName], pens.penList, xColumn = 'x',
                                        yColumn=yColumnName, name=traceName, xAxisUnit = xUnit, xAxisLabel = xLabel, windowName=plotName)
            self.scanExperiment.plotDict[plotName]["view"].enableAutoRange(axis=ViewBox.XAxis)
            plottedTrace.traceCollection.name = self.script.shortname
            commentIntro = "Created by script {0}".format(self.script.shortname)
            plottedTrace.traceCollection.comment = commentIntro + " -- " + comment if comment else commentIntro
            plottedTrace.traceCollection.autoSave = True
            plottedTrace.traceCollection.filenamePattern = traceName
            self.scriptTraces[traceName] = plottedTrace
            self.traceAlreadyCreated[traceName] = False #Keep track of whether the trace has already been added
            error = False
            message = "Added trace {0}\n plot: {1}\n xUnit: {2}\n xLabel: {3}\n comment: {4}".format(traceName, plotName, xUnit, xLabel, comment)
        return (error, message)

    @QtCore.pyqtSlot(str)
    @scriptCommand
    def onCloseTrace(self, traceName):
        traceName = str(traceName)
        if traceName not in self.scriptTraces:
            message = "Trace {0} does not exist".format(traceName)
            error = True
        else:
            plottedTrace = self.scriptTraces.pop(traceName) #remove from the list of script traces
            plottedTrace.traceCollection.description["traceFinalized"] = datetime.now(pytz.utc)
            plottedTrace.traceCollection.save()
            self.registerMeasurement(plottedTrace)
            message = "Trace {0} closed".format(traceName)
            error = False
        return error, message

    @QtCore.pyqtSlot(str, str)
    @scriptCommand
    def onFit(self, fitName, traceName):
        fitName = str(fitName)
        traceName = str(traceName)
        fitAnalysisIndex = self.fitWidget.fitSelectionComboBox.findText(fitName)
        if fitAnalysisIndex < 0:
            message = "Fit '{0}' does not exist.".format(fitName)
            error = True
        elif traceName not in self.scriptTraces:
            message = "Trace '{0}' does not exist".format(traceName)
            error = True
        else:
            plottedTrace = self.scriptTraces[traceName]
            self.fitWidget.fitSelectionComboBox.setCurrentIndex(fitAnalysisIndex)
            message = "Fitting trace '{0}' using fit '{1}'".format(traceName, fitName)
            self.fitWidget.fit(plottedTrace)
            with QtCore.QMutexLocker(self.script.mutex):
                self.script.fitResults.clear()
                self.script.fitResults['error'] = dict()
                for index, parameter in enumerate(plottedTrace.fitFunction.parameterNames):
                    self.script.fitResults[parameter] = plottedTrace.fitFunction.parameters[index]
                    self.script.fitResults['error'][parameter] = plottedTrace.fitFunction.parametersConfidence[index]
            error = False
        return (error, message)

    @QtCore.pyqtSlot(float, float, str, int)
    @scriptCommand
    def onPlotPoint(self, x, y, traceName, plotStyle=-1):
        """Plot point (x,y) to traceName"""
        traceName = str(traceName)
        error, message = self.plotList([x], [y], traceName, plotStyle=plotStyle)
        return (error, message) 
        
    @QtCore.pyqtSlot(list, list, str, bool, int)
    @scriptCommand
    def onPlotList(self, xList, yList, traceName, overwrite=False, plotStyle=-1):
        """Plot [x1, x2,...], [y1, y2,...] to traceName"""
        traceName = str(traceName)
        error, message = self.plotList(xList, yList, traceName, overwrite, plotStyle=plotStyle)
        return (error, message)
        
    @QtCore.pyqtSlot(numpy.ndarray, str,dict)
    @scriptCommand
    def onPlotImage(self,image_array, plotname,kwargs):
        plotname = str(plotname)
        image_plot = self.scanExperiment.imagePlotDict[plotname]['image_item']
        image_plot.setImage(image_array.copy(),levels = kwargs.get('color_levels'))
        error = False
        message = 'Image plotted'
        return (error, message)
        
    def plotList(self, xList, yList, traceName, overwrite=False, plotStyle=-1):
        """Plot [x1, x2,...], [y1, y2,...] to traceName"""
        try:
            plottedTrace = self.scriptTraces[traceName]
            created = self.traceAlreadyCreated[traceName]
        except KeyError:
            message = "Trace {0} does not exist".format(traceName)
            error = True
            return (error, message)
        if not (len(xList)==len(yList)):
            message = 'x and y lists are of unequal lengths'
            error = True
            return (error, message)
        else:
            if created:
                if not overwrite:
                    plottedTrace.x = numpy.append(plottedTrace.x, xList)
                    plottedTrace.y = numpy.append(plottedTrace.y, yList)
                else:
                    plottedTrace.x = xList
                    plottedTrace.y = yList
                plottedTrace.replot()
            else:
                plottedTrace.x = numpy.array(xList)
                plottedTrace.y = numpy.array(yList)
                self.scanExperiment.traceui.addTrace(plottedTrace, pen=-1, style=plotStyle)
                if self.scanExperiment.traceui.expandNew:
                    self.scanExperiment.traceui.expand(plottedTrace)
                self.scanExperiment.traceui.resizeColumnsToContents()
                self.traceAlreadyCreated[traceName] = True
            message = '{0}, {1} plotted to trace: {2}'.format(xList, yList, traceName)
            error = False
        return (error, message)


    @QtCore.pyqtSlot(str, str, int, float, str, bool)
    @scriptCommand
    def onPushToNamedTrace(self, topNode, child, row, data, col, ignorenans):
        self.namedTraceList.add(topNode)
        self.scanExperiment.namedTraceui.updateExternally(topNode, child, row, data, col, ignoreTrailingNaNs=ignorenans)
        message = 'pushed value {0} to named trace {1}'.format(data, topNode+'_'+child)
        error = False
        return (error, message)

    @QtCore.pyqtSlot()
    @scriptCommand
    def onPauseScriptFromScript(self):
        self.experimentUi.scriptingWindow.onPauseScript(True)
        message = None
        error = False
        return (error, message)

    @QtCore.pyqtSlot()
    @scriptCommand
    def onStopScriptFromScript(self):
        self.onStopScript()
        message = 'script stopped'
        error = False
        return (error, message)

    @QtCore.pyqtSlot(str, bool, str)
    def onConsolePrintSignal(self, message, error, color):
        self.writeToConsole(message, error=error, color=color)
    
    def onStartScript(self):
        """Runs when start script button clicked. Starts the script and disables some aspects of the script GUI"""
        if not self.script.isRunning():
            self.globalVariablesRevertDict.clear()
            with QtCore.QMutexLocker(self.script.mutex):
                self.script.paused = False
                self.script.stopped = False
                self.script.exception = None
                self.script.start()
                self.namedTraceList = set()

    def onPauseScript(self, paused):
        """Runs when pause script button clicked. Sets paused variable and wakes up script if unpaused."""
        with QtCore.QMutexLocker(self.script.mutex):
            self.script.paused = paused
            if not paused:
                self.script.pauseWait.wakeAll()
        
    def onStopScript(self):
        """Runs when stop script button is clicked. Sets stopped variable and wakes up all waitConditions.""" 
        with QtCore.QMutexLocker(self.script.mutex):
            self.script.stopped = True
            self.script.paused = False
            self.script.waitOnScan = False
            self.script.repeat = False
            self.script.analysisReady = True
            self.script.dataReady = True
            self.script.allDataReady = True
            self.script.guiWait.wakeAll()
            self.script.pauseWait.wakeAll()
            self.script.scanWait.wakeAll()
            self.script.dataWait.wakeAll()
            self.script.analysisWait.wakeAll()
            self.script.genericWait.wakeAll()
            self.scanExperiment.namedTraceui.saveAndUpdateFileList()

    def onPauseScriptAndScan(self):
        """Runs when pause script and scan button is clicked."""
        self.onPauseScript(True)
        self.experimentUi.actionPause.trigger()
        
    def onStopScriptAndScan(self):
        """Runs when stop script and scan button is clicked."""
        self.onStopScript()
        self.experimentUi.actionStop.trigger()

    def onRepeat(self, repeat):
        """Runs when repeat button is clicked. Set repeat variable."""
        with QtCore.QMutexLocker(self.script.mutex):
            self.script.repeat = repeat

    def onSlow(self, slow):
        """Runs when slow button is clicked. Set slow variable."""
        with QtCore.QMutexLocker(self.script.mutex):
            self.script.slow = slow
            
    @QtCore.pyqtSlot(str)
    def onScanStateChanged(self, state):
        """Runs when the scan state changes"""
        with QtCore.QMutexLocker(self.script.mutex):
            self.script.scanStatus = state
            if state == 'idle':
                self.writeToConsole("scan finished at {0}".format(str(datetime.now())), False, 'green')
                self.script.scanIsRunning = False
                self.script.scanWait.wakeAll()
            else:
                self.script.scanIsRunning = True

    @QtCore.pyqtSlot(object)
    def onAnalysisResult(self, allResults):
        with QtCore.QMutexLocker(self.script.mutex):
            self.script.analysisResults = allResults
            self.script.analysisReady = True
            self.script.analysisWait.wakeAll()

    @QtCore.pyqtSlot(dict)
    def onData(self, data):
        with QtCore.QMutexLocker(self.script.mutex):
            self.script.data = data
            self.script.dataReady = True
            self.script.dataWait.wakeAll()

    @QtCore.pyqtSlot(dict)
    def onAllData(self, allData):
        with QtCore.QMutexLocker(self.script.mutex):
            self.script.allData = allData
            self.script.allDataReady = True
            self.script.allDataWait.wakeAll()

    @QtCore.pyqtSlot()
    def onFinished(self):
        for plottedTrace in list(self.scriptTraces.values()):
            plottedTrace.traceCollection.description["traceFinalized"] = datetime.now(pytz.utc)
            plottedTrace.traceCollection.save()
            self.registerMeasurement(plottedTrace)
        self.scriptTraces = dict()
        self.scanExperiment.namedTraceui.saveAndUpdateFileList(self.namedTraceList)

    @QtCore.pyqtSlot(str, bool, str)
    def onConsoleSignal(self, message, error, color):
        """Runs when script emits a console signal. Writes message to console."""
        self.writeToConsole(message, error=error, color=color)
    
    @QtCore.pyqtSlot(str, str)
    def onException(self, message, trace):
        """Runs when script emits exception signal. Highlights error."""
        logger = logging.getLogger(__name__)
        message = str(message)
        trace = str(trace)
        logger.error(trace)
        self.writeToConsole(trace, error=True)
        self.experimentUi.scriptingWindow.markError(self.currentLines, message)
    
    @QtCore.pyqtSlot(list)        
    def onLocation(self, locs):
        """Mark where the script currently is"""
        logger = logging.getLogger(__name__)
        self.currentLines = []
        if locs:
            self.currentLines = [loc[1] for loc in locs]
            for loc in locs:
                message = "Executing {0} in {1} at line {2}".format( loc[3], os.path.basename(str(loc[0])), loc[1] )
                logger.debug(message)
                self.writeToConsole(message, False)
        else: #This should never execute
            message = "onLocation called while not executing script"
            logger.warning(message)
            self.writeToConsole(message, True)
        self.experimentUi.scriptingWindow.markLocation(self.currentLines)
        
    def writeToConsole(self, message, error=False, color=''):
        """write a message to the console."""
        self.experimentUi.scriptingWindow.writeToConsole(message, error, color)

    def registerMeasurement(self, plottedTrace):
        """register a script created trace in the measurement log"""
        measurement = Measurement(scanType= 'Script', scanName=plottedTrace.traceCollection.filenamePattern,
                                  scanParameter='', scanTarget='',
                                  scanPP = '',
                                  evaluation='<Script {0}>'.format(self.script.shortname),
                                  startDate=plottedTrace.traceCollection.description['traceCreation'],
                                  duration=None,
                                  filename=plottedTrace.traceCollection.filename,
                                  comment=plottedTrace.traceCollection.comment,
                                  longComment=None,
                                  failedAnalysis=None)
        space = self.scanExperiment.measurementLog.container.getSpace('GlobalVariables')
        for name, value in self.experimentUi.globalVariablesUi.globalDict.items():
            measurement.parameters.append( Parameter(name=name, value=value, space=space) )
        measurement.plottedTraceList = [plottedTrace]
        self.scanExperiment.measurementLog.container.addMeasurement(measurement)

