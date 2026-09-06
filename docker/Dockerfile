# Use a clean, official Ubuntu 22.04 base image
FROM ubuntu:22.04

# Prevent interactive prompts during package installations
ENV DEBIAN_FRONTEND=noninteractive

USER root

# Install system dependencies including C++ compiler, SUMO, Python, and download tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    clang \
    bison \
    flex \
    libxml2-dev \
    zlib1g-dev \
    sumo \
    sumo-tools \
    sumo-doc \
    python3 \
    python3-pip \
    python3-dev \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set up SUMO environment variables
ENV SUMO_HOME=/usr/share/sumo
ENV PATH=$SUMO_HOME/bin:$PATH

# Download and compile OMNeT++ 5.7.1 (headless) from the GitHub source tag
WORKDIR /opt
RUN wget --no-check-certificate https://github.com/omnetpp/omnetpp/archive/refs/tags/omnetpp-5.7.1.tar.gz \
    && tar -xzf omnetpp-5.7.1.tar.gz \
    && mv omnetpp-omnetpp-5.7.1 omnetpp \
    && rm omnetpp-5.7.1.tar.gz

# Change default Docker RUN shell to bash so that setenv sources correctly
SHELL ["/bin/bash", "-c"]

# Add OMNeT++ binaries to PATH
ENV PATH=/opt/omnetpp/bin:$PATH

WORKDIR /opt/omnetpp
# Source setenv to initialize release variables, then configure and build OMNeT++ headless
RUN source ./setenv && ./configure WITH_QTENV=no WITH_OSG=no WITH_OSGEARTH=no \
    && make -j$(nproc)

# Download and compile the Veins 5.2 framework
WORKDIR /opt
RUN wget --no-check-certificate https://github.com/sommer/veins/archive/refs/tags/veins-5.2.tar.gz \
    && tar -xzf veins-5.2.tar.gz \
    && mv veins-veins-5.2 veins \
    && rm veins-5.2.tar.gz

WORKDIR /opt/veins
RUN source /opt/omnetpp/setenv && ./configure \
    && make -j$(nproc)

# Set up the LBDT Application working directory
WORKDIR /app

# Install python packages
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy all source files
COPY . .

# Copy default antenna.xml from Veins examples (we use our custom config.xml from host)
RUN cp /opt/veins/examples/veins/antenna.xml /app/veins_sim/antenna.xml

# Build our custom OMNeT++ application binary linking to the Veins library
WORKDIR /app/veins_sim
RUN source /opt/omnetpp/setenv && opp_makemake -f --deep -O out -I/opt/veins/src -L/opt/veins/src -lveins
RUN source /opt/omnetpp/setenv && make -j$(nproc)

# Make the entrypoint script executable
RUN chmod +x /app/docker/entrypoint.sh

# Run the startup script to launch Python socket server, launchd, and Veins
WORKDIR /app
ENTRYPOINT ["/bin/bash", "/app/docker/entrypoint.sh"]
