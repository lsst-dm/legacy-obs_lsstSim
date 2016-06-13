# Name of RA column
config.ra_name = 'raJ2000'

# Name of Dec column
config.dec_name = 'decJ2000'

# Name of column to use as an identifier (optional).
config.id_name = 'uniqueId'

# The values in the reference catalog are assumed to be in AB magnitudes.
# List of column names to use for photometric information.  At least one entry is required.
config.mag_column_list = ['lsst_g', 'lsst_r', 'lsst_i']

# Name of column stating if the object is resolved (optional).
config.is_resolved_name = 'isresolved'

# Name of column stating if the object is measured to be variable (optional).
config.is_variable_name = 'isvariable'
