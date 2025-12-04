FROM debian:bullseye-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg2 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Add FreeSWITCH repository
RUN wget -O - https://files.freeswitch.org/repo/deb/debian-release/fsstretch-archive-keyring.asc | apt-key add - && \
    echo "deb https://files.freeswitch.org/repo/deb/debian-release/ bullseye main" > /etc/apt/sources.list.d/freeswitch.list

# Install FreeSWITCH
RUN apt-get update && apt-get install -y \
    freeswitch \
    freeswitch-mod-console \
    freeswitch-mod-logfile \
    freeswitch-mod-dialplan-xml \
    freeswitch-mod-sofia \
    freeswitch-mod-commands \
    freeswitch-mod-dptools \
    freeswitch-mod-event-socket \
    freeswitch-mod-g711 \
    freeswitch-mod-opus \
    freeswitch-mod-sndfile \
    freeswitch-mod-native-file \
    freeswitch-mod-say-en \
    && rm -rf /var/lib/apt/lists/*

# Create recordings directory
RUN mkdir -p /recordings && chown freeswitch:freeswitch /recordings

# Expose ports
# 5060: SIP (UDP)
# 5080: External SIP (TCP)
# 8021: ESL (Event Socket Layer)
# 16384-32768: RTP
EXPOSE 5060/udp 5080/tcp 8021/tcp 16384-32768/udp

# Copy custom configuration
COPY freeswitch.xml /etc/freeswitch/freeswitch.xml

# Run as freeswitch user
USER freeswitch

# Start FreeSWITCH
CMD ["freeswitch", "-nonat", "-nc", "-nf"]
