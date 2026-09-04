# The build recipe. Generic: it packages whatever this repository's analysis is.
# The base is public and carries the platform SDK and DuckDB, nothing else.
ARG BASE_IMAGE=ghcr.io/subtractsoftware/tarn-job-base:0.8.17
FROM ${BASE_IMAGE}
COPY main.py parameters.json /job/
COPY dashboard/ /job/dashboard/
# Not optional. Without it the container runs the base image's default python, which exits at
# once with nothing to do, and the platform records a zero-second run with no outputs.
CMD ["python", "/job/main.py"]
