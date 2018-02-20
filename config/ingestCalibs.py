from lsst.obs.lsstSim.ingest import SimCalibsParseTask
config.parse.retarget(SimCalibsParseTask)
config.parse.translation = {
                            'expTime': 'EXPTIME',
                            }
config.register.columns = {'filter': 'text',
                           'ccd': 'text',
                           'sensor': 'text',
                           'raft': 'text',
                           'calibDate': 'text',
                           'validStart': 'text',
                           'validEnd': 'text',
                           }

config.parse.translators = {'ccd': 'translate_ccd',
                            'sensor': 'translate_sensor',
                            'raft': 'translate_raft',
                            'filter': 'translate_filter',
                            'calibDate': 'translate_calibDate',
                            }

config.register.unique = ['filter', 'ccd', 'calibDate', 'raft']
config.register.tables = ['bias', 'dark', 'flat', 'fringe']
config.register.visit = ['calibDate', 'filter']
