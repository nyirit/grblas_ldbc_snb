# GraphBLAS implementation using grblas Python API for LDBC SNB BI queries

## Getting started

1. Install Anaconda.

2. Install [`grblas`](https://github.com/metagraph-dev/grblas): `conda install -c conda-forge grblas`

## Usage

Example usage:
`python -m ldbc_snb_grblas 9 ../social_network-csv_basic-sf0.1/ 2012-05-31 2012-06-30`

Example profiling:
`python -m cProfile -s cumulative -m ldbc_snb_grblas 9 ../social_network-csv_basic-sf0.1/ 2012-05-31 2012-06-30`
