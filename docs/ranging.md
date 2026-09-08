# Ranging

TF02-Pro frames begin with `0x59 0x59`, contain little-endian distance,
strength and temperature, and end with an 8-byte checksum. Corrupt frames are
rejected and counted. The filter supports a median window, EMA coefficient,
outlier threshold and stale timestamp policy. No camera-only exact meters are
invented.
