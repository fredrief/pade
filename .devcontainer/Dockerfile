FROM hpretl/iic-osic-tools:latest

# Install build dependencies for gdstk (qhull missing from base image)
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    libqhull-dev \
    && rm -rf /var/lib/apt/lists/*
USER 1000

ENV PATH="/foss/tools/bin:/foss/tools/sak:/headless/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/foss/tools/kactus2:/foss/tools/klayout:/foss/tools/osic-multitool"
ENV LD_LIBRARY_PATH="/foss/tools/klayout:/foss/tools/ngspice/lib:/foss/tools/iverilog/lib:/foss/tools/openems/lib:/foss/tools/kactus2:/foss/tools/gtkwave/lib/x86_64-linux-gnu"
ENV PDK=sky130A
ENV PDKPATH=/foss/pdks/sky130A
ENV STD_CELL_LIBRARY=sky130_fd_sc_hd
ENV SPICE_USERINIT_DIR=/foss/pdks/sky130A/libs.tech/ngspice

# Override .bashrc default PDK (base image defaults to ihp-sg13g2)
RUN echo '\n# PADE: override default PDK to Sky130A\nexport PDK=sky130A\nexport PDKPATH=/foss/pdks/sky130A\nexport STD_CELL_LIBRARY=sky130_fd_sc_hd\nexport SPICE_USERINIT_DIR=/foss/pdks/sky130A/libs.tech/ngspice' >> /headless/.bashrc

ENTRYPOINT []
CMD ["bash"]
