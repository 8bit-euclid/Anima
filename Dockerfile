FROM ubuntu:22.04

RUN apt-get update && \
   apt-get install -y \
        wget \
        xz-utils \
        libgl1-mesa-glx \
        libxrender1 \
        libxi6 \
        libxkbcommon-x11-0 \
        libsm6 \
        libice6 \
        libxext6 \
        libxfixes3 && \
   rm -rf /var/lib/apt/lists/*

ENV BLENDER_VERSION=4.4.3
ARG BLENDER_MM_VERSION=${BLENDER_VERSION%.*}
ARG BLENDER_NAME=blender-${BLENDER_VERSION}-linux-x64
RUN wget -q https://download.blender.org/release/Blender${BLENDER_MM_VERSION}/${BLENDER_NAME}.tar.xz \
    && tar -xf ${BLENDER_NAME}.tar.xz \
    && mv ${BLENDER_NAME} /opt/blender \
    && rm ${BLENDER_NAME}.tar.xz

# Create Blender config directory and copy user preferences template
ARG BLENDER_CONFIG_DIR=/root/.config/blender/${BLENDER_MM_VERSION}/config
RUN mkdir -p ${BLENDER_CONFIG_DIR}
COPY .blender/config/userpref.blend ${BLENDER_CONFIG_DIR}/userpref.blend

# # Install Python dependencies
# ARG PIP=blender/blender-${BLENDER_VERSION}-linux-x64/${BLENDER_MM_VERSION}/python/bin/pip3
# RUN ${PIP} install --no-cache-dir \
#         numpy \
#         scipy 

WORKDIR /app
CMD ["/opt/blender/blender"]
# CMD ["/opt/blender/blender", "--background", "--python-console"]