# Name of RA column
config.ra_name='raJ2000'

# Name of Dec column
config.dec_name='decJ2000'

# An ordered list of column names to use in ingesting the catalog. With an empty list, column names will be discovered from the first line after the skipped header lines.
config.file_reader.colnames=['uniqueId', 'raJ2000', 'decJ2000', 'u', 'g', 'r', 'i', 'z', 'y', 'isresolved',
                             'isvariable']

# Name of column stating if the object is resolved (optional).
config.is_resolved_name='isresolved'

# Name of column to use as an identifier (optional).
config.id_name='uniqueId'

# The values in the reference catalog are assumed to be in AB magnitudes. List of column names to use for photometric information.  At least one entry is required.
config.mag_column_list=['u', 'g', 'r', 'i', 'z', 'y']

# Depth of the HTM tree to make.  Default is depth=7 which gives
#               ~ 0.3 sq. deg. per trixel.
config.dataset_config.indexer['HTM'].depth=8

# Name of column stating if the object is measured to be variable (optional).
config.is_variable_name='isvariable'

