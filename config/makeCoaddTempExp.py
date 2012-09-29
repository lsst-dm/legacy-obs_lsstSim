from lsst.obs.lsstSim.selectLsstImages import SelectLsstImagesTask

root.select.retarget(SelectLsstImagesTask)
root.consolidateKeys=("raft", "sensor")
