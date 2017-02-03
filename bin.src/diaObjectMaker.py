#!/user/bin/env python2
from lsst.pipe.base import TaskRunner, CmdLineTask, ArgumentParser, ConfigDatasetType
import lsst.pex.config as pex_config
from lsst.afw.table import MultiMatch, SourceRecord, SchemaMapper, CoordKey
import lsst.afw.geom
import numpy

o_init = MultiMatch.__init__
def __n_init__(self, schema, dataIdFormat, coordField="coord", idField="id", radius=None,
    RecordClass=SourceRecord):
    if radius is None:
        radius = 0.5*lsst.afw.geom.arcseconds
    elif not isinstance(radius, lsst.afw.geom.Angle):
        raise ValueError("'radius' argument must be an Angle")
    self.radius = radius
    self.mapper = SchemaMapper(schema)
    self.mapper.addMinimalSchema(schema, True)
    self.coordKey = CoordKey(schema[coordField])
    self.idKey = schema.find(idField).key
    self.dataIdKeys = {}
    outSchema = self.mapper.editOutputSchema()
    self.objectKey = outSchema.addField("object", type=numpy.int64, doc="Unique ID for joined sources")
    for name, dataType in dataIdFormat.items():
        if hasattr(dataType, '__len__'):
            # tuple so:
            self.dataIdKeys[name] = outSchema.addField(name, type=dataType[0], size=dataType[1], doc="'%s' data ID component")
        else:
            self.dataIdKeys[name] = outSchema.addField(name, type=dataType, doc="'%s' data ID component")
    # self.result will be a catalog containing the union of all matched records, with an 'object' ID
    # column that can be used to group matches.  Sources that have ambiguous matches may appear
    # multiple times.
    self.result = None
    # self.reference will be a subset of self.result, with exactly one record for each group of matches
    # (we'll use the one from the first catalog matched into this group)
    # We'll use this to match against each subsequent catalog.
    self.reference = None
    # A set of ambiguous objects that we may want to ultimately remove from the final merged catalog.
    self.ambiguous = set()
    # Table used to allocate new records for the ouput catalog.
    self.table = RecordClass.Table.make(self.mapper.getOutputSchema())
    # Counter used to assign the next object ID
    self.nextObjId = 1

MultiMatch.__init__ = __n_init__

class ConfigDiaDatasetType(ConfigDatasetType):
    def getDatasetType(self, namespace):
    """Return the dataset type as a string, from the appropriate config field
    @param[in] namespace  parsed command
    """
    # getattr does not work reliably if the config field name is dotted,
    # so step through one level at a time
    keyList = self.name.split(".")
    value = namespace.config
    for key in keyList:
        try:
	    value = getattr(value, key)
        except KeyError:
	    raise RuntimeError("Cannot find config parameter %r" % (self.name,))
    return value+"_diaSource"

class DiaObjectMakerRunner(TaskRunner):
    def run(self, parsedCmd):
        return [self.__call__(parsedCmd.id.refList),]

    def __call__(self, refList):
        """!Run the Task on a single target.
        This default implementation assumes that the 'args' is a tuple
        containing a data reference and a dict of keyword arguments.
        @warning if you override this method and wish to return something when
        doReturnResults is false, then it must be picklable to support
        multiprocessing and it should be small enough that pickling and
        unpickling do not add excessive overhead.
        @param args     Arguments for Task.run()
        @return:
        - None if doReturnResults false
        - A pipe_base Struct containing these fields if doReturnResults true:
            - dataRef: the provided data reference
            - metadata: task metadata after execution of run
            - result: result returned by task run, or None if the task fails
        """
        if self.log is None:
            self.log = Log.getDefaultLogger()
        task = self.makeTask()
        result = None  # in case the task fails
        result = task.run(refList)
        task.writeMetadata(refList[0])

        if self.doReturnResults:
            return Struct(
                refList=refList,
                metadata=task.metadata,
                result=result,
            )

class DiaObjectMakerTask(pex_config.Config):
    coaddName = pex_config.Field(str, doc="Name of coadd used to make diaSources",
                                 default="goodSeeing")

class DiaObjectMakerTask(CmdLineTask):
    RunnerClass = DiaObjectMakerRunner
    ConfigClass = pex_config.Config
    _DefaultName = "DiaObjectMakerTask"

    def _getMetadataName(self):
        return "diaObjectMakerMetadata"

    def run(self, ref_list):
        data_id = ref_list[0].dataId
        seed_cat = ref_list[0].get()
        data_id_format = {}
        for key, value in data_id.iteritems():
            if type(value) == str:
                vtype = (str, len(value)*2)
            else:
                vtype = type(value)            
            data_id_format[key] = vtype
        multi_match = MultiMatch(seed_cat.schema, data_id_format)
        for data_ref in ref_list:
            dia_source_cat = data_ref.get()
            multi_match.add(dia_source_cat, data_ref.dataId)
        dia_object_cat = multi_match.finish()
        ref_list[0].put(dia_object_cat, 'deepDiff_diaObj')

    @classmethod
    def _makeArgumentParser(cls):
        """!Create and return an argument parser
        @param[in] cls      the class object
        @return the argument parser for this task.
        This override is used to delay making the data ref list until the dataset type is known;
        this is done in @ref parseAndRun.
        """
        parser = pipeBase.ArgumentParser(name=cls._DefaultName)
        parser.add_id_argument(name="--id",
                               datasetType=pipeBase.ConfigDiaDatasetType(name="coaddName"),
                               help="data IDs, e.g. --id visit=12345 ccd=1,2^0,3")
        return parser


if __name__ == "__main__":
    DiaObjectMakerTask.parseAndRun()

