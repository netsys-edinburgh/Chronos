# syntax=docker/dockerfile:1

FROM ubuntu:jammy

RUN apt update
RUN apt install -y build-essential libsctp-dev lksctp-tools zlib1g-dev
RUN apt install -y iproute2 iputils-ping nano

ARG SOURCE_COMMIT
ARG SOURCE_DIRTY=false
LABEL org.opencontainers.image.source="https://github.com/ujjwalpawar/phobos-5g" \
      org.opencontainers.image.revision="${SOURCE_COMMIT}" \
      org.opencontainers.image.source-dirty="${SOURCE_DIRTY}"

COPY --from=proxy-source / /phobos-5g

WORKDIR /phobos-5g

# build the proxy
RUN make

# build the global slot checker
RUN gcc -O3 -o global_slotchecker src/timeout_handling_sc_global.c