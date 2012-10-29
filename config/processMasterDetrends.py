from lsst.obs.lsstSim import LsstSimCalibIsrTask
root.detrend.process.isr.retarget(LsstSimCalibIsrTask)
root.detrend.process.isr.doBias=True
root.detrend.process.isr.doDark=False
root.detrend.process.isr.doFlat=False
#Isr = LsstSimIsrTask
#root.detrend.process.isr.registry.register("biasIsr", Isr)
#root.detrend.process.isr.registry.register("flatIsr", Isr)
#root.detrend.process.isr['biasIsr'].doBias = False
#root.detrend.process.isr['biasIsr'].doDark = False
#root.detrend.process.isr['biasIsr'].doFlat = False
#root.detrend.process.isr['flatIsr'].doBias = True
#root.detrend.process.isr['flatIsr'].doDark = True
#root.detrend.process.isr['flatIsr'].doFlat = False
#root.detrend.process.isr.name = 'biasIsr'
