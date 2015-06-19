"""Set color terms for LSST Simulations"""

from lsst.pipe.tasks.colorterms import Colorterm, ColortermDict

"""SDSS terms derived in ipython notebook that can be found at:
https://github.com/jbkalmbach/lsst_colorTransform/blob/master/LSST-SDSS%20Color%20Transformations.ipynb

Max errors in u > 5%, y < 2%, all other bands < 1%."""

root.data = {
    "sdss*": ColortermDict(data={
        'u':    Colorterm(primary="u", secondary="g", c0= 0.01765032, c1=-0.10413400, c2= 0.02569698)
        'g':    Colorterm(primary="g", secondary="r", c0=-0.00425500, c1=-0.04584603, c2=-0.01922445),
        'r':    Colorterm(primary="r", secondary="i", c0= 0.00035896, c1= 0.00776209, c2=-0.02407214),
        'i':    Colorterm(primary="i", secondary="z", c0=-0.00002106, c1=-0.02325962, c2=-0.00143333),
        'z':    Colorterm(primary="z", secondary="i", c0=-0.00117210, c1=-0.09616944, c2= 0.14426774),
        'y':    Colorterm(primary="z", secondary="i", c0= 0.00254280, c1= 0.22164297, c2=-0.52703611),
    }),
}
