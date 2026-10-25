# syntax=docker/dockerfile:1

FROM ubuntu:focal AS gnb-build

SHELL ["/bin/bash", "-c"]

ARG BUILD_JOBS=4
ARG BUILD_CPUSET=4-7
ENV BUILD_JOBS=${BUILD_JOBS}

RUN apt-get -y update
RUN DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC apt-get install -y \
    apt-utils \
    bc \
    git \
    iproute2 \
    iputils-ping \
    libuhd-dev \
    net-tools \
    nano \
    software-properties-common \
    tcpdump \
    uhd-host

# OAI's build helper hardcodes -j$(nproc). Override nproc inside the image so
# every OAI dependency and target build honors the configured job ceiling.
RUN printf '#!/bin/sh\nprintf "%%s\\n" "${BUILD_JOBS:-4}"\n' > /usr/local/bin/nproc && \
    chmod +x /usr/local/bin/nproc

COPY --from=oai-source / /openairinterface5g

WORKDIR /openairinterface5g/cmake_targets/
RUN DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC \
    taskset -c "${BUILD_CPUSET}" ./build_oai -I

WORKDIR /
RUN git clone https://github.com/ujjwalpawar/asn1c.git
RUN apt-get install -y bison flex
WORKDIR /asn1c
RUN autoreconf -iv
RUN ./configure --prefix /opt/asn1c/
RUN taskset -c "${BUILD_CPUSET}" make -j"${BUILD_JOBS}"
RUN make install

WORKDIR /openairinterface5g/cmake_targets/

# Reuse compiled objects between image builds. Copy only runtime artifacts out
# of the cache mount so build objects do not become final-image layers.
RUN --mount=type=cache,id=oai-gnb-build,target=/openairinterface5g/cmake_targets/ran_build,sharing=locked \
    taskset -c "${BUILD_CPUSET}" bash -c '\
      source /openairinterface5g/oaienv; \
      ./build_oai --gNB & build_pid=$!; \
      while kill -0 "$build_pid" 2>/dev/null; do \
        progress=$(grep -oE "\[[[:space:]]*[0-9]+%\]" /openairinterface5g/cmake_targets/log/all.txt 2>/dev/null | tail -1); \
        if [[ -n "$progress" ]]; then echo "gNB compile progress: $progress"; else echo "gNB compile progress: configuring"; fi; \
        sleep 15; \
      done; \
      wait "$build_pid"' && \
    rm -rf /opt/gnb-artifacts && \
    mkdir -p /opt/gnb-artifacts && \
    find /openairinterface5g/cmake_targets/ran_build/build -maxdepth 1 -type f \
      \( -name nr-softmodem -o -name 'lib*.so' \) \
      -exec cp -a {} /opt/gnb-artifacts/ \;

FROM ubuntu:focal AS gnb-runtime

SHELL ["/bin/bash", "-c"]

ARG SOURCE_COMMIT
ARG SOURCE_DIRTY=false
LABEL org.opencontainers.image.source="https://github.com/andrewferguson/openairinterface-nfapi-netsys" \
      org.opencontainers.image.revision="${SOURCE_COMMIT}" \
      org.opencontainers.image.source-dirty="${SOURCE_DIRTY}"

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC apt-get install -y --no-install-recommends \
      bc \
      gdb \
      iproute2 \
      iputils-ping \
      libatlas3-base \
      libblas3 \
      libconfig9 \
      libsctp1 \
      libusb-1.0-0 \
      net-tools \
      openssl \
      procps \
      tcpdump && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p \
      /openairinterface-nfapi-netsys/cmake_targets/ran_build/build \
      /usr/local/lib

COPY --from=gnb-build /opt/gnb-artifacts/nr-softmodem \
    /openairinterface-nfapi-netsys/cmake_targets/ran_build/build/
COPY --from=gnb-build /opt/gnb-artifacts/lib*.so /usr/local/lib/
COPY --from=gnb-build /openairinterface5g/oaienv /openairinterface-nfapi-netsys/

RUN ldconfig && \
    ldd /openairinterface-nfapi-netsys/cmake_targets/ran_build/build/nr-softmodem | \
      tee /tmp/nr-softmodem-ldd.txt && \
    ! grep -q 'not found' /tmp/nr-softmodem-ldd.txt && \
    rm /tmp/nr-softmodem-ldd.txt

WORKDIR /openairinterface-nfapi-netsys/cmake_targets/ran_build/build/
COPY template_gnb.conf .
