"""环境与实验阶段常量。 / Environment and experiment-phase constants."""

ENVIRONMENT_NAMES = (
    "clear", "dim_light", "night", "high_wind", "dust", "dust_storm",
    "light_snow", "heavy_snow", "extreme_cold", "high_heat", "flat",
    "gentle_slope", "steep_slope", "loose_soil", "sand", "dense_rocks",
    "sharp_rocks", "crater", "radiation", "high_radiation", "magnetic_noise",
    "long_delay", "blackout", "ice", "wet_soil", "thin_atmosphere",
    "shadow", "sunny", "rough_terrain", "low_visibility",
)

PHASE_NAMES = (
    "normal", "global_comms_failure", "local_heater_failure", "recovery",
    "local_camera_failure", "mixed_recurrence",
)
