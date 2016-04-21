from lsst.obs.lsstSim.ingest import SimParseTask
config.parse.retarget(SimParseTask)
config.parse.translation = {'visit': 'OBSID',
                          'expTime': 'EXPTIME',
                          }
config.parse.translators = {'taiObs': 'translate_taiobs',
                          'filter': 'translate_filter',
                          'ccd': 'translate_ccd',
                          'sensor': 'translate_sensor',
                          'raft': 'translate_raft',
                          'channel': 'translate_channel',
                          'snap': 'translate_snap'
                          }
config.register.columns = {'visit':    'int',
                         'channel':  'text',
                         'snap':     'int',
                         'sensor':   'text',
                         'ccd':      'text',
                         'raft':     'text',
                         'filter':   'text',
                         'taiObs':   'text',
                         'expTime':  'double',
                         }
config.register.visit = ['visit', 'filter']
config.register.unique = ['visit', 'sensor', 'raft', 'channel', 'snap']