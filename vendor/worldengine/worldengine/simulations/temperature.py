import numpy
from noise import snoise2  # http://nullege.com/codes/search/noise.snoise2

from worldengine.simulations.basic import find_threshold_f


class TemperatureSimulation:
    @staticmethod
    def is_applicable(world):
        return not world.has_temperature()

    def execute(self, world, seed):
        e = world.layers["elevation"].data
        ml = world.start_mountain_th()  # returns how many percent of the world are mountains
        ocean = world.layers["ocean"].data

        t = self._calculate(world, seed, e, ml)
        t_th = [
            ("polar", find_threshold_f(t, world.temps[0], ocean)),
            ("alpine", find_threshold_f(t, world.temps[1], ocean)),
            ("boreal", find_threshold_f(t, world.temps[2], ocean)),
            ("cool", find_threshold_f(t, world.temps[3], ocean)),
            ("warm", find_threshold_f(t, world.temps[4], ocean)),
            ("subtropical", find_threshold_f(t, world.temps[5], ocean)),
            ("tropical", None),
        ]
        world.temperature = (t, t_th)

    @staticmethod
    def _calculate(world, seed, elevation, mountain_level):
        width = world.width
        height = world.height

        rng = numpy.random.RandomState(seed)  # create our own random generator
        base = rng.randint(0, 4096)
        temp = numpy.zeros((height, width), dtype=float)

        """
        Orbital parameters (PlanetKit: user-set, defaults Earth-like — no RNG):
         distance_to_sun: Earth-like = 1.0 (habitable zone ~0.7–1.3); closer → hotter
         axial_tilt:      0.0 = equator-centered hot band; 0.5 ≈ 90° Uranus-style
        """
        distance_to_sun = float(getattr(world, "distance_to_sun", 1.0))
        distance_to_sun = max(0.1, distance_to_sun)
        distance_to_sun *= distance_to_sun  # inverse-square law for later divide
        axial_tilt = float(getattr(world, "axial_tilt", 0.0))
        axial_tilt = min(max(-0.5, axial_tilt), 0.5)

        border = width / 4
        octaves = 8  # number of passes of snoise2
        freq = 16.0 * octaves
        n_scale = 1024 / float(height)

        for y in range(0, height):  # TODO: Check for possible numpy optimizations.
            y_scaled = float(y) / height - 0.5  # -0.5...0.5

            # map/linearly interpolate y_scaled to latitude measured from where the most sunlight hits the world:
            # 1.0 = hottest zone, 0.0 = coldest zone
            latitude_factor = numpy.interp(
                y_scaled, [axial_tilt - 0.5, axial_tilt, axial_tilt + 0.5], [0.0, 1.0, 0.0], left=0.0, right=0.0
            )
            for x in range(0, width):
                n = snoise2((x * n_scale) / freq, (y * n_scale) / freq, octaves, base=base)

                # Added to allow noise pattern to wrap around right and left.
                if x <= border:
                    n = (snoise2((x * n_scale) / freq, (y * n_scale) / freq, octaves, base=base) * x / border) + (
                        snoise2(((x * n_scale) + width) / freq, (y * n_scale) / freq, octaves, base=base)
                        * (border - x)
                        / border
                    )

                t = (latitude_factor * 12 + n * 1) / 13.0 / distance_to_sun
                if elevation[y, x] > mountain_level:  # vary temperature based on height
                    if elevation[y, x] > (mountain_level + 29):
                        altitude_factor = 0.033
                    else:
                        altitude_factor = 1.00 - (float(elevation[y, x] - mountain_level) / 30)
                    t *= altitude_factor
                temp[y, x] = t

        return temp
